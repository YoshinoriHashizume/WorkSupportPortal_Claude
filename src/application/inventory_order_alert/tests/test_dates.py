from __future__ import annotations

from datetime import date, datetime, timezone

from application.inventory_order_alert.domain.value_objects.dates import (
    JST,
    add_calendar_months,
    format_stock_as_of_label,
    has_passed_calendar_months,
    is_within_calendar_months,
)


def test_add_calendar_months_same_day_next_year():
    assert add_calendar_months(date(2024, 6, 17), 12) == date(2025, 6, 17)


def test_add_calendar_months_handles_month_end():
    assert add_calendar_months(date(2024, 1, 31), 1) == date(2024, 2, 29)


def test_is_within_calendar_months_inclusive_deadline():
    assert is_within_calendar_months(
        start=date(2024, 1, 31),
        end=date(2025, 1, 31),
        months=12,
    )


def test_has_passed_calendar_months_waits_until_anniversary():
    assert not has_passed_calendar_months(
        start=date(2024, 5, 1),
        end=date(2025, 4, 30),
        months=12,
    )
    assert has_passed_calendar_months(
        start=date(2024, 5, 1),
        end=date(2025, 5, 1),
        months=12,
    )


# ISSUE-0008: 在庫時点（T-202）は取込日時。同日に複数回取り込んでも新旧を見分けられるよう時分を出す。


def test_format_stock_as_of_label_includes_time_for_aware_datetime():
    value = datetime(2026, 10, 29, 14, 30, tzinfo=JST)
    assert format_stock_as_of_label(value) == "2026年10月29日 14:30 時点の在庫"


def test_format_stock_as_of_label_converts_aware_datetime_to_jst():
    """UTC で渡しても日本時間で表示する（日付が繰り上がるケース）。"""
    value = datetime(2026, 10, 29, 20, 5, tzinfo=timezone.utc)
    assert format_stock_as_of_label(value) == "2026年10月30日 05:05 時点の在庫"


def test_format_stock_as_of_label_treats_naive_datetime_as_local():
    value = datetime(2026, 10, 29, 9, 7)
    assert format_stock_as_of_label(value) == "2026年10月29日 09:07 時点の在庫"


def test_format_stock_as_of_label_keeps_date_only_form():
    """暦日を渡す既存の呼び出し（在庫列の結合）は従来の書式を保つ。"""
    assert format_stock_as_of_label(date(2026, 10, 29)) == "2026年10月29日時点の在庫"
