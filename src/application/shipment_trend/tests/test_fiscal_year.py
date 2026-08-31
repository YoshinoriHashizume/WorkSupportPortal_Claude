from __future__ import annotations

from datetime import date

from application.shipment_trend.domain.value_objects.fiscal_year import add_months, fiscal_year_of, year_month_to_date


def test_fiscal_year_of_calendar_year():
    assert fiscal_year_of(date(2025, 1, 1)) == 2025
    assert fiscal_year_of(date(2025, 12, 31)) == 2025
    assert fiscal_year_of(date(2026, 3, 15)) == 2026


def test_add_months():
    assert add_months("2025-12", 1) == "2026-01"
    assert add_months("2026-01", -1) == "2025-12"


def test_year_month_to_date():
    assert year_month_to_date("2024-06") == date(2024, 6, 1)
