from __future__ import annotations

from apps.inventory_order_alert.domain.row_counts import count_rows
from apps.inventory_order_alert.domain.row_display import (
    display_alert_level,
    row_alert_class,
)


def test_row_alert_class_uses_confirmation_color_for_confirmed_row():
    row = {"alert_level": "重点", "confirmation_status": "確認済み"}
    assert display_alert_level(row) == "重点"
    assert row_alert_class(row) == "確認済"


def test_row_alert_class_uses_confirmation_color_for_in_progress_row():
    row = {"alert_level": "重点", "confirmation_status": "確認中"}
    assert display_alert_level(row) == "重点"
    assert row_alert_class(row) == "確認中"


def test_row_alert_class_keeps_alert_level_when_unconfirmed():
    row = {"alert_level": "警告（出荷あり）", "confirmation_status": "未確認"}
    assert display_alert_level(row) == "警告（出荷あり）"
    assert row_alert_class(row) == "警告（出荷あり）"


def test_row_alert_class_normalizes_legacy_alert_level():
    row = {"alert_level": "警告（出荷）", "confirmation_status": "未確認"}
    assert display_alert_level(row) == "警告（出荷あり）"
    assert row_alert_class(row) == "警告（出荷あり）"


def test_count_rows_includes_alert_none_count():
    rows = [
        {"alert_level": "アラートなし", "confirmation_status": "未確認"},
        {"alert_level": "重点", "confirmation_status": "未確認"},
        {"alert_level": "アラートなし", "confirmation_status": "確認済み"},
    ]
    counts = count_rows(rows)
    assert counts.alert_none == 2


def test_count_rows_unconfirmed_includes_no_alert_rows():
    rows = [
        {"alert_level": "アラートなし", "confirmation_status": "未確認"},
        {"alert_level": "重点", "confirmation_status": "未確認"},
        {"alert_level": "アラートなし", "confirmation_status": "確認済み"},
        {"alert_level": "警告（出荷）", "confirmation_status": "確認中"},
    ]
    counts = count_rows(rows)
    assert counts.unconfirmed == 2
    assert counts.in_progress == 1
    assert counts.confirmed == 1


def test_count_rows_alert_levels_sum_to_total():
    rows = [
        {"alert_level": "重点", "confirmation_status": "確認済み"},
        {"alert_level": "重点", "confirmation_status": "未確認"},
        {"alert_level": "警告（出荷）", "confirmation_status": "確認済み"},
        {"alert_level": "警告（入荷）", "confirmation_status": "確認中"},
        {"alert_level": "アラートなし", "confirmation_status": "未確認"},
    ]
    counts = count_rows(rows)
    assert counts.critical == 2
    assert counts.warning_ship == 1
    assert counts.warning_incoming == 1
    assert counts.alert_none == 1
    assert counts.critical + counts.warning_ship + counts.warning_incoming + counts.alert_none == counts.total
    assert counts.unconfirmed + counts.in_progress + counts.confirmed == counts.total


def test_count_rows_alert_levels_sum_to_total_with_legacy_none_label():
    rows = [
        {"alert_level": "なし", "confirmation_status": "未確認"},
        {"alert_level": "重点", "confirmation_status": "未確認"},
    ]
    counts = count_rows(rows)
    assert counts.alert_none == 1
    assert counts.critical == 1
    assert counts.critical + counts.alert_none == counts.total
