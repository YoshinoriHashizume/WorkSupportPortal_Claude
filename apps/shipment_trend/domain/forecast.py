from __future__ import annotations

import math
from datetime import date

from apps.shipment_trend.domain.fiscal_year import add_months, year_month_to_date


def current_year_month(as_of_date: date) -> str:
    return f"{as_of_date.year:04d}-{as_of_date.month:02d}"


def sum_current_year_through_month(monthly: dict[str, int], *, as_of_date: date) -> int:
    """集計基準日の暦年で、1月〜基準月までの出荷数量合計。"""
    current_year = as_of_date.year
    return sum(
        int(monthly.get(f"{current_year:04d}-{month:02d}", 0))
        for month in range(1, as_of_date.month + 1)
    )


def average_of_current_year(monthly: dict[str, int], *, as_of_date: date) -> float:
    """当年1月〜基準月の出荷合計を経過月数で割った月平均。"""
    if as_of_date.month <= 0:
        return 0.0
    total = sum_current_year_through_month(monthly, as_of_date=as_of_date)
    return total / as_of_date.month


def forecast_monthly_qty(monthly: dict[str, int], *, as_of_date: date) -> int:
    """残月予測の月次数量（月平均の切り上げ）。"""
    return math.ceil(average_of_current_year(monthly, as_of_date=as_of_date))


def remaining_calendar_year_months(as_of_date: date) -> int:
    """集計基準日の翌月から当該暦年12月までの月数。"""
    return max(0, 12 - as_of_date.month)


def build_forecast_months(
    monthly: dict[str, int],
    *,
    as_of_date: date,
) -> list[dict[str, object]]:
    monthly_forecast_qty = forecast_monthly_qty(monthly, as_of_date=as_of_date)
    start = current_year_month(as_of_date)
    current_year = as_of_date.year
    forecast: list[dict[str, object]] = []
    for offset in range(1, remaining_calendar_year_months(as_of_date) + 1):
        year_month = add_months(start, offset)
        if year_month_to_date(year_month).year != current_year:
            break
        forecast.append(
            {
                "yearMonth": year_month,
                "qty": monthly_forecast_qty,
                "kind": "forecast",
            }
        )
    return forecast


def expand_continuous_monthly_points(
    points: list[dict[str, object]],
    *,
    as_of_date: date,
) -> list[dict[str, object]]:
    """最初の月から最後の月まで欠損月を qty=0 で埋め、月次連続の系列にする。"""
    if not points:
        return []
    by_month = {str(point["yearMonth"]): point for point in points}
    sorted_months = sorted(by_month.keys())
    first_month = sorted_months[0]
    last_month = sorted_months[-1]
    as_of_year_month = current_year_month(as_of_date)
    continuous: list[dict[str, object]] = []
    current = first_month
    while current <= last_month:
        if current in by_month:
            continuous.append(by_month[current])
        else:
            continuous.append(
                {
                    "yearMonth": current,
                    "qty": 0,
                    "kind": "forecast" if current > as_of_year_month else "actual",
                }
            )
        current = add_months(current, 1)
    return continuous


def build_chart_points(monthly: dict[str, int], *, as_of_date: date) -> list[dict[str, object]]:
    as_of_year_month = current_year_month(as_of_date)
    actual_points = [
        {
            "yearMonth": year_month,
            "qty": int(quantity),
            "kind": "actual",
        }
        for year_month, quantity in sorted(monthly.items())
        if year_month <= as_of_year_month
    ]
    combined = actual_points + build_forecast_months(monthly, as_of_date=as_of_date)
    return expand_continuous_monthly_points(combined, as_of_date=as_of_date)
