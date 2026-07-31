from __future__ import annotations

from datetime import date

from application.shipment_trend.domain.value_objects.app_settings import AppSettings
from application.shipment_trend.domain.value_objects.forecast import build_chart_points
from application.shipment_trend.domain.value_objects.least_squares import compute_least_squares_regression
from application.shipment_trend.domain.value_objects.trend_metrics import (
    available_baseline_years,
    compute_fiscal_year_rows,
    compute_trend_metrics,
)


def find_row(
    rows: list[dict[str, object]],
    *,
    cust_code: str,
    item_cd: str,
) -> dict[str, object] | None:
    for row in rows:
        if str(row.get("cust_code") or "").strip() == cust_code and str(row.get("item_cd") or "").strip() == item_cd:
            return row
    return None


def filter_chart_points_from_baseline_year(
    points: list[dict[str, object]],
    *,
    baseline_fiscal_year: int | None,
) -> list[dict[str, object]]:
    """比較基準年の1月からグラフ系列を開始する（未指定時は全期間）。"""
    if baseline_fiscal_year is None or not points:
        return points
    start_year_month = f"{int(baseline_fiscal_year):04d}-01"
    return [point for point in points if str(point.get("yearMonth") or "") >= start_year_month]


def build_year_chart_points(
    fiscal_year_rows: list[dict[str, object]],
    *,
    baseline_fiscal_year: int | None,
) -> list[dict[str, object]]:
    """年度別のグラフ点。比較基準年以降のみ。集計基準年は予測込み合計。"""
    points: list[dict[str, object]] = []
    for row in fiscal_year_rows:
        year = int(row["fiscal_year"])
        if baseline_fiscal_year is not None and year < int(baseline_fiscal_year):
            continue
        is_current = bool(row.get("is_current_year"))
        qty = int(row["fy_with_forecast_total"] if is_current else row["fy_total"])
        points.append(
            {
                "yearMonth": f"{year:04d}",
                "fiscalYear": year,
                "qty": qty,
                "kind": "forecast" if is_current else "actual",
            }
        )
    return points


def _regression_payload(points: list[dict[str, object]]) -> dict[str, object] | None:
    regression = compute_least_squares_regression(points)
    if regression is None:
        return None
    return {
        "slope": regression["slope"],
        "intercept": regression["intercept"],
        "rSquared": regression["r_squared"],
        "points": [
            {
                "yearMonth": point["yearMonth"],
                "qty": point["qty"],
                "kind": "regression",
            }
            for point in regression["regression_points"]
        ],
    }


def build_chart_payload(
    row: dict[str, object],
    *,
    as_of_date: date,
    settings: AppSettings,
    baseline_fiscal_year: int | None = None,
) -> dict[str, object]:
    monthly = row.get("monthly") or {}
    if not isinstance(monthly, dict):
        monthly = {}
    monthly_int = {str(key): int(value) for key, value in monthly.items()}
    metrics = compute_trend_metrics(
        monthly_int,
        as_of_date,
        baseline_fiscal_year=baseline_fiscal_year,
    )
    fiscal_years = compute_fiscal_year_rows(
        monthly_int,
        as_of_date,
        baseline_fiscal_year=baseline_fiscal_year,
    )
    effective_baseline = metrics.get("first_fiscal_year")
    baseline_year_int = int(effective_baseline) if effective_baseline is not None else None
    points = filter_chart_points_from_baseline_year(
        build_chart_points(monthly_int, as_of_date=as_of_date),
        baseline_fiscal_year=baseline_year_int,
    )
    year_points = build_year_chart_points(
        fiscal_years,
        baseline_fiscal_year=baseline_year_int,
    )
    fiscal_years_payload = [
        {
            "fiscalYear": year_row["fiscal_year"],
            "fyTotal": year_row["fy_total"],
            "fyWithForecastTotal": year_row["fy_with_forecast_total"],
            "changeQty": year_row["change_qty"],
            "changeRatePct": year_row["change_rate_pct"],
            "isFirstYear": year_row["is_first_year"],
            "isCurrentYear": year_row["is_current_year"],
        }
        for year_row in fiscal_years
    ]
    return {
        "custCode": row.get("cust_code", ""),
        "custName": row.get("cust_name", ""),
        "custChrgPsnCd": row.get("cust_chrg_psn_cd", ""),
        "itemCd": row.get("item_cd", ""),
        "points": points,
        "yearPoints": year_points,
        "firstFiscalYear": metrics.get("first_fiscal_year"),
        "dataFirstFiscalYear": metrics.get("data_first_fiscal_year"),
        "baselineFiscalYear": metrics.get("first_fiscal_year"),
        "baselineIsManual": metrics.get("baseline_is_manual"),
        "availableBaselineYears": available_baseline_years(monthly_int, as_of_date),
        "currentFiscalYear": metrics.get("current_fiscal_year"),
        "firstFyTotal": metrics.get("first_fy_total"),
        "currentFyTotal": metrics.get("current_fy_total"),
        "changeQty": metrics.get("change_qty"),
        "changeRatePct": metrics.get("change_rate_pct"),
        "regression": _regression_payload(points),
        "yearRegression": _regression_payload(year_points),
        "fiscalYears": fiscal_years_payload,
        "decreaseThresholdPct": settings.decrease_threshold_pct,
        "increaseThresholdPct": settings.increase_threshold_pct,
    }
