from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.alert_level import (
    ALERT_CRITICAL,
    ALERT_NONE,
    ALERT_WARNING_INCOMING,
    ALERT_WARNING_SHIP,
    alert_sort_rank,
    has_balanced_incoming_shipment,
    is_alert_level,
    is_alert_none_level,
    normalize_alert_level,
    resolve_alert_level,
)
from application.inventory_order_alert.domain.value_objects.alert_rules import build_alert_rule_rows

AS_OF = date(2026, 6, 17)
SETTINGS = {
    "warning_shipment_months": 12,
    "warning_incoming_months": 12,
}


def test_alert_none_label_is_alert_nashi():
    assert ALERT_NONE == "アラート無し"


def test_normalize_alert_level_accepts_legacy_none_label():
    assert normalize_alert_level("なし") == ALERT_NONE
    assert normalize_alert_level("アラートなし") == ALERT_NONE
    assert normalize_alert_level("問題なし") == ALERT_NONE
    assert is_alert_none_level("なし")
    assert alert_sort_rank("なし") == alert_sort_rank(ALERT_NONE)


def test_normalize_alert_level_accepts_legacy_warning_labels():
    assert normalize_alert_level("警告（出荷）") == ALERT_WARNING_SHIP
    assert normalize_alert_level("警告（入荷）") == ALERT_WARNING_INCOMING
    assert is_alert_level("警告（出荷）")
    assert is_alert_level("警告（入荷）")


def test_build_alert_rule_rows_uses_separate_months():
    rows = build_alert_rule_rows(warning_shipment_months=18, warning_incoming_months=6)
    assert rows[2].has_shipment == "あり（18か月以上）"
    assert rows[4].has_shipment == "なし（6か月以上）"


def test_has_balanced_incoming_shipment_within_calendar_months():
    assert has_balanced_incoming_shipment(
        date(2024, 1, 31),
        date(2025, 1, 15),
        warning_shipment_months=12,
    )


def test_has_balanced_incoming_shipment_false_when_after_calendar_deadline():
    assert not has_balanced_incoming_shipment(
        date(2024, 1, 31),
        date(2025, 2, 1),
        warning_shipment_months=12,
    )


def test_has_balanced_incoming_shipment_false_when_gap_exceeds_calendar_year():
    assert not has_balanced_incoming_shipment(
        date(2022, 1, 31),
        date(2025, 11, 27),
        warning_shipment_months=12,
    )


def test_resolve_alert_level_critical_when_no_incoming_and_shipment_exists():
    level = resolve_alert_level(
        None,
        date(2026, 6, 10),
        2,
        as_of_date=AS_OF,
        **SETTINGS,
    )
    assert level == ALERT_CRITICAL


def test_resolve_alert_level_warning_ship_when_shipment_after_calendar_deadline():
    level = resolve_alert_level(
        date(2024, 1, 31),
        date(2025, 2, 1),
        2,
        as_of_date=AS_OF,
        **SETTINGS,
    )
    assert level == ALERT_WARNING_SHIP


def test_resolve_alert_level_warning_incoming_when_no_shipment_for_threshold():
    level = resolve_alert_level(
        date(2024, 5, 1),
        None,
        0,
        as_of_date=AS_OF,
        **SETTINGS,
    )
    assert level == ALERT_WARNING_INCOMING


def test_resolve_alert_level_none_when_no_shipment_before_calendar_anniversary():
    level = resolve_alert_level(
        date(2024, 5, 1),
        None,
        0,
        as_of_date=date(2025, 4, 30),
        warning_shipment_months=12,
        warning_incoming_months=12,
    )
    assert level == ALERT_NONE


def test_resolve_alert_level_uses_separate_incoming_months():
    level = resolve_alert_level(
        date(2025, 12, 1),
        None,
        0,
        as_of_date=AS_OF,
        warning_shipment_months=24,
        warning_incoming_months=6,
    )
    assert level == ALERT_WARNING_INCOMING


def test_resolve_alert_level_none_when_balanced_within_calendar_months():
    level = resolve_alert_level(
        date(2026, 5, 1),
        date(2026, 6, 10),
        2,
        as_of_date=AS_OF,
        **SETTINGS,
    )
    assert level == ALERT_NONE


def test_resolve_alert_level_critical_when_no_incoming_even_if_shipment_is_old():
    level = resolve_alert_level(
        None,
        date(2024, 3, 29),
        1118,
        as_of_date=date(2026, 6, 18),
        **SETTINGS,
    )
    assert level == ALERT_CRITICAL


def test_resolve_alert_level_none_when_no_incoming_and_no_shipment():
    level = resolve_alert_level(
        None,
        None,
        0,
        as_of_date=AS_OF,
        **SETTINGS,
    )
    assert level == ALERT_NONE


def test_resolve_alert_level_respects_critical_enabled_false():
    level = resolve_alert_level(
        None,
        date(2026, 6, 10),
        2,
        as_of_date=AS_OF,
        critical_enabled=False,
        **SETTINGS,
    )
    assert level == ALERT_NONE


def test_is_alert_level():
    assert is_alert_level(ALERT_CRITICAL)
    assert is_alert_level(ALERT_WARNING_SHIP)
    assert is_alert_level(ALERT_WARNING_INCOMING)
    assert not is_alert_level(ALERT_NONE)
