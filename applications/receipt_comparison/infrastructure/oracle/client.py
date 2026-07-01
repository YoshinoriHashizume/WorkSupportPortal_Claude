from __future__ import annotations

from datetime import date

from applications.gonenkukumi.infrastructure.oracle.client import oracle_connection, rows_as_dicts, use_mock
from applications.receipt_comparison.domain.comparison import normalize_qty
from applications.receipt_comparison.domain.records import MariReceiptRow
from applications.receipt_comparison.models import (
    FinishedProductReceiptSupplier,
    ReceiptComparisonType,
    SuppliedPartsReceiptSupplier,
)
from applications.receipt_comparison.infrastructure.persistence.supplier_repository import mari_vendor_codes_for_supplier


def fetch_mari_rows(
    *,
    comparison_type: str,
    supplier: FinishedProductReceiptSupplier | SuppliedPartsReceiptSupplier,
    start_date: date,
    end_date: date,
    receiving_places: list[str],
) -> list[MariReceiptRow]:
    if use_mock():
        return []
    if comparison_type == ReceiptComparisonType.FINISHED_PRODUCT:
        if not isinstance(supplier, FinishedProductReceiptSupplier):
            raise ValueError("完成品の取引先が読み込まれませんでした。")
        return fetch_finished_product_rows(supplier, start_date, end_date, receiving_places)
    if comparison_type == ReceiptComparisonType.SUPPLIED_PARTS:
        if not isinstance(supplier, SuppliedPartsReceiptSupplier):
            raise ValueError("支給品の取引先が読み込まれませんでした。")
        vendor_codes = mari_vendor_codes_for_supplier(supplier)
        if not vendor_codes:
            raise ValueError("子取引先（購買取引先コード）が未登録です。設定画面で追加してください。")
        return fetch_supplied_parts_rows(vendor_codes, start_date, end_date)
    raise ValueError("正しい比較区分が読み込まれませんでした。")


def fetch_finished_product_rows(
    supplier: FinishedProductReceiptSupplier,
    start_date: date,
    end_date: date,
    receiving_places: list[str],
) -> list[MariReceiptRow]:
    supplier_code = supplier.direct_delivery_customer_code or supplier.customer_code
    query1 = """
        SELECT
            T_SHIP1.CUST_ITEM_CD AS ITEM_CD,
            TO_CHAR(T_SHIP1.SHIP_DATE, 'yyyy/mm/dd') AS SHIP_DATE,
            T_SHIP1.SHIP_QTY AS SHIP_QTY,
            T_SHIP1.CUST_DESINATED_DLV_LOC_CD AS DELIVERY_PLACE
        FROM T_SHIP T_SHIP1, T_SHIP_ODR T_SHIP_ODR1
        WHERE T_SHIP1.COMPANY_CD = T_SHIP_ODR1.COMPANY_CD
          AND T_SHIP1.SHIP_ODR_NO = T_SHIP_ODR1.SHIP_ODR_NO
          AND T_SHIP1.CUST_CD = T_SHIP_ODR1.CUST_CD
          AND T_SHIP1.CUST_CD = :supplier_code
          AND T_SHIP1.SHIP_DATE BETWEEN TO_DATE(:start_date, 'YYYY/MM/DD') AND TO_DATE(:end_date, 'YYYY/MM/DD')
          AND T_SHIP1.SHIP_QTY > 0
    """
    query2 = """
        SELECT
            ITEM_CD,
            TO_CHAR(SALES_DATE, 'yyyy/mm/dd') AS SHIP_DATE,
            SALES_QTY AS SHIP_QTY,
            CUST_DESINATED_DLV_LOC_CD AS DELIVERY_PLACE
        FROM T_SALES_TEMP
        WHERE CUST_CD = :supplier_code
          AND SALES_DATE BETWEEN TO_DATE(:start_date, 'YYYY/MM/DD') AND TO_DATE(:end_date, 'YYYY/MM/DD')
          AND SHIP_SEQ_NO IS NULL
          AND SALES_QTY > 0
    """
    query = f"SELECT * FROM ({query1} UNION ALL {query2})"
    params = {
        "supplier_code": supplier_code,
        "start_date": start_date.strftime("%Y/%m/%d"),
        "end_date": end_date.strftime("%Y/%m/%d"),
    }
    if receiving_places:
        placeholders = ", ".join(f":place_{index}" for index, _ in enumerate(receiving_places))
        operator = "NOT IN" if supplier.exclusion else "IN"
        query += f" WHERE DELIVERY_PLACE {operator} ({placeholders})"
        params.update({f"place_{index}": place for index, place in enumerate(receiving_places)})
    query += " ORDER BY ITEM_CD ASC"
    return execute_mari_query(query, params)


def fetch_supplied_parts_rows(vendor_codes: list[str], start_date: date, end_date: date) -> list[MariReceiptRow]:
    placeholders = ", ".join(f":vendor_{index}" for index, _ in enumerate(vendor_codes))
    query = f"""
        SELECT
            T_RLSD_PUCH_ODR1.VEND_CD,
            CASE
                WHEN LENGTH(TRIM(T_RLSD_PUCH_ODR1.ITEM_CD)) > 10
                THEN SUBSTR(
                    TRIM(T_RLSD_PUCH_ODR1.ITEM_CD),
                    1,
                    LENGTH(TRIM(T_RLSD_PUCH_ODR1.ITEM_CD)) - 5
                )
                ELSE TRIM(T_RLSD_PUCH_ODR1.ITEM_CD)
            END AS ITEM_CD,
            TO_CHAR(T_ACPT_RSLT1.ACPT_DATE, 'yyyy/mm/dd') AS SHIP_DATE,
            T_ACPT_RSLT1.ACPT_QTY AS SHIP_QTY,
            T_ACPT_RSLT1.WH_CD AS DELIVERY_PLACE
        FROM T_ACPT_RSLT T_ACPT_RSLT1,
             M_VEND_CTRL M_VEND_CTRL1,
             T_RLSD_PUCH_ODR T_RLSD_PUCH_ODR1
        WHERE T_ACPT_RSLT1.PUCH_ODR_CD = T_RLSD_PUCH_ODR1.PUCH_ODR_CD
          AND T_RLSD_PUCH_ODR1.VEND_CD = M_VEND_CTRL1.VEND_CD
          AND T_RLSD_PUCH_ODR1.VEND_CD IN ({placeholders})
          AND T_ACPT_RSLT1.ACPT_DATE BETWEEN TO_DATE(:start_date, 'YYYY/MM/DD') AND TO_DATE(:end_date, 'YYYY/MM/DD')
    """
    params = {
        "start_date": start_date.strftime("%Y/%m/%d"),
        "end_date": end_date.strftime("%Y/%m/%d"),
        **{f"vendor_{index}": code for index, code in enumerate(vendor_codes)},
    }
    return execute_mari_query(query, params)


def execute_mari_query(query: str, params: dict[str, object]) -> list[MariReceiptRow]:
    with oracle_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query, params)
        rows = rows_as_dicts(cursor)
    return [
        MariReceiptRow(
            item_cd=str(row.get("item_cd") or "").strip(),
            ship_date=str(row.get("ship_date") or "").strip(),
            ship_qty=normalize_qty(row.get("ship_qty")),
            delivery_place=str(row.get("delivery_place") or "").strip(),
        )
        for row in rows
    ]


def list_vendors(keyword: str = "") -> list[dict[str, str]]:
    if use_mock():
        samples = [
            {"vendorCode": "1001", "vendorName": "サンプル仕入先A"},
            {"vendorCode": "1002", "vendorName": "サンプル仕入先B"},
            {"vendorCode": "2001", "vendorName": "サンプル仕入先C"},
            {"vendorCode": "9106", "vendorName": "サンプル仕入先D"},
            {"vendorCode": "9990", "vendorName": "サンプル仕入先E"},
        ]
        if not keyword:
            return samples
        normalized = keyword.upper()
        return [
            row
            for row in samples
            if row["vendorCode"].startswith(keyword) or normalized in row["vendorName"].upper()
        ]

    conditions = ["REGEXP_LIKE(TRIM(VEND_CD), '^\\d{4}$')"]
    params: dict[str, object] = {}
    if keyword:
        conditions.append("TRIM(VEND_CD) LIKE :vendor_keyword")
        params["vendor_keyword"] = f"{keyword}%"
    sql = f"""
        SELECT DISTINCT TRIM(VEND_CD) AS VEND_CD,
               TRIM(VEND_ANAME) AS VEND_ANAME
          FROM M_VEND_CTRL
         WHERE {" AND ".join(conditions)}
         ORDER BY VEND_CD
    """
    with oracle_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(sql, params)
        rows = rows_as_dicts(cursor)
    return [
        {"vendorCode": str(row["vend_cd"]).strip(), "vendorName": str(row.get("vend_aname") or "").strip()}
        for row in rows
    ]
