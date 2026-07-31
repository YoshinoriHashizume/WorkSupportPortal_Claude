from __future__ import annotations

import math
from decimal import Decimal

from application.shipment_trend.domain.value_objects.alert_tier import alert_row_class
from application.shipment_trend.domain.value_objects.app_settings import AppSettings
from application.shipment_trend.domain.value_objects.list_filter import ListFilterOptions
from application.shipment_trend.domain.value_objects.table_display import (
    DEFAULT_DIRECTION,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SORT,
    DEFAULT_SORT_SPECS,
    PAGE_SIZE_OPTIONS,
    SORTABLE_COLUMNS,
    SortSpec,
    format_baseline_fiscal_year,
    format_change_qty,
    format_change_rate,
    format_quantity,
)


def _json_value(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if value is None:
        return ""
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


def row_to_client_dict(row: dict[str, object], settings: AppSettings) -> dict[str, object]:
    change_rate = row.get("change_rate_pct")
    rate_value = float(change_rate) if change_rate is not None else None
    client_row = {key: _json_value(value) for key, value in row.items() if key != "monthly"}
    client_row["alertRowClass"] = alert_row_class(
        rate_value,
        decrease_threshold_pct=settings.decrease_threshold_pct,
        increase_threshold_pct=settings.increase_threshold_pct,
    )
    client_row["display"] = {
        "cust_chrg_psn_cd": str(row.get("cust_chrg_psn_cd") or ""),
        "cust_code": str(row.get("cust_code") or ""),
        "cust_name": str(row.get("cust_name") or ""),
        "item_cd": str(row.get("item_cd") or ""),
        "first_fiscal_year": format_baseline_fiscal_year(
            row.get("first_fiscal_year"),
            is_manual=bool(row.get("baseline_is_manual")),
        ),
        "change_rate_pct": format_change_rate(row.get("change_rate_pct")),
        "change_qty": format_change_qty(row.get("change_qty")),
        "first_fy_total": format_quantity(row.get("first_fy_total")),
        "prev_fy_total": format_quantity(row.get("prev_fy_total")),
        "current_fy_with_forecast_total": format_quantity(row.get("current_fy_with_forecast_total")),
    }
    return client_row


def _sort_specs_to_payload(specs: tuple[SortSpec, ...]) -> list[dict[str, str]]:
    return [{"column": spec.column, "direction": spec.direction} for spec in specs]


def _filter_options_to_payload(options: ListFilterOptions) -> dict[str, list[dict[str, str]]]:
    return {
        "custOptions": [{"value": option.value, "label": option.label} for option in options.cust_options],
        "custChrgPsnOptions": [
            {"value": option.value, "label": option.label} for option in options.cust_chrg_psn_options
        ],
        "itemCdOptions": list(options.item_cd_options),
    }


def build_list_client_payload(
    *,
    all_rows: list[dict[str, object]],
    filter_options: ListFilterOptions,
    settings: AppSettings,
) -> dict[str, object]:
    return {
        "rows": [row_to_client_dict(row, settings) for row in all_rows],
        "itemCdOptions": list(filter_options.item_cd_options),
        "filterOptions": _filter_options_to_payload(filter_options),
        "pageSizeOptions": list(PAGE_SIZE_OPTIONS),
        "defaultPageSize": DEFAULT_PAGE_SIZE,
        "sortableColumns": [{"key": key, "label": label} for key, label in SORTABLE_COLUMNS],
        "defaultSortSpecs": _sort_specs_to_payload(DEFAULT_SORT_SPECS),
        "decreaseThresholdPct": settings.decrease_threshold_pct,
        "increaseThresholdPct": settings.increase_threshold_pct,
    }
