from __future__ import annotations

from applications.gonenkukumi.domain.errors import OracleNotConfiguredError, OracleQueryError

CUSTOMER_CODE_DIGIT_LENGTH_3 = 3
CUSTOMER_CODE_DIGIT_LENGTH_4 = 4
VALID_CUSTOMER_CODE_DIGIT_LENGTHS = {
    CUSTOMER_CODE_DIGIT_LENGTH_3,
    CUSTOMER_CODE_DIGIT_LENGTH_4,
}

CUSTOMER_NAME_SQL = "TRIM(NVL(CUST_ANAME, CUST_NAME))"


def mock_customers_all() -> list[dict[str, str]]:
    return [
        {"custCode": "101", "custName": "サンプル得意先A"},
        {"custCode": "102", "custName": "サンプル得意先B"},
        {"custCode": "119", "custName": "サンプル得意先D"},
        {"custCode": "191", "custName": "サンプル得意先E"},
        {"custCode": "201", "custName": "サンプル得意先C"},
        {"custCode": "1001", "custName": "支給品得意先A"},
        {"custCode": "9001", "custName": "丸栄－豊橋"},
    ]


def _filter_mock_customers(*, digit_length: int, keyword: str = "") -> list[dict[str, str]]:
    rows = [row for row in mock_customers_all() if len(row["custCode"]) == digit_length]
    if not keyword:
        return rows
    normalized = keyword.upper()
    return [
        row
        for row in rows
        if row["custCode"].startswith(keyword) or normalized in row["custName"].upper()
    ]


def customer_code_digit_pattern(digit_length: int) -> str:
    if digit_length not in VALID_CUSTOMER_CODE_DIGIT_LENGTHS:
        raise ValueError("得意先コードの桁数が不正です。")
    return f"^\\d{{{digit_length}}}$"


def list_customers_by_digit_length(*, digit_length: int, keyword: str = "") -> list[dict[str, str]]:
    from .client import (
        oracle_config,
        oracle_connection,
        rows_as_dicts,
        use_mock,
    )

    if use_mock():
        return _filter_mock_customers(digit_length=digit_length, keyword=keyword)

    config = oracle_config()
    conditions = [f"REGEXP_LIKE(TRIM(CUST_CD), '{customer_code_digit_pattern(digit_length)}')"]
    params: dict[str, object] = {}
    if keyword:
        conditions.append(
            f"(UPPER(TRIM(CUST_CD)) LIKE :code_keyword OR UPPER({CUSTOMER_NAME_SQL}) LIKE :name_keyword)"
        )
        params["code_keyword"] = f"{keyword.upper()}%"
        params["name_keyword"] = f"%{keyword.upper()}%"
    if config["company_cd"]:
        conditions.append("COMPANY_CD = :company_cd")
        params["company_cd"] = config["company_cd"]

    sql = f"""
        SELECT TRIM(CUST_CD) AS CUST_CD, {CUSTOMER_NAME_SQL} AS CUST_NAME
          FROM M_CUST
         WHERE {" AND ".join(conditions)}
         ORDER BY CUST_CD
    """
    try:
        with oracle_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, params)
            rows = rows_as_dicts(cursor)
    except Exception as exc:
        if isinstance(exc, OracleNotConfiguredError):
            raise
        raise OracleQueryError("得意先候補の取得に失敗しました。") from exc

    return [
        {"custCode": str(row["cust_cd"]).strip(), "custName": str(row.get("cust_name") or "").strip()}
        for row in rows
    ]


def list_customers(keyword: str = "") -> list[dict[str, str]]:
    """5年9組・完成品向け: 3桁得意先候補。"""
    return list_customers_by_digit_length(digit_length=CUSTOMER_CODE_DIGIT_LENGTH_3, keyword=keyword)


def list_customers_3(keyword: str = "") -> list[dict[str, str]]:
    return list_customers(keyword=keyword)


def list_customers_4(keyword: str = "") -> list[dict[str, str]]:
    """支給品向け: 4桁得意先候補。"""
    return list_customers_by_digit_length(digit_length=CUSTOMER_CODE_DIGIT_LENGTH_4, keyword=keyword)


def lookup_customer_name(customer_code: str) -> str | None:
    from .client import (
        oracle_config,
        oracle_connection,
        rows_as_dicts,
        use_mock,
    )

    customer_code = str(customer_code or "").strip()
    if not customer_code:
        return None

    if use_mock():
        match = next((row for row in mock_customers_all() if row["custCode"] == customer_code), None)
        return match["custName"] if match else None

    config = oracle_config()
    conditions = ["TRIM(CUST_CD) = :customer_code"]
    params: dict[str, object] = {"customer_code": customer_code}
    if config["company_cd"]:
        conditions.append("COMPANY_CD = :company_cd")
        params["company_cd"] = config["company_cd"]

    sql = f"""
        SELECT {CUSTOMER_NAME_SQL} AS CUST_NAME
          FROM M_CUST
         WHERE {" AND ".join(conditions)}
           AND ROWNUM = 1
    """
    try:
        with oracle_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, params)
            rows = rows_as_dicts(cursor)
    except Exception as exc:
        if isinstance(exc, OracleNotConfiguredError):
            raise
        raise OracleQueryError("得意先名の取得に失敗しました。") from exc

    if not rows:
        return None
    return str(rows[0].get("cust_name") or "").strip() or None
