from __future__ import annotations

from decimal import Decimal

from apps.inventory_order_alert.domain.confirmation import STATUS_CHOICES, confirmation_status_key
from apps.inventory_order_alert.domain.format_display import format_cell_display
from apps.inventory_order_alert.domain.list_filter import ListFilterOptions
from apps.inventory_order_alert.domain.row_display import display_alert_level, row_alert_class
from apps.inventory_order_alert.domain.table_display import (
    DEFAULT_DIRECTION,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SORT,
    PAGE_SIZE_OPTIONS,
    SORTABLE_COLUMNS,
    SortSpec,
)

DEFAULT_SORT_SPECS: tuple[SortSpec, ...] = (SortSpec(DEFAULT_SORT, DEFAULT_DIRECTION),)


def _json_value(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if value is None:
        return ""
    return value


def row_to_client_dict(row: dict[str, object]) -> dict[str, object]:
    client_row: dict[str, object] = {
        key: _json_value(value) for key, value in row.items()
    }
    client_row["alertRowClass"] = row_alert_class(row)
    client_row["confirmationStatusKey"] = confirmation_status_key(row)
    client_row["display"] = {
        column: (
            display_alert_level(row)
            if column == "alert_level"
            else format_cell_display(row.get(column, ""), column)
        )
        for column, _label in SORTABLE_COLUMNS
        if column != "confirmation_status"
    }
    return client_row


def _sort_specs_to_payload(specs: tuple[SortSpec, ...]) -> list[dict[str, str]]:
    return [{"column": spec.column, "direction": spec.direction} for spec in specs]


def _filter_options_to_payload(options: ListFilterOptions) -> dict[str, list[dict[str, str]]]:
    return {
        "custOptions": [
            {"value": option.value, "label": option.label} for option in options.cust_options
        ],
        "custChrgPsnOptions": [
            {"value": option.value, "label": option.label}
            for option in options.cust_chrg_psn_options
        ],
    }


def build_list_client_payload(
    *,
    all_rows: list[dict[str, object]],
    filter_options: ListFilterOptions,
    confirmation_status_choices: list[tuple[str, str]],
) -> dict[str, object]:
    return {
        "rows": [row_to_client_dict(row) for row in all_rows],
        "filterOptions": _filter_options_to_payload(filter_options),
        "confirmationStatusChoices": [
            {"value": value, "label": label} for value, label in confirmation_status_choices
        ],
        "pageSizeOptions": list(PAGE_SIZE_OPTIONS),
        "defaultPageSize": DEFAULT_PAGE_SIZE,
        "sortableColumns": [{"key": key, "label": label} for key, label in SORTABLE_COLUMNS],
        "defaultSortSpecs": _sort_specs_to_payload(DEFAULT_SORT_SPECS),
    }
