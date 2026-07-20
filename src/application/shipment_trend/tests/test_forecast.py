from __future__ import annotations

from datetime import date

from application.shipment_trend.domain.value_objects.forecast import (
    average_of_current_year,
    build_chart_points,
    build_forecast_months,
    expand_continuous_monthly_points,
    forecast_monthly_qty,
    remaining_calendar_year_months,
    sum_current_year_through_month,
)


def test_average_of_current_year_uses_only_current_calendar_year():
    monthly = {"2024-12": 1000, "2025-01": 50, "2025-02": 70}
    assert average_of_current_year(monthly, as_of_date=date(2025, 2, 28)) == 60.0


def test_average_of_current_year_divides_by_elapsed_months_not_shipment_months():
    monthly = {"2025-06": 400}
    assert sum_current_year_through_month(monthly, as_of_date=date(2025, 6, 30)) == 400
    assert average_of_current_year(monthly, as_of_date=date(2025, 6, 30)) == 400 / 6
    assert forecast_monthly_qty(monthly, as_of_date=date(2025, 6, 30)) == 67


def test_remaining_calendar_year_months():
    assert remaining_calendar_year_months(date(2025, 2, 28)) == 10
    assert remaining_calendar_year_months(date(2025, 5, 31)) == 7
    assert remaining_calendar_year_months(date(2025, 12, 31)) == 0


def test_build_forecast_months_uses_ceiled_monthly_average():
    monthly = {"2025-01": 80, "2025-02": 120}
    forecast = build_forecast_months(monthly, as_of_date=date(2025, 2, 28))
    assert len(forecast) == 10
    assert forecast[0]["yearMonth"] == "2025-03"
    assert forecast[-1]["yearMonth"] == "2025-12"
    assert forecast[0]["qty"] == 100
    assert forecast[0]["kind"] == "forecast"


def test_build_forecast_months_ceil_partial_average():
    monthly = {"2025-06": 400}
    forecast = build_forecast_months(monthly, as_of_date=date(2025, 6, 30))
    assert len(forecast) == 6
    assert all(point["qty"] == 67 for point in forecast)


def test_build_forecast_months_is_empty_after_december():
    monthly = {"2025-12": 100}
    assert build_forecast_months(monthly, as_of_date=date(2025, 12, 31)) == []


def test_build_chart_points_includes_actual_and_forecast():
    monthly = {"2025-01": 50, "2025-02": 70}
    points = build_chart_points(monthly, as_of_date=date(2025, 2, 28))
    actual = [point for point in points if point["kind"] == "actual"]
    forecast = [point for point in points if point["kind"] == "forecast"]
    assert len(actual) == 2
    assert len(forecast) == 10
    assert forecast[-1]["yearMonth"] == "2025-12"
    assert all(point["qty"] == 60 for point in forecast)


def test_build_chart_points_fills_missing_months_with_zero():
    monthly = {"2025-01": 50, "2025-03": 70}
    points = build_chart_points(monthly, as_of_date=date(2025, 3, 31))
    assert [point["yearMonth"] for point in points[:3]] == ["2025-01", "2025-02", "2025-03"]
    assert points[1]["qty"] == 0
    assert points[1]["kind"] == "actual"


def test_expand_continuous_monthly_points():
    points = [
        {"yearMonth": "2025-01", "qty": 10, "kind": "actual"},
        {"yearMonth": "2025-03", "qty": 30, "kind": "forecast"},
    ]
    expanded = expand_continuous_monthly_points(points, as_of_date=date(2025, 2, 28))
    assert [point["yearMonth"] for point in expanded] == ["2025-01", "2025-02", "2025-03"]
    assert expanded[1]["qty"] == 0
    assert expanded[1]["kind"] == "actual"
