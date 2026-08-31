from __future__ import annotations

from datetime import date

from application.shipment_trend.domain.value_objects.forecast import build_forecast_months, current_year_month
from application.shipment_trend.domain.value_objects.fiscal_year import fiscal_year_of, year_month_to_date


def sum_fiscal_year(monthly: dict[str, int], fiscal_year: int) -> int:
    total = 0
    for year_month, quantity in monthly.items():
        if fiscal_year_of(year_month_to_date(year_month)) == fiscal_year:
            total += int(quantity)
    return total


def data_first_fiscal_year(monthly: dict[str, int]) -> int | None:
    if not monthly:
        return None
    first_year_month = min(monthly.keys())
    return fiscal_year_of(year_month_to_date(first_year_month))


def available_baseline_years(monthly: dict[str, int], as_of_date: date) -> list[int]:
    """比較基準年の候補（出荷がある暦年かつ集計基準年以下）。"""
    if not monthly:
        return []
    current_year = fiscal_year_of(as_of_date)
    years = {
        fiscal_year_of(year_month_to_date(year_month))
        for year_month in monthly.keys()
        if fiscal_year_of(year_month_to_date(year_month)) <= current_year
    }
    return sorted(years)


def resolve_baseline_fiscal_year(
    monthly: dict[str, int],
    *,
    baseline_fiscal_year: int | None,
) -> tuple[int | None, int | None, bool]:
    """(比較基準年, データ初年度, 手動設定か) を返す。"""
    data_first = data_first_fiscal_year(monthly)
    if data_first is None:
        return None, None, False
    if baseline_fiscal_year is None:
        return data_first, data_first, False
    return int(baseline_fiscal_year), data_first, True


def compute_current_fy_with_forecast_total(monthly: dict[str, int], as_of_date: date) -> int:
    current_fiscal_year = fiscal_year_of(as_of_date)
    as_of_year_month = current_year_month(as_of_date)
    actual_total = sum(
        int(quantity)
        for year_month, quantity in monthly.items()
        if fiscal_year_of(year_month_to_date(year_month)) == current_fiscal_year
        and year_month <= as_of_year_month
    )
    forecast_total = sum(
        int(point["qty"])
        for point in build_forecast_months(monthly, as_of_date=as_of_date)
        if fiscal_year_of(year_month_to_date(str(point["yearMonth"]))) == current_fiscal_year
    )
    return actual_total + forecast_total


def compute_trend_metrics(
    monthly: dict[str, int],
    as_of_date: date,
    *,
    baseline_fiscal_year: int | None = None,
) -> dict[str, object]:
    current_fiscal_year = fiscal_year_of(as_of_date)
    if not monthly:
        return {
            "first_fiscal_year": None,
            "data_first_fiscal_year": None,
            "baseline_is_manual": False,
            "current_fiscal_year": current_fiscal_year,
            "first_fy_total": 0,
            "prev_fy_total": 0,
            "current_fy_total": 0,
            "current_fy_with_forecast_total": 0,
            "change_qty": 0,
            "change_rate_pct": None,
        }

    effective_baseline, data_first, baseline_is_manual = resolve_baseline_fiscal_year(
        monthly,
        baseline_fiscal_year=baseline_fiscal_year,
    )
    assert effective_baseline is not None
    prev_fiscal_year = current_fiscal_year - 1
    first_fy_total = sum_fiscal_year(monthly, effective_baseline)
    prev_fy_total = sum_fiscal_year(monthly, prev_fiscal_year)
    current_fy_total = sum_fiscal_year(monthly, current_fiscal_year)
    current_fy_with_forecast_total = compute_current_fy_with_forecast_total(monthly, as_of_date)
    change_qty = current_fy_with_forecast_total - first_fy_total
    if first_fy_total > 0:
        change_rate_pct = round(change_qty / first_fy_total * 100, 2)
    elif current_fy_with_forecast_total > 0:
        change_rate_pct = None
    else:
        change_rate_pct = 0.0

    return {
        "first_fiscal_year": effective_baseline,
        "data_first_fiscal_year": data_first,
        "baseline_is_manual": baseline_is_manual,
        "current_fiscal_year": current_fiscal_year,
        "first_fy_total": first_fy_total,
        "prev_fy_total": prev_fy_total,
        "current_fy_total": current_fy_total,
        "current_fy_with_forecast_total": current_fy_with_forecast_total,
        "change_qty": change_qty,
        "change_rate_pct": change_rate_pct,
    }


def _normalize_monthly(monthly: object) -> dict[str, int]:
    if not isinstance(monthly, dict):
        return {}
    return {str(key): int(value) for key, value in monthly.items()}


def _row_key(row: dict[str, object]) -> tuple[str, str]:
    return (str(row.get("cust_code") or "").strip(), str(row.get("item_cd") or "").strip())


def hydrate_row_metrics(
    row: dict[str, object],
    as_of_date: date,
    *,
    baseline_fiscal_year: int | None = None,
) -> dict[str, object]:
    """スナップショット行の monthly から指標を再計算する（旧データ互換・暦年変更反映）。"""
    monthly = _normalize_monthly(row.get("monthly"))
    if not monthly:
        return row
    metrics = compute_trend_metrics(
        monthly,
        as_of_date,
        baseline_fiscal_year=baseline_fiscal_year,
    )
    return {**row, **metrics}


def hydrate_rows_metrics(
    rows: list[dict[str, object]],
    as_of_date: date | None,
    *,
    baseline_overrides: dict[tuple[str, str], int] | None = None,
) -> list[dict[str, object]]:
    if as_of_date is None:
        return rows
    overrides = baseline_overrides or {}
    hydrated: list[dict[str, object]] = []
    for row in rows:
        key = _row_key(row)
        hydrated.append(
            hydrate_row_metrics(
                row,
                as_of_date,
                baseline_fiscal_year=overrides.get(key),
            )
        )
    return hydrated


def _change_metrics_vs_first_year(
    *,
    fiscal_year: int,
    first_fiscal_year: int,
    first_fy_total: int,
    compare_total: int,
) -> tuple[int, float | None]:
    if fiscal_year == first_fiscal_year:
        if first_fy_total > 0:
            return 0, 0.0
        return 0, None
    change_qty = compare_total - first_fy_total
    if first_fy_total > 0:
        return change_qty, round(change_qty / first_fy_total * 100, 2)
    if compare_total > 0:
        return change_qty, None
    return change_qty, 0.0


def compute_fiscal_year_rows(
    monthly: dict[str, int],
    as_of_date: date,
    *,
    baseline_fiscal_year: int | None = None,
) -> list[dict[str, object]]:
    """データ初年度から集計基準年までの各暦年の出荷合計と比較基準年比変動を返す。"""
    if not monthly:
        return []

    base_metrics = compute_trend_metrics(
        monthly,
        as_of_date,
        baseline_fiscal_year=baseline_fiscal_year,
    )
    first_fiscal_year = int(base_metrics["first_fiscal_year"])
    first_fy_total = int(base_metrics["first_fy_total"])
    current_fiscal_year = int(base_metrics["current_fiscal_year"])
    current_fy_with_forecast_total = int(base_metrics["current_fy_with_forecast_total"])
    shipment_years = {
        fiscal_year_of(year_month_to_date(year_month)) for year_month in monthly.keys()
    }
    fiscal_years = list(range(min(shipment_years), current_fiscal_year + 1))

    rows: list[dict[str, object]] = []
    for fiscal_year in fiscal_years:
        fy_total = sum_fiscal_year(monthly, fiscal_year)
        if fiscal_year == current_fiscal_year:
            fy_with_forecast_total = current_fy_with_forecast_total
        else:
            fy_with_forecast_total = fy_total
        compare_total = fy_with_forecast_total
        change_qty, change_rate_pct = _change_metrics_vs_first_year(
            fiscal_year=fiscal_year,
            first_fiscal_year=first_fiscal_year,
            first_fy_total=first_fy_total,
            compare_total=compare_total,
        )
        rows.append(
            {
                "fiscal_year": fiscal_year,
                "fy_total": fy_total,
                "fy_with_forecast_total": fy_with_forecast_total,
                "change_qty": change_qty,
                "change_rate_pct": change_rate_pct,
                "is_first_year": fiscal_year == first_fiscal_year,
                "is_current_year": fiscal_year == current_fiscal_year,
            }
        )
    return rows
