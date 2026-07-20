from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.dates import parse_optional_ymd
from application.inventory_order_alert.domain.value_objects.export_csv import EXPORT_HEADER_LABELS as SUMMARY_HEADER_LABELS
from application.inventory_order_alert.infrastructure.oracle.summary_queries import (
    aggregate_shipment_stats,
    resolve_last_incoming_for_finished,
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
    shipments = [
        ("112", "90249-10112", date(2026, 6, 10), 100),
        ("112", "90249-10112", date(2026, 6, 15), 250),
    ]

    last_ship, count, total_qty = aggregate_shipment_stats(
        shipments,
        "112",
        "90249-10112",
        date(2026, 6, 11),
    )

    assert last_ship == date(2026, 6, 15)
    assert count == 1
    assert total_qty == 250


def test_fetch_customer_shipment_stats_without_incoming_counts_all_shipments():
    shipments = [
        ("112", "90249-10112", date(2026, 6, 10), 1000),
        ("112", "90249-10112", date(2026, 6, 15), 250),
    ]

    _, count, total_qty = aggregate_shipment_stats(shipments, "112", "90249-10112", None)

    assert count == 2
    assert total_qty == 1250


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
