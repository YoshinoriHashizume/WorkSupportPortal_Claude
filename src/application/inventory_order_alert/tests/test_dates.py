from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.dates import add_calendar_months, has_passed_calendar_months, is_within_calendar_months


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
