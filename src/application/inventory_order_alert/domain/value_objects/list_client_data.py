from __future__ import annotations

from decimal import Decimal

from application.inventory_order_alert.domain.value_objects.confirmation import STATUS_CHOICES, confirmation_status_key
from application.inventory_order_alert.domain.value_objects.format_display import format_cell_display
from application.inventory_order_alert.domain.value_objects.list_filter import ListFilterOptions
from application.inventory_order_alert.domain.value_objects.row_display import display_alert_level, row_alert_class
from application.inventory_order_alert.domain.value_objects.table_display import (
    DEFAULT_DIRECTION,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SORT,
    PAGE_SIZE_OPTIONS,
    SORTABLE_COLUMNS,
    SortSpec,
)

DEFAULT_SORT_SPECS: tuple[SortSpec, ...] = (SortSpec(DEFAULT_SORT, DEFAULT_DIRECTION),)
ROW_KEY_SEPARATOR = "|"


def build_row_key(cust_code: str, item_cd: str) -> str:
    cust = str(cust_code or "").strip()
    item = str(item_cd or "").strip()
    if not cust or not item:
        return ""
    return f"{cust}{ROW_KEY_SEPARATOR}{item}"


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
    cust_code = str(row.get("cust_code") or "").strip()
    item_cd = str(row.get("item_cd") or "").strip()
    client_row["cust_code"] = cust_code
    client_row["item_cd"] = item_cd
    client_row["rowKey"] = build_row_key(cust_code, item_cd)
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


def _filter_options_to_payload(options: ListFilterOptions) -> dict[str, object]:
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
        "itemCdOptions": list(filter_options.item_cd_options),
        "level1ItemCdOptions": list(filter_options.level1_item_cd_options),
        "confirmationStatusChoices": [
            {"value": value, "label": label} for value, label in confirmation_status_choices
        ],
        "pageSizeOptions": list(PAGE_SIZE_OPTIONS),
        "defaultPageSize": DEFAULT_PAGE_SIZE,
        "sortableColumns": [{"key": key, "label": label} for key, label in SORTABLE_COLUMNS],
        "defaultSortSpecs": _sort_specs_to_payload(DEFAULT_SORT_SPECS),
    }
