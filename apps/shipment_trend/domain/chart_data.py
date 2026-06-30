from __future__ import annotations

from datetime import date

from apps.shipment_trend.domain.app_settings import AppSettings
from apps.shipment_trend.domain.forecast import build_chart_points
from apps.shipment_trend.domain.trend_metrics import compute_fiscal_year_rows, compute_trend_metrics


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


def build_chart_payload(
    row: dict[str, object],
    *,
    as_of_date: date,
    settings: AppSettings,
) -> dict[str, object]:
    monthly = row.get("monthly") or {}
    if not isinstance(monthly, dict):
        monthly = {}
    monthly_int = {str(key): int(value) for key, value in monthly.items()}
    metrics = compute_trend_metrics(monthly_int, as_of_date)
    fiscal_years = compute_fiscal_year_rows(monthly_int, as_of_date)
    return {
        "custCode": row.get("cust_code", ""),
        "custName": row.get("cust_name", ""),
        "custChrgPsnCd": row.get("cust_chrg_psn_cd", ""),
        "itemCd": row.get("item_cd", ""),
        "points": build_chart_points(monthly_int, as_of_date=as_of_date),
        "firstFiscalYear": metrics.get("first_fiscal_year"),
        "currentFiscalYear": metrics.get("current_fiscal_year"),
        "firstFyTotal": metrics.get("first_fy_total"),
        "currentFyTotal": metrics.get("current_fy_total"),
        "changeQty": metrics.get("change_qty"),
        "changeRatePct": metrics.get("change_rate_pct"),
        "fiscalYears": [
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
        ],
        "decreaseThresholdPct": settings.decrease_threshold_pct,
        "increaseThresholdPct": settings.increase_threshold_pct,
    }
