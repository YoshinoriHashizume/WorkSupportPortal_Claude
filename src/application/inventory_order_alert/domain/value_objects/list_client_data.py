from __future__ import annotations

from decimal import Decimal

from application.inventory_order_alert.domain.value_objects.confirmation import STATUS_CHOICES, confirmation_status_key
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    DEFAULT_FLOW_AXIS,
    DEFAULT_LOW_FLOW_VALUE,
    EVALUATION_PERIODS,
    FLOW_AXIS_DORMANT,
    FLOW_AXIS_LABELS,
    FLOW_AXIS_LOW_FLOW,
    FLOW_QUADRANT_KEYS,
    FLOW_QUADRANT_LABELS,
    FLOW_QUADRANTS,
    format_responsible_departments,
)
from application.inventory_order_alert.domain.value_objects.format_display import format_cell_display
from application.inventory_order_alert.domain.value_objects.list_filter import ListFilterOptions
from application.inventory_order_alert.domain.value_objects.row_display import display_flow_quadrant, row_alert_class
from application.inventory_order_alert.domain.value_objects.stock_quantity import (
    format_stock_quantity,
    is_stock_fetched,
)
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


#: 未取得（キーなし）と該当なし（空）を区別して表示する在庫数の列。
STOCK_COLUMNS = ("stock_qty", "mari_stock_qty")


def _display_cell(row: dict[str, object], column: str, quadrant: str) -> str:
    if column == "flow_quadrant":
        return quadrant
    if column in STOCK_COLUMNS:
        return format_stock_quantity(
            row.get(column, ""),
            fetched=is_stock_fetched(row, column),
        )
    return format_cell_display(row.get(column, ""), column)


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
    quadrant = display_flow_quadrant(row)
    # 判定軸・判定期間の切り替えはクライアント側で `flowQuadrants` を引き直すだけにする（design.md §3.2 案B）。
    client_row["flowQuadrants"] = dict(row.get("flow_quadrants") or {})
    client_row["flowQuadrant"] = quadrant
    client_row["flowQuadrantKey"] = str(row.get("flow_quadrant_key") or FLOW_QUADRANT_KEYS[quadrant])
    client_row["noIncomingRecord"] = bool(row.get("no_incoming_record"))
    client_row["responsibleDepartment"] = str(row.get("responsible_department") or "")
    # 未取得（キーなし）を保つため、キーがある場合のみ配信する
    if "mari_stock_qty" in row:
        client_row["mariStockQty"] = _json_value(row.get("mari_stock_qty"))
    client_row["display"] = {
        column: _display_cell(row, column, quadrant)
        for column, _label in SORTABLE_COLUMNS
        if column != "confirmation_status"
    }
    return client_row


def _flow_periods_payload() -> dict[str, list[dict[str, object]]]:
    return {
        axis: [
            {"value": period.value, "key": period.key, "label": period.label}
            for period in EVALUATION_PERIODS.for_axis(axis)
        ]
        for axis in (FLOW_AXIS_LOW_FLOW, FLOW_AXIS_DORMANT)
    }


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
        "flowAxes": [
            {"value": axis, "label": FLOW_AXIS_LABELS[axis]}
            for axis in (FLOW_AXIS_LOW_FLOW, FLOW_AXIS_DORMANT)
        ],
        "flowPeriods": _flow_periods_payload(),
        "flowQuadrantLabels": dict(FLOW_QUADRANT_LABELS),
        # 判定軸を切り替えると行の責任部署も変わるため、区分ごとの対応表をクライアントへ渡す。
        "flowQuadrantDepartments": {
            FLOW_QUADRANT_KEYS[quadrant]: format_responsible_departments(quadrant)
            for quadrant in FLOW_QUADRANTS
        },
        "flowQuadrantOrder": [FLOW_QUADRANT_KEYS[quadrant] for quadrant in FLOW_QUADRANTS],
        "defaultFlowSelection": {"axis": DEFAULT_FLOW_AXIS, "period": DEFAULT_LOW_FLOW_VALUE},
    }
