from __future__ import annotations

"""仕入先マスタ（M_VEND_CTRL）から仕入先名を引く（spec/12 design §6.2）。基幹へは SELECT のみ。"""

from application.inventory_order_alert.domain.value_objects.errors import VendorLookupUnavailableError
from application.sales.infrastructure.oracle.client import (
    OracleNotConfiguredError,
    OracleQueryError,
    oracle_connection,
    rows_as_dicts,
    use_mock,
)


def lookup_vendor_names(codes: list[str]) -> dict[str, str]:
    """仕入先コード → 仕入先名（見つかったものだけ）。基幹に接続できなければ VendorLookupUnavailableError。"""
    unique_codes = sorted({str(code).strip() for code in codes if str(code).strip()})
    if not unique_codes:
        return {}
    if use_mock():
        # 開発用モック: 基幹がないため、すべて実在扱いにして名前はコードを返す
        return {code: code for code in unique_codes}

    binds = {f"c{index}": code for index, code in enumerate(unique_codes)}
    placeholders = ", ".join(f":{name}" for name in binds)
    sql = f"""
        SELECT TRIM(VEND_CD) AS VEND_CD,
               TRIM(VEND_ANAME) AS VEND_NAME
          FROM M_VEND_CTRL
         WHERE TRIM(VEND_CD) IN ({placeholders})
    """
    try:
        with oracle_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, binds)
            rows = rows_as_dicts(cursor)
    except (OracleNotConfiguredError, OracleQueryError) as exc:
        raise VendorLookupUnavailableError() from exc
    except Exception as exc:  # 接続失敗（oracledb の例外・タイムアウト等）
        raise VendorLookupUnavailableError() from exc

    names: dict[str, str] = {}
    for row in rows:
        code = str(row.get("vend_cd") or "").strip()
        if code:
            names[code] = str(row.get("vend_name") or "").strip()
    return names
