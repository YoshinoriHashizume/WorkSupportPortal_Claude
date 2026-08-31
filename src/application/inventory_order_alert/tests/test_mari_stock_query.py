from __future__ import annotations

from unittest.mock import MagicMock

from application.inventory_order_alert.infrastructure.oracle.summary_queries import fetch_mari_stock_totals

WRITE_KEYWORDS = ("INSERT", "UPDATE", "DELETE", "MERGE", "TRUNCATE", "DROP", "ALTER")


def _connection(rows: list[dict[str, object]]) -> tuple[MagicMock, MagicMock]:
    cursor = MagicMock()
    cursor.description = [("ITEM_CD",), ("STOCK_QTY",)]
    cursor.fetchall.return_value = [tuple(row.values()) for row in rows]
    connection = MagicMock()
    connection.cursor.return_value = cursor
    return connection, cursor


def test_fetch_mari_stock_totals_sums_by_internal_item_cd():
    connection, _ = _connection([{"item_cd": "ITEM-A", "stock_qty": 30}])

    totals = fetch_mari_stock_totals(connection, ["ITEM-A"])

    assert totals["ITEM-A"] == 30


def test_fetch_mari_stock_totals_returns_empty_for_unknown_item():
    connection, _ = _connection([])

    totals = fetch_mari_stock_totals(connection, ["ITEM-UNKNOWN"])

    assert "ITEM-UNKNOWN" not in totals


def test_fetch_mari_stock_totals_issues_single_query_for_all_items():
    connection, cursor = _connection([{"item_cd": "ITEM-A", "stock_qty": 1}])

    fetch_mari_stock_totals(connection, [f"ITEM-{index}" for index in range(10)])

    # 品番ごとに問い合わせず、1 回でまとめて取得する
    assert cursor.execute.call_count == 1


def test_fetch_mari_stock_totals_chunks_over_oracle_in_limit():
    connection, cursor = _connection([{"item_cd": "ITEM-A", "stock_qty": 1}])

    fetch_mari_stock_totals(connection, [f"ITEM-{index:04d}" for index in range(1000)])

    # Oracle の IN 句上限を超えるため既存の chunked() で分割する（論理的には 1 回の取得）
    assert cursor.execute.call_count == 2


def test_fetch_mari_stock_totals_issues_select_only():
    connection, cursor = _connection([{"item_cd": "ITEM-A", "stock_qty": 1}])

    fetch_mari_stock_totals(connection, ["ITEM-A"])

    sql = cursor.execute.call_args[0][0].strip().upper()
    assert sql.startswith("SELECT")
    for keyword in WRITE_KEYWORDS:
        assert keyword not in sql


def test_fetch_mari_stock_totals_returns_empty_dict_for_no_items():
    connection, cursor = _connection([])

    totals = fetch_mari_stock_totals(connection, [])

    assert totals == {}
    assert cursor.execute.call_count == 0
