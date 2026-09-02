"""入荷推移(V-217)の取得クエリのテスト（test-design.md TC-SHC-I-009, I-011）。"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from application.inventory_order_alert.infrastructure.oracle.summary_queries import fetch_incoming_receipts

WRITE_KEYWORDS = ("INSERT", "UPDATE", "DELETE", "MERGE", "TRUNCATE", "DROP", "ALTER")


def _connection(rows: list[dict[str, object]]) -> tuple[MagicMock, MagicMock]:
    cursor = MagicMock()
    cursor.description = [("ITEM_CD",), ("VEND_CD",), ("ACPT_DATE",), ("QTY",)]
    cursor.fetchall.return_value = [tuple(row.values()) for row in rows]
    connection = MagicMock()
    connection.cursor.return_value = cursor
    return connection, cursor


def test_TC_SHC_I_009_fetch_incoming_receipts_returns_rows():
    connection, _ = _connection(
        [{"item_cd": "L1-A", "vend_cd": "9209", "acpt_date": date(2026, 6, 10), "qty": 50}]
    )

    receipts = fetch_incoming_receipts(connection, date(2024, 7, 1))

    assert receipts == [("L1-A", "9209", date(2026, 6, 10), 50)]


def test_TC_SHC_I_009_fetch_incoming_receipts_query_filters_by_window_start():
    connection, cursor = _connection([])

    fetch_incoming_receipts(connection, date(2024, 7, 1))

    sql = cursor.execute.call_args[0][0]
    assert "ACPT_DATE" in sql.upper()
    assert ":window_start" in sql or ":WINDOW_START" in sql.upper()
    params = cursor.execute.call_args[0][1] if len(cursor.execute.call_args[0]) > 1 else cursor.execute.call_args.kwargs
    assert date(2024, 7, 1) in params.values()


def test_fetch_incoming_receipts_issues_select_only():
    connection, cursor = _connection([])

    fetch_incoming_receipts(connection, date(2024, 7, 1))

    sql = cursor.execute.call_args[0][0].strip().upper()
    assert sql.startswith("SELECT")
    for keyword in WRITE_KEYWORDS:
        assert keyword not in sql


def test_TC_SHC_I_011_fetch_incoming_receipts_issues_single_query():
    connection, cursor = _connection([])

    fetch_incoming_receipts(connection, date(2024, 7, 1))

    assert cursor.execute.call_count == 1
