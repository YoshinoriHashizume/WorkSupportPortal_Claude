"""内示受注の取得クエリのテスト（test-design.md TC-SFV-I-001〜002、I-006）。`test_incoming_trend_query.py` の方式。"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from application.inventory_order_alert.infrastructure.oracle.summary_queries import (
    UNCONFIRMED_ORDER_FETCH_ERROR_PREFIX,
    fetch_unconfirmed_orders,
    fetch_unconfirmed_orders_or_warn,
)
from application.sales.infrastructure.oracle.client import OracleQueryError

WRITE_KEYWORDS = ("INSERT", "UPDATE", "DELETE", "MERGE", "TRUNCATE", "DROP", "ALTER")
AS_OF = date(2026, 9, 15)


def _connection(rows: list[tuple[object, ...]]) -> tuple[MagicMock, MagicMock]:
    cursor = MagicMock()
    cursor.description = [("CUST_CD",), ("ITEM_CD",), ("UNCNFM_REQUIRED_DATE",), ("QTY",)]
    cursor.fetchall.return_value = rows
    connection = MagicMock()
    connection.cursor.return_value = cursor
    return connection, cursor


# --- TC-SFV-I-001: 内示受注クエリの条件 ---


def test_i001_query_targets_unconfirmed_orders_within_the_window():
    connection, cursor = _connection([])

    fetch_unconfirmed_orders(connection, as_of_date=AS_OF)

    sql = cursor.execute.call_args[0][0]
    upper = sql.upper()
    assert "T_UNCNFM_ODR" in upper
    assert "DEL_FLG = '0'" in upper
    assert "UNCNFM_REQUIRED_DATE >= :AS_OF_DATE" in upper
    assert "UNCNFM_REQUIRED_DATE < :WINDOW_END" in upper.replace("  ", " ")
    params = cursor.execute.call_args[0][1]
    assert params == {"as_of_date": AS_OF, "window_end": date(2027, 1, 1)}


def test_i001_query_is_select_only_and_issued_once():
    connection, cursor = _connection([])

    fetch_unconfirmed_orders(connection, as_of_date=AS_OF)

    sql = cursor.execute.call_args[0][0].strip().upper()
    assert sql.startswith("SELECT")
    for keyword in WRITE_KEYWORDS:
        assert keyword not in sql
    assert cursor.execute.call_count == 1


# --- TC-SFV-I-002: 内示受注の行変換 ---


def test_i002_rows_are_converted_to_tuples_with_trimmed_codes_and_int_qty():
    connection, _ = _connection(
        [
            (" 104 ", "96160-00500-9065 ", date(2026, 10, 5), 194),
            ("137", "96160-00500-9065", date(2026, 11, 1), None),
            ("", "96160-00500-9065", date(2026, 11, 1), 10),
            ("137", "96160-00500-9065", None, 10),
        ]
    )

    orders = fetch_unconfirmed_orders(connection, as_of_date=AS_OF)

    assert orders == [
        ("104", "96160-00500-9065", date(2026, 10, 5), 194),
        ("137", "96160-00500-9065", date(2026, 11, 1), 0),
    ]


# --- TC-SFV-I-006: Oracle 例外時は内示推移を空にして続行 ---


def test_i006_oracle_error_returns_empty_orders_and_warning():
    connection = MagicMock()
    connection.cursor.return_value.execute.side_effect = OracleQueryError("ORA-00942: 表またはビューが存在しません。")

    orders, warning = fetch_unconfirmed_orders_or_warn(connection, as_of_date=AS_OF)

    assert orders == []
    assert warning.startswith(UNCONFIRMED_ORDER_FETCH_ERROR_PREFIX)
    assert "ORA-00942" in warning


def test_i006_success_returns_orders_and_no_warning():
    connection, _ = _connection([("104", "X", date(2026, 10, 5), 1)])

    orders, warning = fetch_unconfirmed_orders_or_warn(connection, as_of_date=AS_OF)

    assert orders == [("104", "X", date(2026, 10, 5), 1)]
    assert warning == ""


def test_i006_unexpected_exception_is_not_swallowed():
    connection = MagicMock()
    connection.cursor.return_value.execute.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError):
        fetch_unconfirmed_orders_or_warn(connection, as_of_date=AS_OF)
