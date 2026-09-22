"""発注残（V-224）・品目マスタ（V-225/V-227）の取得クエリのテスト（TC-SOR-I-001〜003、005〜006）。"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from application.inventory_order_alert.infrastructure.oracle.summary_queries import (
    ITEM_MASTER_FETCH_ERROR_PREFIX,
    OPEN_PURCHASE_ORDER_FETCH_ERROR_PREFIX,
    fetch_item_ordering_profiles,
    fetch_item_ordering_profiles_or_warn,
    fetch_open_purchase_orders,
    fetch_open_purchase_orders_or_warn,
)
from application.sales.infrastructure.oracle.client import OracleQueryError

WRITE_KEYWORDS = ("INSERT", "UPDATE", "DELETE", "MERGE", "TRUNCATE", "DROP", "ALTER")


def _connection(description: list[str], rows: list[tuple[object, ...]]) -> tuple[MagicMock, MagicMock]:
    cursor = MagicMock()
    cursor.description = [(name,) for name in description]
    cursor.fetchall.return_value = rows
    connection = MagicMock()
    connection.cursor.return_value = cursor
    return connection, cursor


PO_COLUMNS = ["ORDER_CD", "ITEM_CD", "VEND_CD", "PUCH_ODR_DLV_DATE", "CONFIRM_DLV_DATE", "ZAN"]


# --- TC-SOR-I-001: 発注残クエリの条件 ---


def test_i001_open_purchase_order_query_conditions():
    connection, cursor = _connection(PO_COLUMNS, [])

    fetch_open_purchase_orders(connection)

    sql = cursor.execute.call_args[0][0]
    upper = " ".join(sql.upper().split())
    assert "T_RLSD_PUCH_ODR" in upper
    assert "PUCH_ODR_STS_TYP = '2'" in upper
    assert "ODR_CANCEL_SLIP_ISS_FLG" in upper
    assert "T_PAST_INSPC_ACPT" in upper
    # 明細の識別子（重複除去キー）。同品番・同納期・同数量の別明細を潰さないため（2026/09/18）
    assert "TRIM(P.PUCH_ODR_CD) AS ORDER_CD" in upper
    assert upper.strip().startswith("SELECT")
    for keyword in WRITE_KEYWORDS:
        assert keyword not in upper
    assert cursor.execute.call_count == 1


# --- TC-SOR-I-002: 行変換 ---


def test_i002_rows_are_converted_with_confirmed_due_date_preferred():
    connection, _ = _connection(
        PO_COLUMNS,
        [
            (" PO-1 ", " X-9065 ", " 9065 ", date(2026, 10, 5), None, 100),
            ("PO-2", "X-9065", "9065", date(2026, 10, 5), date(2026, 10, 20), 30),
            ("PO-3", "X-9065", "9065", None, None, 7),
            # 残数 ≤ 0 の明細は落とす（REQ-SOR-F-001「残数 > 0」）
            ("PO-4", "X-9065", "9065", date(2026, 11, 1), None, -3),
            ("PO-5", "X-9065", "9065", date(2026, 11, 1), None, 0),
            ("PO-6", "", "9065", date(2026, 11, 1), None, 5),
            # 同品番・同納期・同数量でも別明細は両方返す
            ("PO-7", "X-9065", "9065", date(2026, 12, 1), None, 20),
            ("PO-8", "X-9065", "9065", date(2026, 12, 1), None, 20),
        ],
    )

    orders = fetch_open_purchase_orders(connection)

    assert orders == [
        ("PO-1", "X-9065", "9065", date(2026, 10, 5), 100),
        ("PO-2", "X-9065", "9065", date(2026, 10, 20), 30),
        ("PO-3", "X-9065", "9065", None, 7),
        ("PO-7", "X-9065", "9065", date(2026, 12, 1), 20),
        ("PO-8", "X-9065", "9065", date(2026, 12, 1), 20),
    ]


def test_i002_or_warn_wraps_oracle_error():
    connection = MagicMock()
    connection.cursor.return_value.execute.side_effect = OracleQueryError("ORA-00942")

    orders, warning = fetch_open_purchase_orders_or_warn(connection)

    assert orders == []
    assert warning.startswith(OPEN_PURCHASE_ORDER_FETCH_ERROR_PREFIX)
    assert "ORA-00942" in warning


# --- TC-SOR-I-003: 品目マスタクエリ ---


def test_i003_item_master_query_uses_chunked_in_clause():
    connection, cursor = _connection(["ITEM_CD", "FIXED_LT", "MRP_ODR_TYP"], [("X-9065", 3, "4")])

    profiles = fetch_item_ordering_profiles(connection, ["X-9065", "", "Y-9209"])

    sql = " ".join(cursor.execute.call_args[0][0].upper().split())
    assert "M_ITEM" in sql
    assert "FIXED_LT" in sql and "MRP_ODR_TYP" in sql
    assert "IN (" in sql
    assert cursor.execute.call_count == 1
    assert profiles == {"X-9065": (3, "4")}


def test_i003_item_master_query_is_skipped_for_no_items():
    connection, cursor = _connection(["ITEM_CD", "FIXED_LT", "MRP_ODR_TYP"], [])

    assert fetch_item_ordering_profiles(connection, []) == {}
    assert cursor.execute.call_count == 0


def test_i003_item_master_chunks_over_900_items():
    connection, cursor = _connection(["ITEM_CD", "FIXED_LT", "MRP_ODR_TYP"], [])

    fetch_item_ordering_profiles(connection, [f"ITEM-{index:04d}" for index in range(1000)])

    assert cursor.execute.call_count == 2


def test_i006_item_master_or_warn_wraps_oracle_error():
    connection = MagicMock()
    connection.cursor.return_value.execute.side_effect = OracleQueryError("ORA-00942")

    profiles, warning = fetch_item_ordering_profiles_or_warn(connection, ["X"])

    assert profiles == {}
    assert warning.startswith(ITEM_MASTER_FETCH_ERROR_PREFIX)


# --- 2026/09/18: BOM を末端まで辿る ---


def test_bom_chain_query_walks_all_levels_in_order():
    from datetime import date as _date

    from application.inventory_order_alert.infrastructure.oracle.summary_queries import fetch_bom_chain_by_root

    connection, cursor = _connection(
        ["ROOT_ITEM", "COMP_ITEM_CD", "LVL"],
        [("R", "X-9106", 3), ("R", "X-9133", 1), ("R", "X-9213", 2), ("R", "X-9213", 2)],
    )

    chain = fetch_bom_chain_by_root(connection, {"R"}, _date(2026, 9, 18))

    sql = " ".join(cursor.execute.call_args[0][0].upper().split())
    assert "CONNECT BY" in sql and "LEVEL" in sql and "OUTSIDE_TYP = '2'" in sql
    assert "LEVEL = 1" not in sql
    assert chain == {"R": [(1, "X-9133"), (2, "X-9213"), (3, "X-9106")]}


def test_bom_chain_query_is_skipped_for_no_roots():
    from datetime import date as _date

    from application.inventory_order_alert.infrastructure.oracle.summary_queries import fetch_bom_chain_by_root

    connection, cursor = _connection(["ROOT_ITEM", "COMP_ITEM_CD", "LVL"], [])

    assert fetch_bom_chain_by_root(connection, set(), _date(2026, 9, 18)) == {}
    assert cursor.execute.call_count == 0
