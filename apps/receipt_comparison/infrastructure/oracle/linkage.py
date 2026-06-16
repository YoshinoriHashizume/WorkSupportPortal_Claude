from __future__ import annotations

from apps.gonenkukumi.infrastructure.oracle.client import (
    OracleNotConfiguredError,
    OracleQueryError,
    oracle_connection,
    rows_as_dicts,
    use_mock,
)
from apps.receipt_comparison.domain.customer_vendor_link import resolve_purchase_vendor_code


def mock_customer_vendor_link(customer_code: str) -> dict[str, object]:
    samples = {
        "101": {"purchaseVendorCode": "9101", "vendorName": "サンプル仕入先A"},
        "102": {"purchaseVendorCode": "102", "vendorName": "サンプル仕入先B"},
        "137": {"purchaseVendorCode": "137", "vendorName": "エース産業"},
        "9001": {"purchaseVendorCode": "9001", "vendorName": "丸栄－豊橋"},
    }
    if customer_code in samples:
        return {"customerCode": customer_code, **samples[customer_code]}
    return {
        "customerCode": customer_code,
        "purchaseVendorCode": "",
        "vendorName": "",
    }


def get_customer_vendor_link(customer_code: str) -> dict[str, str]:
    customer_code = str(customer_code or "").strip()
    if not customer_code:
        return {"customerCode": "", "purchaseVendorCode": "", "vendorName": ""}

    if use_mock():
        mock = mock_customer_vendor_link(customer_code)
        return {
            "customerCode": str(mock["customerCode"]),
            "purchaseVendorCode": str(mock.get("purchaseVendorCode") or ""),
            "vendorName": str(mock.get("vendorName") or ""),
        }

    sql = """
        SELECT
            TRIM(c.CUST_CD) AS customer_code,
            TRIM(c.VEND_CD) AS cust_vend_cd,
            CASE
                WHEN EXISTS (
                    SELECT 1
                      FROM M_VEND_CTRL v
                     WHERE TRIM(v.VEND_CD) = TRIM(c.CUST_CD)
                ) THEN 'Y'
                ELSE 'N'
            END AS vendor_exists,
            (
                SELECT TRIM(v.VEND_ANAME)
                  FROM M_VEND_CTRL v
                 WHERE TRIM(v.VEND_CD) = TRIM(
                     NVL(NULLIF(TRIM(c.VEND_CD), ''), TRIM(c.CUST_CD))
                 )
                   AND ROWNUM = 1
            ) AS vendor_name
          FROM M_CUST c
         WHERE TRIM(c.CUST_CD) = :customer_code
           AND ROWNUM = 1
    """
    try:
        with oracle_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, {"customer_code": customer_code})
            rows = rows_as_dicts(cursor)
    except (OracleNotConfiguredError, OracleQueryError):
        raise
    except Exception as exc:
        raise OracleQueryError("客先と取引先の紐づけ取得に失敗しました。") from exc

    if not rows:
        return {"customerCode": customer_code, "purchaseVendorCode": "", "vendorName": ""}

    row = rows[0]
    purchase_vendor_code = resolve_purchase_vendor_code(
        customer_code,
        cust_vend_cd=str(row.get("cust_vend_cd") or ""),
        vendor_exists_for_customer_code=str(row.get("vendor_exists") or "").upper() == "Y",
    )
    return {
        "customerCode": customer_code,
        "purchaseVendorCode": purchase_vendor_code or "",
        "vendorName": str(row.get("vendor_name") or "").strip(),
    }


def purchase_vendor_codes_for_customer(customer_code: str) -> list[str]:
    link = get_customer_vendor_link(customer_code)
    purchase = str(link.get("purchaseVendorCode") or "").strip()
    return [purchase] if purchase else []
