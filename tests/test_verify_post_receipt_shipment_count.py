from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from scripts.verify_post_receipt_shipment_count import (
    fetch_customer_shipment_stats,
    parse_optional_ymd,
    resolve_last_incoming_for_finished,
    SUMMARY_HEADER_LABELS,
)


def test_parse_optional_ymd_defaults_to_today():
    assert parse_optional_ymd("") == date.today()


def test_parse_optional_ymd_parses_slash_format():
    assert parse_optional_ymd("2026/06/11") == date(2026, 6, 11)


def test_summary_headers_are_japanese():
    assert SUMMARY_HEADER_LABELS["last_incoming_date"] == "最終入荷日"
    assert SUMMARY_HEADER_LABELS["post_shipment_total_qty"] == "最終入荷日以降の出荷数合計"
    assert "階層1品番" in SUMMARY_HEADER_LABELS["level1_item_cd"]


def test_fetch_customer_shipment_stats_after_incoming_date():
    cursor = MagicMock()
    cursor.fetchone.return_value = (date(2026, 6, 15), 1, 250)
    connection = MagicMock()
    connection.cursor.return_value = cursor

    last_ship, count, total_qty = fetch_customer_shipment_stats(
        connection,
        "112",
        "90249-10112",
        date(2026, 6, 11),
    )

    assert last_ship == date(2026, 6, 15)
    assert count == 1
    assert total_qty == 250
    executed_sql = cursor.execute.call_args[0][0]
    assert "SHIP_DATE > :last_incoming_date" in executed_sql
    assert "DEL_FLG != 1" in executed_sql


def test_resolve_last_incoming_for_finished_picks_latest_level1_incoming():
    incoming = {("90249-10112-9209", "9209"): date(2026, 6, 11)}
    vendor = {"90249-10112-9209": ("9209", "小野メッキ")}
    last, l1, vend, vend_name = resolve_last_incoming_for_finished(
        "90249-10112",
        {"90249-10112": {"90249-10112"}},
        {"90249-10112": ["90249-10112-9209"]},
        vendor,
        incoming,
    )
    assert last == date(2026, 6, 11)
    assert l1 == "90249-10112-9209"
    assert vend == "9209"
    assert vend_name == "小野メッキ"


def test_resolve_last_incoming_for_finished_shows_level1_without_incoming():
    vendor = {"43522-D1020-9064": ("9064", "伸光技研")}
    last, l1, vend, vend_name = resolve_last_incoming_for_finished(
        "43522-D1020-00",
        {"43522-D1020-00": {"43522-D1020-00"}},
        {"43522-D1020-00": ["43522-D1020-9064"]},
        vendor,
        {},
    )
    assert last is None
    assert l1 == "43522-D1020-9064"
    assert vend == "9064"
    assert vend_name == "伸光技研"


def test_fetch_customer_shipment_stats_without_incoming_counts_all_shipments():
    cursor = MagicMock()
    cursor.fetchone.return_value = (date(2026, 6, 15), 7, 3250)
    connection = MagicMock()
    connection.cursor.return_value = cursor

    _, count, total_qty = fetch_customer_shipment_stats(connection, "112", "90249-10112", None)

    assert count == 7
    assert total_qty == 3250
    executed_sql = cursor.execute.call_args[0][0]
    assert "SHIP_DATE >" not in executed_sql
