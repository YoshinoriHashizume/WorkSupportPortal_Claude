from __future__ import annotations

from application.shipment_trend.domain.value_objects.alert_tier import alert_row_class
from application.shipment_trend.domain.value_objects.app_settings import AppSettings
from application.shipment_trend.domain.value_objects.table_display import (
    format_baseline_fiscal_year,
    format_change_qty,
    format_change_rate,
    format_quantity,
)


def enrich_row(row: dict[str, object], settings: AppSettings) -> dict[str, object]:
    change_rate = row.get("change_rate_pct")
    rate_value = float(change_rate) if change_rate is not None else None
    return {
        **row,
        "alert_row_class": alert_row_class(
            rate_value,
            decrease_threshold_pct=settings.decrease_threshold_pct,
            increase_threshold_pct=settings.increase_threshold_pct,
        ),
        "display_change_rate_pct": format_change_rate(row.get("change_rate_pct")),
        "display_change_qty": format_change_qty(row.get("change_qty")),
        "display_first_fiscal_year": format_baseline_fiscal_year(
            row.get("first_fiscal_year"),
            is_manual=bool(row.get("baseline_is_manual")),
        ),
        "display_first_fy_total": format_quantity(row.get("first_fy_total")),
        "display_prev_fy_total": format_quantity(row.get("prev_fy_total")),
        "display_current_fy_with_forecast_total": format_quantity(row.get("current_fy_with_forecast_total")),
    }


def enrich_rows(rows: list[dict[str, object]], settings: AppSettings) -> list[dict[str, object]]:
    return [enrich_row(row, settings) for row in rows]
