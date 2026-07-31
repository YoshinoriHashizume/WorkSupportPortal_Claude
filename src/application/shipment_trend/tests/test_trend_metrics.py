from __future__ import annotations

from datetime import date

from application.shipment_trend.domain.value_objects.trend_metrics import (
    compute_current_fy_with_forecast_total,
    compute_fiscal_year_rows,
    compute_trend_metrics,
    hydrate_row_metrics,
    hydrate_rows_metrics,
)


def test_compute_trend_metrics_first_and_current_fy():
    monthly = {
        "2023-04": 100,
        "2023-05": 50,
        "2024-04": 80,
        "2025-04": 200,
        "2025-05": 100,
    }
    metrics = compute_trend_metrics(monthly, date(2025, 6, 15))
    assert metrics["first_fiscal_year"] == 2023
    assert metrics["current_fiscal_year"] == 2025
    assert metrics["first_fy_total"] == 150
    assert metrics["prev_fy_total"] == 80
    assert metrics["current_fy_total"] == 300
    assert metrics["current_fy_with_forecast_total"] > 300
    assert metrics["change_qty"] == metrics["current_fy_with_forecast_total"] - 150
    assert metrics["change_rate_pct"] == round(metrics["change_qty"] / 150 * 100, 2)


def test_compute_trend_metrics_zero_first_year():
    monthly = {"2025-04": 10}
    metrics = compute_trend_metrics(monthly, date(2025, 12, 31))
    assert metrics["first_fy_total"] == 10
    assert metrics["change_rate_pct"] == 0.0
    assert metrics["prev_fy_total"] == 0


def test_compute_current_fy_with_forecast_total_includes_remaining_calendar_year_months():
    monthly = {
        "2025-04": 100,
        "2025-05": 50,
    }
    total = compute_current_fy_with_forecast_total(monthly, date(2025, 5, 31))
    # 実績 150 + 2025年残月（6〜12月）7か月 × ceil(150/5)=30
    assert total == 150 + 30 * 7


def test_compute_current_fy_with_forecast_total_excludes_prior_year_from_average():
    monthly = {
        "2024-12": 1000,
        "2025-04": 100,
        "2025-05": 50,
    }
    total = compute_current_fy_with_forecast_total(monthly, date(2025, 5, 31))
    # 実績 150 + 残月7か月 × ceil(150/5)=30（2024-12は含めない）
    assert total == 150 + 30 * 7


def test_hydrate_row_metrics_recomputes_missing_snapshot_fields():
    row = {
        "cust_code": "101",
        "item_cd": "ITEM-1",
        "first_fy_total": 999,
        "prev_fy_total": 0,
        "current_fy_with_forecast_total": 0,
        "monthly": {"2024-06": 80, "2025-04": 200, "2025-05": 100},
    }
    hydrated = hydrate_row_metrics(row, date(2025, 6, 15))
    assert hydrated["prev_fy_total"] == 80
    assert hydrated["current_fy_total"] == 300
    assert hydrated["current_fy_with_forecast_total"] > 300


def test_compute_fiscal_year_rows_compares_against_first_year_current_uses_forecast():
    monthly = {
        "2023-04": 100,
        "2023-05": 50,
        "2024-04": 80,
        "2025-04": 200,
        "2025-05": 100,
    }
    as_of_date = date(2025, 6, 15)
    rows = compute_fiscal_year_rows(monthly, as_of_date)
    current_with_forecast = compute_current_fy_with_forecast_total(monthly, as_of_date)
    assert [row["fiscal_year"] for row in rows] == [2023, 2024, 2025]
    assert rows[0]["fy_total"] == 150
    assert rows[0]["change_qty"] == 0
    assert rows[0]["change_rate_pct"] == 0.0
    assert rows[1]["fy_total"] == 80
    assert rows[1]["change_qty"] == -70
    assert rows[1]["change_rate_pct"] == round(-70 / 150 * 100, 2)
    assert rows[2]["fy_total"] == 300
    assert rows[2]["fy_with_forecast_total"] == current_with_forecast
    assert rows[2]["change_qty"] == current_with_forecast - 150
    assert rows[2]["change_rate_pct"] == round((current_with_forecast - 150) / 150 * 100, 2)
    assert rows[2]["is_current_year"] is True


def test_compute_trend_metrics_uses_manual_baseline_year():
    monthly = {
        "2023-04": 10,
        "2024-04": 100,
        "2025-04": 200,
    }
    metrics = compute_trend_metrics(monthly, date(2025, 6, 15), baseline_fiscal_year=2024)
    assert metrics["data_first_fiscal_year"] == 2023
    assert metrics["first_fiscal_year"] == 2024
    assert metrics["baseline_is_manual"] is True
    assert metrics["first_fy_total"] == 100
    assert metrics["change_qty"] == metrics["current_fy_with_forecast_total"] - 100


def test_hydrate_rows_metrics_applies_baseline_overrides():
    rows = [
        {
            "cust_code": "101",
            "item_cd": "ITEM-1",
            "monthly": {"2023-04": 10, "2024-04": 100, "2025-04": 200},
        }
    ]
    hydrated = hydrate_rows_metrics(
        rows,
        date(2025, 6, 15),
        baseline_overrides={("101", "ITEM-1"): 2024},
    )
    assert hydrated[0]["first_fiscal_year"] == 2024
    assert hydrated[0]["baseline_is_manual"] is True
    assert hydrated[0]["data_first_fiscal_year"] == 2023


def test_available_baseline_years_excludes_future_years():
    from application.shipment_trend.domain.value_objects.trend_metrics import available_baseline_years

    monthly = {"2023-01": 1, "2024-01": 2, "2026-01": 3}
    assert available_baseline_years(monthly, date(2025, 6, 1)) == [2023, 2024]


def test_compute_fiscal_year_rows_with_manual_baseline():
    monthly = {
        "2023-04": 100,
        "2024-04": 50,
        "2025-04": 200,
    }
    rows = compute_fiscal_year_rows(monthly, date(2025, 6, 15), baseline_fiscal_year=2024)
    assert rows[0]["is_first_year"] is False
    assert rows[1]["is_first_year"] is True
    assert rows[1]["change_qty"] == 0
    assert rows[2]["change_qty"] == rows[2]["fy_with_forecast_total"] - 50
