from __future__ import annotations

import logging
import os
import re
import unicodedata
from calendar import monthrange
from contextlib import contextmanager
from datetime import date
from typing import Iterator

from apps.gonenkukumi.domain.schemas import GonenKukumiSearchParams
from apps.gonenkukumi.domain.year_month_nav import YearMonth, normalize_year_month

logger = logging.getLogger(__name__)
DAY_NUMBER_PATTERN = re.compile(r"(\d{1,2})")


from apps.gonenkukumi.domain.errors import OracleNotConfiguredError, OracleQueryError


def use_mock() -> bool:
    return os.environ.get("ORACLE_USE_MOCK", "false").lower() != "false"


def oracle_connect_timeout_seconds() -> float:
    raw = os.environ.get("ORACLE_CONNECT_TIMEOUT_SECONDS", "5")
    try:
        timeout = float(raw)
    except ValueError:
        return 5.0
    return max(0.0, timeout)


def oracle_config() -> dict[str, str]:
    config = {
        "host": os.environ.get("ORACLE_HOST", ""),
        "port": os.environ.get("ORACLE_PORT", "1521"),
        "sid": os.environ.get("ORACLE_SID", ""),
        "service_name": os.environ.get("ORACLE_SERVICE_NAME", ""),
        "user": os.environ.get("ORACLE_USER", ""),
        "password": os.environ.get("ORACLE_PASSWORD", ""),
        "company_cd": os.environ.get("MARI_COMPANY_CD", ""),
        "thick_mode": os.environ.get("ORACLE_THICK_MODE", "false"),
        "client_lib_dir": os.environ.get("ORACLE_CLIENT_LIB_DIR", ""),
    }
    required = ["host", "port", "user", "password"]
    if not config["sid"] and not config["service_name"]:
        required.append("sid")
    missing = [key for key in required if not config[key]]
    if missing:
        raise OracleNotConfiguredError(f"Oracle 接続情報が不足しています: {', '.join(missing)}")
    return config


@contextmanager
def oracle_connection() -> Iterator[object]:
    try:
        import oracledb
    except ImportError as exc:
        raise OracleNotConfiguredError("oracledb パッケージがインストールされていません。") from exc

    config = oracle_config()
    if config["thick_mode"].lower() == "true":
        try:
            oracledb.init_oracle_client(lib_dir=config["client_lib_dir"] or None)
        except Exception as exc:
            if "already been initialized" not in str(exc):
                raise OracleNotConfiguredError("Oracle thick mode の初期化に失敗しました。") from exc

    if config["service_name"]:
        dsn = oracledb.makedsn(config["host"], int(config["port"]), service_name=config["service_name"])
    else:
        dsn = oracledb.makedsn(config["host"], int(config["port"]), sid=config["sid"])

    connect_kwargs: dict[str, object] = {
        "user": config["user"],
        "password": config["password"],
        "dsn": dsn,
    }
    timeout_seconds = oracle_connect_timeout_seconds()
    if timeout_seconds > 0:
        connect_kwargs["tcp_connect_timeout"] = timeout_seconds

    connection = oracledb.connect(**connect_kwargs)
    try:
        yield connection
    finally:
        connection.close()


def rows_as_dicts(cursor: object) -> list[dict[str, object]]:
    columns = [column[0].lower() for column in cursor.description]
    return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]


def month_bounds(year_month: str) -> tuple[date, date]:
    parsed = YearMonth.parse(year_month)
    year, month = parsed.year, parsed.month
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return date(year, month, 1), next_month


def active_days_in_month(year_month: str) -> int:
    parsed = YearMonth.parse(year_month)
    return monthrange(parsed.year, parsed.month)[1]


def empty_day_values() -> list[int]:
    return [0 for _ in range(31)]


def section_theme_for_customer() -> dict[str, str]:
    return {
        "bg": "#dcfce7",
        "lightBg": "#f0fdf4",
        "veryLightBg": "#f7fef9",
        "border": "#86efac",
        "outerBorder": "#22c55e",
    }


def section_theme_for_supplier(kaiso: object) -> dict[str, str]:
    try:
        level = max(1, int(kaiso or 1))
    except (TypeError, ValueError):
        level = 1
    hue = (200 + (level - 1) * 137.508) % 360
    return {
        "bg": f"hsl({hue:.3f} 55% 92%)",
        "lightBg": f"hsl({hue:.3f} 45% 96%)",
        "veryLightBg": f"hsl({hue:.3f} 25% 98%)",
        "border": f"hsl({hue:.3f} 45% 75%)",
        "outerBorder": f"hsl({hue:.3f} 55% 55%)",
    }


def parse_day_number(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        day_no = int(value)
        return day_no if 1 <= day_no <= 31 else None
    normalized = unicodedata.normalize("NFKC", str(value)).strip()
    match = DAY_NUMBER_PATTERN.search(normalized)
    if not match:
        return None
    day_no = int(match.group(1))
    return day_no if 1 <= day_no <= 31 else None


def parse_quantity(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, int | float):
        return int(value)
    normalized = unicodedata.normalize("NFKC", str(value)).replace(",", "").strip()
    return int(normalized or 0)


def add_company_condition(config: dict[str, str], conditions: list[str], params: dict[str, object]) -> None:
    if config["company_cd"]:
        conditions.append("COMPANY_CD = :company_cd")
        params["company_cd"] = config["company_cd"]


def add_effective_range_conditions(conditions: list[str], params: dict[str, object], *, alias: str = "") -> None:
    prefix = f"{alias}." if alias else ""
    conditions.append(f"{prefix}EFF_PHASE_IN_DATE <= :as_of_date")
    conditions.append(f"{prefix}EFF_PHASE_OUT_DATE >= :as_of_date")
    params["as_of_date"] = params.get("as_of_date") or date.today()


def mock_customers(keyword: str = "") -> list[dict[str, str]]:
    from .customers import list_customers

    return list_customers(keyword)


def list_customers(keyword: str = "") -> list[dict[str, str]]:
    from .customers import list_customers as list_customers_impl

    return list_customers_impl(keyword)


def get_customer_name(cust_code: str) -> str:
    from .customers import lookup_customer_name

    return lookup_customer_name(cust_code) or ""


def mock_cust_items(cust_code: str, keyword: str = "") -> list[dict[str, str]]:
    samples = [
        {"custCode": cust_code, "custItem": "ITEM-001", "itemName": "内作品番サンプル1"},
        {"custCode": cust_code, "custItem": "ITEM-002", "itemName": "内作品番サンプル2"},
    ]
    if not keyword:
        return samples
    return [row for row in samples if keyword.lower() in row["custItem"].lower() or keyword in row["itemName"]]


def list_cust_items(cust_code: str, keyword: str = "", as_of_date: date | None = None) -> list[dict[str, str]]:
    if use_mock():
        return mock_cust_items(cust_code, keyword)

    config = oracle_config()
    conditions = ["CUST_CD = :cust_code", "DLV_LOC_CD = '*'"]
    params: dict[str, object] = {"cust_code": cust_code, "as_of_date": as_of_date or date.today()}
    add_effective_range_conditions(conditions, params)
    if keyword:
        conditions.append("(UPPER(TRIM(CUST_ITEM_CD)) LIKE :keyword OR UPPER(TRIM(ITEM_CD)) LIKE :keyword)")
        params["keyword"] = f"%{keyword.upper()}%"
    if config["company_cd"]:
        conditions.append("COMPANY_CD = :company_cd")
        params["company_cd"] = config["company_cd"]

    sql = f"""
        SELECT CUST_CD, CUST_ITEM_CD, ITEM_CD
          FROM M_CUST_ITEM
         WHERE {" AND ".join(conditions)}
         ORDER BY CUST_ITEM_CD, ITEM_CD
    """
    try:
        with oracle_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, params)
            rows = rows_as_dicts(cursor)
    except Exception as exc:
        if isinstance(exc, OracleNotConfiguredError):
            raise
        raise OracleQueryError("得意先品目の取得に失敗しました。") from exc

    return [
        {
            "custCode": str(row["cust_cd"]).strip(),
            "custItem": str(row["cust_item_cd"]).strip(),
            "itemName": str(row["item_cd"]).strip(),
        }
        for row in rows
    ]


def resolve_internal_item_cd(params: GonenKukumiSearchParams) -> str:
    conditions = [
        "CUST_CD = :cust_code",
        "DLV_LOC_CD = '*'",
        "CUST_ITEM_CD = :cust_item",
        "ITEM_CD_OPTION_CHANGE_VALUE = :option_change",
    ]
    query_params: dict[str, object] = {
        "cust_code": params.cust_code,
        "cust_item": params.cust_item,
        "option_change": params.option_change,
        "as_of_date": params.as_of_date,
    }
    add_effective_range_conditions(conditions, query_params)

    sql = f"""
        SELECT ITEM_CD
          FROM M_CUST_ITEM
         WHERE {" AND ".join(conditions)}
    """
    with oracle_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(sql, query_params)
        rows = cursor.fetchall()
    if not rows:
        raise OracleQueryError("NAISAK_NOT_FOUND")
    return str(rows[-1][0]).strip()


def fetch_item_planning_values(connection: object, item_cd: str) -> dict[str, int]:
    sql = """
        SELECT FIXED_LT, SAFETY_STOCK
          FROM M_ITEM
         WHERE ITEM_CD = :item_cd
           AND ROWNUM = 1
    """
    cursor = connection.cursor()
    cursor.execute(sql, {"item_cd": item_cd})
    row = cursor.fetchone()
    if row is None:
        return {"teban": 0, "anzen": 0}
    fixed_lt, safety_stock = row
    return {"teban": parse_quantity(fixed_lt), "anzen": parse_quantity(safety_stock)}


def mock_search(params: GonenKukumiSearchParams, internal_item_cd: str | None = None) -> dict[str, object]:
    days = list(range(1, 32))
    return {
        "success": True,
        "custCode": params.cust_code,
        "customerName": get_customer_name(params.cust_code),
        "custItem": params.cust_item or "ITEM-001",
        "optionChange": params.option_change,
        "yearMonth": params.year_month,
        "asOfDate": params.as_of_date.isoformat(),
        "internalItemCd": internal_item_cd or "MOCK-ITEM",
        "headline": f"{params.cust_code} / {params.year_month}",
        "days": days,
        "activeDays": active_days_in_month(params.year_month),
        "holidayDays": [],
        "blocks": [
            {
                "label": "得意先",
                "meta": {"custCode": params.cust_code, "custItem": params.cust_item or "ITEM-001", "customerName": get_customer_name(params.cust_code), "teban": 1, "anzen": 0},
                "rows": [
                    {"item": "受注", "values": [day * 10 for day in days]},
                    {"item": "出荷", "values": [day * 8 for day in days]},
                ],
            },
            {
                "label": "仕入先",
                "kind": "supplier",
                "meta": {"vendCd": "V001", "vendName": "サンプル仕入先", "itemCd": "MOCK-PART", "requestType": "", "whCd": "?", "teban": 1, "anzen": 0, "kaiso": 1},
                "rows": [
                    {"item": "月初発注", "values": [day * 3 for day in days]},
                    {"item": "所要量", "values": [day * 5 for day in days]},
                    {"item": "確定発注", "values": [day * 4 for day in days]},
                    {"item": "入荷実績", "values": [day * 7 for day in days]},
                    {"item": "本日在庫", "values": [1000 - day for day in days]},
                ],
            },
        ],
    }


def with_row_totals(result: dict[str, object]) -> dict[str, object]:
    for block in result.get("blocks", []):
        block.setdefault("kind", "customer")
        block.setdefault("meta", {})
        if "theme" not in block:
            if block.get("kind") == "supplier":
                block["theme"] = section_theme_for_supplier(block.get("meta", {}).get("kaiso"))
            else:
                block["theme"] = section_theme_for_customer()
        for row in block.get("rows", []):
            values = row.get("values", [])
            row.setdefault("balance", None)
            if row.get("item") == "本日在庫":
                row["total"] = row.get("total") if isinstance(row.get("total"), int | float) else 0
                row["balance"] = None
                continue
            total = sum(value for value in values if isinstance(value, int | float))
            if isinstance(row["balance"], int | float):
                total += row["balance"]
            row["total"] = total
    return result


def fetch_daily_series(
    connection: object,
    *,
    table: str,
    date_column: str,
    qty_column: str,
    params: GonenKukumiSearchParams,
    internal_item_cd: str,
    start_date: date,
    next_month_date: date,
    extra_conditions: list[str] | None = None,
    cust_code: str | None = None,
) -> list[int]:
    conditions = [
        "CUST_CD = :cust_code",
        "ITEM_CD = :item_cd",
        f"{date_column} >= :start_date",
        f"{date_column} < :next_month_date",
    ]
    query_params: dict[str, object] = {
        "cust_code": cust_code or params.cust_code,
        "item_cd": internal_item_cd,
        "start_date": start_date,
        "next_month_date": next_month_date,
    }
    if extra_conditions:
        conditions.extend(extra_conditions)

    sql = f"""
        SELECT EXTRACT(DAY FROM {date_column}) AS DAY_NO,
               SUM(NVL({qty_column}, 0)) AS QTY
          FROM {table}
         WHERE {" AND ".join(conditions)}
         GROUP BY EXTRACT(DAY FROM {date_column})
         ORDER BY DAY_NO
    """
    cursor = connection.cursor()
    cursor.execute(sql, query_params)
    values = empty_day_values()
    for day_no, qty in cursor.fetchall():
        parsed_day_no = parse_day_number(day_no)
        if parsed_day_no is not None:
            values[parsed_day_no - 1] = parse_quantity(qty)
    return values


def fetch_customer_previous_balance(
    connection: object,
    *,
    params: GonenKukumiSearchParams,
    internal_item_cd: str,
    start_date: date,
    cust_code: str | None = None,
) -> int:
    conditions = [
        "CUST_CD = :cust_code",
        "ITEM_CD = :item_cd",
        "DESINATED_DLV_DATE <= :legacy_cutoff_date",
        "ODR_CMPLT_FLG != '1'",
        "DEL_FLG != '1'",
    ]
    query_params: dict[str, object] = {
        "cust_code": cust_code or params.cust_code,
        "item_cd": internal_item_cd,
        "legacy_cutoff_date": date(2022, 10, 1),
    }
    sql = f"""
        SELECT SUM(ODR_QTY) - SUM(TOTAL_SHIP_QTY)
          FROM T_ODR
         WHERE {" AND ".join(conditions)}
    """
    cursor = connection.cursor()
    cursor.execute(sql, query_params)
    row = cursor.fetchone()
    return int((row[0] if row else 0) or 0)


def fetch_stock_total(connection: object, internal_item_cd: str) -> int:
    sql = """
        SELECT SUM(NVL(STOCK_ON_HAND_QTY, 0))
          FROM T_ITEM_STOCK
         WHERE ITEM_CD = :item_cd
    """
    cursor = connection.cursor()
    cursor.execute(sql, {"item_cd": internal_item_cd})
    row = cursor.fetchone()
    return int((row[0] if row else 0) or 0)


def fetch_item_stock_total(connection: object, item_cd: str) -> int:
    sql = """
        SELECT SUM(NVL(STOCK_ON_HAND_QTY, 0))
          FROM T_ITEM_STOCK
         WHERE ITEM_CD = :item_cd
    """
    cursor = connection.cursor()
    cursor.execute(sql, {"item_cd": item_cd})
    row = cursor.fetchone()
    return int((row[0] if row else 0) or 0)


def fetch_customer_rows(connection: object, params: GonenKukumiSearchParams, internal_item_cd: str) -> list[dict[str, str]]:
    conditions = [
        "ci.ITEM_CD = :item_cd",
        "ci.DLV_LOC_CD = '*'",
        "ci.ITEM_CD_OPTION_CHANGE_VALUE = :option_change",
    ]
    query_params: dict[str, object] = {
        "item_cd": internal_item_cd,
        "option_change": params.option_change,
        "as_of_date": params.as_of_date,
    }
    add_effective_range_conditions(conditions, query_params, alias="ci")

    sql = f"""
        SELECT ci.CUST_CD,
               ci.CUST_ITEM_CD,
               cust.CUST_ANAME
          FROM M_CUST_ITEM ci
          LEFT JOIN M_CUST cust
            ON cust.CUST_CD = ci.CUST_CD
         WHERE {" AND ".join(conditions)}
    """
    cursor = connection.cursor()
    cursor.execute(sql, query_params)
    rows = rows_as_dicts(cursor)
    if not rows:
        return [{"custCode": params.cust_code, "custItem": params.cust_item, "customerName": get_customer_name(params.cust_code)}]
    return [
        {
            "custCode": str(row["cust_cd"]).strip(),
            "custItem": str(row["cust_item_cd"]).strip(),
            "customerName": str(row.get("cust_aname") or "").strip(),
        }
        for row in rows
    ]


def build_customer_block(
    connection: object,
    params: GonenKukumiSearchParams,
    internal_item_cd: str,
    customer: dict[str, str],
    start_date: date,
    next_month_date: date,
) -> dict[str, object]:
    cust_code = customer["custCode"]
    unofficial = fetch_daily_series(
        connection,
        table="T_UNCNFM_ODR",
        date_column="UNCNFM_REQUIRED_DATE",
        qty_column="UNCNFM_REQUIRED_QTY",
        params=params,
        internal_item_cd=internal_item_cd,
        start_date=start_date,
        next_month_date=next_month_date,
        extra_conditions=["DEL_FLG = '0'"],
        cust_code=cust_code,
    )
    fixed = fetch_daily_series(
        connection,
        table="T_ODR",
        date_column="DESINATED_DLV_DATE",
        qty_column="ODR_QTY",
        params=params,
        internal_item_cd=internal_item_cd,
        start_date=start_date,
        next_month_date=next_month_date,
        extra_conditions=["DEL_FLG != '1'"],
        cust_code=cust_code,
    )
    united = fetch_daily_series(
        connection,
        table="T_UNITE_ODR",
        date_column="SHIP_PLAN_DATE",
        qty_column="REQUIRED_QTY",
        params=params,
        internal_item_cd=internal_item_cd,
        start_date=start_date,
        next_month_date=next_month_date,
        extra_conditions=["DEL_FLG = '0'"],
        cust_code=cust_code,
    )
    shipped = fetch_daily_series(
        connection,
        table="T_SHIP",
        date_column="SHIP_DATE",
        qty_column="SHIP_QTY",
        params=params,
        internal_item_cd=internal_item_cd,
        start_date=start_date,
        next_month_date=next_month_date,
        extra_conditions=["DEL_FLG != 1"],
        cust_code=cust_code,
    )
    sales = fetch_daily_series(
        connection,
        table="T_SALES_TEMP",
        date_column="SALES_DATE",
        qty_column="SALES_QTY",
        params=params,
        internal_item_cd=internal_item_cd,
        start_date=start_date,
        next_month_date=next_month_date,
        extra_conditions=["DEL_FLG != '1'", "ONEROUS_CONS_SALES_TYP != '1'"],
        cust_code=cust_code,
    )
    stock_total = fetch_stock_total(connection, internal_item_cd)
    fixed_balance = fetch_customer_previous_balance(
        connection,
        params=params,
        internal_item_cd=internal_item_cd,
        start_date=start_date,
        cust_code=cust_code,
    )
    return {
        "kind": "customer",
        "label": f"得意先 {cust_code}",
        "theme": section_theme_for_customer(),
        "meta": customer,
        "rows": [
            {"item": "内示受注", "values": unofficial},
            {"item": "確定受注", "values": fixed, "balance": fixed_balance},
            {"item": "統合受注", "values": united},
            {"item": "出荷実績", "values": shipped},
            {"item": "売上実績", "values": sales},
            {"item": "本日在庫", "values": empty_day_values(), "total": stock_total},
        ],
    }


def fetch_customer_blocks(params: GonenKukumiSearchParams, internal_item_cd: str) -> list[dict[str, object]]:
    start_date, next_month_date = month_bounds(params.year_month)
    with oracle_connection() as connection:
        customer_rows = fetch_customer_rows(connection, params, internal_item_cd)
        planning_values = fetch_item_planning_values(connection, internal_item_cd)
        return [
            build_customer_block(connection, params, internal_item_cd, {**customer, **planning_values}, start_date, next_month_date)
            for customer in customer_rows
        ]


def fetch_supplier_root_items(connection: object, internal_item_cd: str) -> list[str]:
    sql = """
        SELECT SUB_ITEM_CD_01,
               SUB_ITEM_CD_02,
               SUB_ITEM_CD_03,
               SUB_ITEM_CD_04,
               SUB_ITEM_CD_05
          FROM M_ITEM
         WHERE ITEM_CD = :item_cd
    """
    cursor = connection.cursor()
    cursor.execute(sql, {"item_cd": internal_item_cd})
    roots = [internal_item_cd]
    seen = {internal_item_cd}
    for row in cursor.fetchall():
        for value in row:
            item_cd = str(value or "").strip()
            if item_cd and item_cd not in seen:
                roots.append(item_cd)
                seen.add(item_cd)
    return roots


def fetch_supplier_candidates_for_root(connection: object, root_item_cd: str, as_of_date: date) -> list[dict[str, object]]:
    sql = """
        SELECT LEVEL AS KAISO,
               ps.COMP_ITEM_CD,
               item.ITEM_NAME,
               ps.CONS_TYP,
               item.PROCESS_REQUEST_ISS_TYP,
               item.KANBAN_FLG,
               item.FIXED_LT,
               item.SAFETY_STOCK
          FROM M_PS ps
          JOIN M_ITEM item
            ON item.ITEM_CD = ps.COMP_ITEM_CD
         WHERE item.OUTSIDE_TYP = '2'
           AND ps.EFF_PHASE_IN_DATE <= :as_of_date
           AND ps.EFF_PHASE_OUT_DATE >= :as_of_date
        START WITH ps.PARENT_ITEM_CD = :root_item_cd
        CONNECT BY PRIOR ps.COMP_ITEM_CD = ps.PARENT_ITEM_CD
    """
    cursor = connection.cursor()
    cursor.execute(sql, {"root_item_cd": root_item_cd, "as_of_date": as_of_date})
    rows = rows_as_dicts(cursor)
    suppliers: list[dict[str, object]] = []
    for row in rows:
        item_cd = str(row["comp_item_cd"]).strip()
        suppliers.append(
            {
                "kaiso": int(row["kaiso"] or 1),
                "itemCd": item_cd,
                "itemName": str(row.get("item_name") or "").strip(),
                "consTyp": str(row.get("cons_typ") or "").strip(),
                "requestType": supplier_request_type(row),
                "teban": parse_quantity(row.get("fixed_lt")),
                "anzen": parse_quantity(row.get("safety_stock")),
            }
        )
    return suppliers


def fetch_supplier_candidates(connection: object, internal_item_cd: str, as_of_date: date) -> list[dict[str, object]]:
    seen: set[str] = set()
    candidates: list[dict[str, object]] = []
    for root_item_cd in fetch_supplier_root_items(connection, internal_item_cd):
        for supplier in fetch_supplier_candidates_for_root(connection, root_item_cd, as_of_date):
            item_cd = str(supplier["itemCd"])
            if item_cd in seen:
                continue
            seen.add(item_cd)
            candidates.append(supplier)
    return candidates


def supplier_request_type(row: dict[str, object]) -> str:
    if str(row.get("process_request_iss_typ") or "").strip() == "1":
        return "加工依頼"
    if str(row.get("kanban_flg") or "").strip() == "1":
        return "かんばん"
    return ""


def attach_supplier_master(connection: object, supplier: dict[str, object]) -> dict[str, object]:
    conditions = ["cost.ITEM_CD = :item_cd"]
    params: dict[str, object] = {"item_cd": supplier["itemCd"]}
    sql = f"""
        SELECT cost.VEND_CD,
               vend.VEND_ANAME,
               wh.WH_CD
          FROM M_PUCH_UNIT_COST_H cost
          LEFT JOIN M_VEND_CTRL vend
            ON cost.VEND_CD = vend.VEND_CD
          LEFT JOIN M_ITEM_RCV_WH wh
            ON wh.ITEM_CD = cost.ITEM_CD
         WHERE {" AND ".join(conditions)}
    """
    cursor = connection.cursor()
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    if not rows:
        return {**supplier, "vendCd": "?", "vendName": "", "plantCd": "", "whCd": "?"}
    vend_cd, vend_name, wh_cd = rows[-1]
    return {
        **supplier,
        "vendCd": str(vend_cd or "?").strip(),
        "vendName": str(vend_name or "").strip(),
        "plantCd": "",
        "whCd": str(wh_cd or "?").strip(),
    }


def fetch_supplier_daily_series(
    connection: object,
    *,
    table: str,
    date_column: str,
    qty_column: str,
    item_cd: str,
    vend_cd: str | None,
    start_date: date,
    next_month_date: date,
    extra_conditions: list[str] | None = None,
) -> list[int]:
    conditions = [
        "ITEM_CD = :item_cd",
        f"{date_column} >= :start_date",
        f"{date_column} < :next_month_date",
    ]
    params: dict[str, object] = {"item_cd": item_cd, "start_date": start_date, "next_month_date": next_month_date}
    if vend_cd and vend_cd != "?":
        conditions.append("VEND_CD = :vend_cd")
        params["vend_cd"] = vend_cd
    if extra_conditions:
        conditions.extend(extra_conditions)

    sql = f"""
        SELECT EXTRACT(DAY FROM {date_column}) AS DAY_NO,
               SUM(NVL({qty_column}, 0)) AS QTY
          FROM {table}
         WHERE {" AND ".join(conditions)}
         GROUP BY EXTRACT(DAY FROM {date_column})
         ORDER BY DAY_NO
    """
    cursor = connection.cursor()
    cursor.execute(sql, params)
    values = empty_day_values()
    for day_no, qty in cursor.fetchall():
        parsed_day_no = parse_day_number(day_no)
        if parsed_day_no is not None:
            values[parsed_day_no - 1] = parse_quantity(qty)
    return values


def fetch_supplier_previous_purchase_balance(
    connection: object,
    *,
    item_cd: str,
    vend_cd: str | None,
    start_date: date,
) -> int:
    conditions = [
        "purchase.ITEM_CD = :item_cd",
        "purchase.PUCH_ODR_DLV_DATE < :start_date",
        "purchase.PUCH_ODR_STS_TYP = '2'",
        "purchase.ODR_CANCEL_SLIP_ISS_FLG = '0'",
    ]
    params: dict[str, object] = {"item_cd": item_cd, "start_date": start_date}
    if vend_cd and vend_cd != "?":
        conditions.append("purchase.VEND_CD = :vend_cd")
        params["vend_cd"] = vend_cd
    sql = f"""
        SELECT SUM(ZANSU)
          FROM (
                SELECT MAX(purchase.PUCH_ODR_QTY) - NVL(SUM(accepted.ACPT_QTY), 0) AS ZANSU
                  FROM T_RLSD_PUCH_ODR purchase
                  LEFT OUTER JOIN T_PAST_INSPC_ACPT accepted
                    ON purchase.PUCH_ODR_CD = accepted.PUCH_ODR_CD
                 WHERE {" AND ".join(conditions)}
                 GROUP BY purchase.PUCH_ODR_CD,
                          purchase.VEND_CD,
                          purchase.ITEM_CD
               )
    """
    cursor = connection.cursor()
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return int((row[0] if row else 0) or 0)


def fetch_supplier_demand_series(
    connection: object,
    *,
    item_cd: str,
    vend_cd: str | None,
    start_date: date,
    next_month_date: date,
) -> list[int]:
    conditions = [
        "od.ITEM_CD = :item_cd",
        "od.PRD_DUE_DATE >= :start_date",
        "od.PRD_DUE_DATE < :next_month_date",
        "od.OD_TYP = '2'",
        "(purchase.ODR_CANCEL_SLIP_ISS_FLG IN ('0') OR purchase.ODR_CANCEL_SLIP_ISS_FLG IS NULL)",
    ]
    params: dict[str, object] = {"item_cd": item_cd, "start_date": start_date, "next_month_date": next_month_date}

    sql = f"""
        SELECT EXTRACT(DAY FROM od.PRD_DUE_DATE) AS DAY_NO,
               SUM(NVL(od.ODR_QTY, 0)) AS QTY
          FROM T_OD od
          LEFT JOIN T_RLSD_PUCH_ODR purchase
            ON purchase.OD_NO = od.OD_NO
         WHERE {" AND ".join(conditions)}
         GROUP BY EXTRACT(DAY FROM od.PRD_DUE_DATE)
         ORDER BY DAY_NO
    """
    cursor = connection.cursor()
    cursor.execute(sql, params)
    values = empty_day_values()
    for day_no, qty in cursor.fetchall():
        parsed_day_no = parse_day_number(day_no)
        if parsed_day_no is not None:
            values[parsed_day_no - 1] = parse_quantity(qty)
    return values


def fetch_monthly_order_work(connection: object, *, item_cd: str, vend_cd: str, year_month: str) -> list[int]:
    parsed_year_month = YearMonth.parse(year_month).format()
    year, month = parsed_year_month.split("-", 1)
    month = str(int(month))
    sql = """
        SELECT DAY_01, QTY_01, DAY_02, QTY_02, DAY_03, QTY_03, DAY_04, QTY_04, DAY_05, QTY_05,
               DAY_06, QTY_06, DAY_07, QTY_07, DAY_08, QTY_08, DAY_09, QTY_09, DAY_10, QTY_10,
               DAY_11, QTY_11, DAY_12, QTY_12, DAY_13, QTY_13, DAY_14, QTY_14, DAY_15, QTY_15,
               DAY_16, QTY_16, DAY_17, QTY_17, DAY_18, QTY_18, DAY_19, QTY_19, DAY_20, QTY_20,
               DAY_21, QTY_21, DAY_22, QTY_22, DAY_23, QTY_23, DAY_24, QTY_24, DAY_25, QTY_25,
               DAY_26, QTY_26
          FROM T_U_MONTHLY_ODR_WORK
         WHERE MNGMNT_YEAR = :year
           AND MNGMNT_MONTH = :month
           AND VENDOR_CD = :vend_cd
           AND ARRIVAL_ITEM_CD = :item_cd
    """
    cursor = connection.cursor()
    cursor.execute(sql, {"vend_cd": vend_cd, "item_cd": item_cd, "year": year, "month": month})
    values = empty_day_values()
    for row in cursor.fetchall():
        pairs = list(row)
        for index in range(0, len(pairs), 2):
            day_no = pairs[index]
            qty = pairs[index + 1]
            parsed_day_no = parse_day_number(day_no)
            if parsed_day_no is not None:
                values[parsed_day_no - 1] = parse_quantity(qty)
    return values


def build_supplier_block(connection: object, params: GonenKukumiSearchParams, supplier: dict[str, object]) -> dict[str, object]:
    start_date, next_month_date = month_bounds(params.year_month)
    item_cd = str(supplier["itemCd"])
    vend_cd = str(supplier.get("vendCd") or "?")
    monthly = fetch_monthly_order_work(connection, item_cd=item_cd, vend_cd=vend_cd, year_month=params.year_month)
    demand = fetch_supplier_demand_series(
        connection,
        item_cd=item_cd,
        vend_cd=vend_cd,
        start_date=start_date,
        next_month_date=next_month_date,
    )
    purchase = fetch_supplier_daily_series(
        connection,
        table="T_RLSD_PUCH_ODR",
        date_column="PUCH_ODR_DLV_DATE",
        qty_column="PUCH_ODR_QTY",
        item_cd=item_cd,
        vend_cd=vend_cd,
        start_date=start_date,
        next_month_date=next_month_date,
        extra_conditions=["PUCH_ODR_STS_TYP != '1'", "ODR_CANCEL_SLIP_ISS_FLG = '0'"],
    )
    purchase_balance = fetch_supplier_previous_purchase_balance(
        connection,
        item_cd=item_cd,
        vend_cd=vend_cd,
        start_date=start_date,
    )
    accepted = fetch_supplier_daily_series(
        connection,
        table="T_PAST_INSPC_ACPT",
        date_column="ACPT_DATE",
        qty_column="INSPC_ACPT_QTY",
        item_cd=item_cd,
        vend_cd=vend_cd,
        start_date=start_date,
        next_month_date=next_month_date,
    )
    stock_total = fetch_item_stock_total(connection, item_cd)
    label_parts = [f"仕入先 {vend_cd}", item_cd]
    if supplier.get("vendName"):
        label_parts.insert(1, str(supplier["vendName"]))
    if supplier.get("requestType"):
        label_parts.append(str(supplier["requestType"]))
    return {
        "kind": "supplier",
        "label": " / ".join(label_parts),
        "theme": section_theme_for_supplier(supplier.get("kaiso")),
        "meta": supplier,
        "rows": [
            {"item": "月初発注", "values": monthly},
            {"item": "所要量", "values": demand},
            {"item": "確定発注", "values": purchase, "balance": purchase_balance},
            {"item": "入荷実績", "values": accepted},
            {"item": "本日在庫", "values": empty_day_values(), "total": stock_total},
        ],
    }


def fetch_supplier_blocks(params: GonenKukumiSearchParams, internal_item_cd: str) -> list[dict[str, object]]:
    with oracle_connection() as connection:
        candidates = fetch_supplier_candidates(connection, internal_item_cd, params.as_of_date)
        suppliers = [attach_supplier_master(connection, supplier) for supplier in candidates]
        return [build_supplier_block(connection, params, supplier) for supplier in suppliers]


def fetch_holiday_days(year_month: str) -> list[int]:
    start_date, next_month_date = month_bounds(year_month)
    start_text = start_date.strftime("%Y%m%d")
    end_text = next_month_date.strftime("%Y%m%d")
    sql = """
        SELECT REGEXP_REPLACE(TO_CHAR(CAL_DATE), '[^0-9]', '') AS CAL_DATE_TEXT
          FROM M_CAL
         WHERE REGEXP_REPLACE(TO_CHAR(CAL_DATE), '[^0-9]', '') >= :start_text
           AND REGEXP_REPLACE(TO_CHAR(CAL_DATE), '[^0-9]', '') < :end_text
           AND (TRIM(HOLIDAY_FLG) IS NULL OR TRIM(HOLIDAY_FLG) <> '0')
    """
    try:
        with oracle_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, {"start_text": start_text, "end_text": end_text})
            days: list[int] = []
            for (cal_date_text,) in cursor.fetchall():
                text = str(cal_date_text or "")
                if len(text) >= 8:
                    day_no = int(text[-2:])
                    if 1 <= day_no <= 31:
                        days.append(day_no)
            return sorted(set(days))
    except Exception as exc:
        logger.warning("休日情報の取得に失敗しました。休日強調なしで継続します。", exc_info=exc)
        return []


def real_search(params: GonenKukumiSearchParams) -> dict[str, object]:
    internal_item_cd = resolve_internal_item_cd(params)
    customer_name = get_customer_name(params.cust_code)
    days = list(range(1, 32))
    customer_blocks = fetch_customer_blocks(params, internal_item_cd)
    supplier_blocks = fetch_supplier_blocks(params, internal_item_cd)
    return {
        "success": True,
        "custCode": params.cust_code,
        "customerName": customer_name,
        "custItem": params.cust_item,
        "optionChange": params.option_change,
        "yearMonth": params.year_month,
        "asOfDate": params.as_of_date.isoformat(),
        "internalItemCd": internal_item_cd,
        "headline": f"{params.cust_code} / {params.year_month} / {internal_item_cd}",
        "days": days,
        "activeDays": active_days_in_month(params.year_month),
        "holidayDays": fetch_holiday_days(params.year_month),
        "blocks": [*customer_blocks, *supplier_blocks],
    }


def run_gonenkukumi_oracle_search(params: GonenKukumiSearchParams) -> dict[str, object]:
    if use_mock():
        return with_row_totals(mock_search(params))

    return with_row_totals(real_search(params))
