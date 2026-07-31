from __future__ import annotations

from datetime import date

from application.shipment_trend.domain.value_objects.app_settings import AppSettings
from application.shipment_trend.domain.value_objects.chart_data import build_chart_payload


def test_build_chart_payload_includes_all_fiscal_years():
    row = {
        "cust_code": "101",
        "cust_name": "テスト得意先",
        "cust_chrg_psn_cd": "A01",
        "item_cd": "ITEM-1",
        "monthly": {
            "2023-04": 100,
            "2024-04": 80,
            "2025-04": 200,
        },
    }
    payload = build_chart_payload(
        row,
        as_of_date=date(2025, 6, 1),
        settings=AppSettings(decrease_threshold_pct=20, increase_threshold_pct=20),
    )
    assert payload["custCode"] == "101"
    assert payload["custName"] == "テスト得意先"
    assert payload["custChrgPsnCd"] == "A01"
    assert len(payload["fiscalYears"]) == 3
    assert payload["fiscalYears"][0]["fiscalYear"] == 2023
    assert payload["fiscalYears"][2]["isCurrentYear"] is True
    assert payload["fiscalYears"][2]["fyWithForecastTotal"] >= payload["fiscalYears"][2]["fyTotal"]
    assert payload["availableBaselineYears"] == [2023, 2024, 2025]
    assert payload["baselineFiscalYear"] == 2023
    assert payload["baselineIsManual"] is False
    assert payload["regression"] is not None
    assert "slope" in payload["regression"]
    assert "rSquared" in payload["regression"]
    assert len(payload["regression"]["points"]) == len(payload["points"])
    assert payload["yearPoints"]
    assert payload["yearPoints"][0]["yearMonth"] == "2023"
    assert payload["yearRegression"] is not None


def test_build_chart_payload_applies_manual_baseline():
    row = {
        "cust_code": "101",
        "cust_name": "テスト得意先",
        "cust_chrg_psn_cd": "A01",
        "item_cd": "ITEM-1",
        "monthly": {
            "2023-04": 10,
            "2024-04": 100,
            "2025-04": 200,
        },
    }
    payload = build_chart_payload(
        row,
        as_of_date=date(2025, 6, 1),
        settings=AppSettings(decrease_threshold_pct=20, increase_threshold_pct=20),
        baseline_fiscal_year=2024,
    )
    assert payload["dataFirstFiscalYear"] == 2023
    assert payload["baselineFiscalYear"] == 2024
    assert payload["baselineIsManual"] is True
    assert payload["firstFyTotal"] == 100
    assert payload["points"]
    assert all(str(point["yearMonth"]) >= "2024-01" for point in payload["points"])
    assert payload["points"][0]["yearMonth"] == "2024-01"
    assert payload["regression"] is not None
    assert len(payload["regression"]["points"]) == len(payload["points"])
    assert payload["yearPoints"]
    assert [point["yearMonth"] for point in payload["yearPoints"]] == ["2024", "2025"]
    assert payload["yearPoints"][0]["kind"] == "actual"
    assert payload["yearPoints"][-1]["kind"] == "forecast"
    assert payload["yearRegression"] is not None
    assert len(payload["yearRegression"]["points"]) == len(payload["yearPoints"])


def test_build_year_chart_points_skips_years_before_baseline():
    from application.shipment_trend.domain.value_objects.chart_data import build_year_chart_points

    rows = [
        {"fiscal_year": 2023, "fy_total": 10, "fy_with_forecast_total": 10, "is_current_year": False},
        {"fiscal_year": 2024, "fy_total": 20, "fy_with_forecast_total": 20, "is_current_year": False},
        {"fiscal_year": 2025, "fy_total": 30, "fy_with_forecast_total": 40, "is_current_year": True},
    ]
    points = build_year_chart_points(rows, baseline_fiscal_year=2024)
    assert [point["qty"] for point in points] == [20, 40]
    assert points[-1]["kind"] == "forecast"


def test_filter_chart_points_from_baseline_year():
    from application.shipment_trend.domain.value_objects.chart_data import filter_chart_points_from_baseline_year

    points = [
        {"yearMonth": "2023-04", "qty": 1},
        {"yearMonth": "2024-01", "qty": 2},
        {"yearMonth": "2024-02", "qty": 3},
    ]
    assert filter_chart_points_from_baseline_year(points, baseline_fiscal_year=None) == points
    filtered = filter_chart_points_from_baseline_year(points, baseline_fiscal_year=2024)
    assert [point["yearMonth"] for point in filtered] == ["2024-01", "2024-02"]
