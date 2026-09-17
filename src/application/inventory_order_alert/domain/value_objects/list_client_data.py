from __future__ import annotations

from decimal import Decimal

from application.inventory_order_alert.domain.value_objects.confirmation import STATUS_CHOICES, confirmation_status_key
from application.inventory_order_alert.domain.value_objects.demand_forecast import BASIS_NONE
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    DEFAULT_EVALUATION_PERIOD,
    EVALUATION_PERIODS,
    FLOW_QUADRANT_KEYS,
    FLOW_QUADRANT_LABELS,
    FLOW_QUADRANTS,
    RESPONSIBLE_DEPARTMENT_SEPARATOR,
)
from application.inventory_order_alert.domain.value_objects.format_display import format_cell_display
from application.inventory_order_alert.domain.value_objects.list_filter import ListFilterOptions
from application.inventory_order_alert.domain.value_objects.recommended_action import (
    DEFAULT_RECOMMENDED_ACTIONS,
    RecommendedActions,
)
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
    SORT_ONLY_COLUMNS,
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
    # 判定期間の切り替えはクライアント側で `flowQuadrants`（Y1/Y3/Y5）を引き直すだけにする（05 design §3.1）。
    client_row["flowQuadrants"] = dict(row.get("flow_quadrants") or {})
    client_row["flowQuadrant"] = quadrant
    client_row["flowQuadrantKey"] = str(row.get("flow_quadrant_key") or FLOW_QUADRANT_KEYS[quadrant])
    client_row["noIncomingRecord"] = bool(row.get("no_incoming_record"))
    client_row["flowStatus"] = str(row.get("flow_status") or "")
    client_row["recommendedAction"] = str(row.get("recommended_action") or "")
    client_row["responsibleDepartment"] = str(row.get("responsible_department") or "")
    # 第 2 段階（05 design §6.2）: 需要予測。旧スナップショット（キーなし）は basis「なし」で値は空
    client_row["internalItemCd"] = str(row.get("internal_item_cd") or "")
    client_row["unconfirmedOrderTrend"] = list(row.get("unconfirmed_order_trend") or [])
    client_row["reconciliationUnitKey"] = str(row.get("reconciliation_unit_key") or "")
    client_row["demandForecast"] = _demand_forecast_payload(row)
    # MARI 在庫は行の生値（mari_stock_qty）がソートに、display が表示に使われる。
    # camelCase の別名は増やさない（同じ値を二重に配信することになるため。design.md §6.4）。
    client_row["display"] = {
        column: _display_cell(row, column, quadrant)
        for column, _label in SORTABLE_COLUMNS
        if column != "confirmation_status"
    }
    return client_row


def _optional_number(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _demand_forecast_payload(row: dict[str, object]) -> dict[str, object]:
    basis = str(row.get("demand_forecast_basis") or BASIS_NONE)
    monthly = row.get("demand_forecast_monthly")
    stockout = row.get("stockout_forecast_month")
    return {
        "basis": basis,
        "currentMonthRemaining": int(row.get("demand_forecast_current_month_remaining") or 0),
        "monthly": [int(qty) for qty in monthly] if isinstance(monthly, list) and len(monthly) == 3 else [0, 0, 0],
        "monthlyAverage": _optional_number(row.get("demand_forecast_monthly_average")) or 0.0,
        "stockTotal": _optional_number(row.get("demand_forecast_stock_total")),
        "monthsOfStock": _optional_number(row.get("months_of_stock")),
        "stockoutForecastMonth": str(stockout) if stockout else None,
    }


def _evaluation_periods_payload() -> list[dict[str, object]]:
    return [
        {"years": period.years, "key": period.key, "label": period.label}
        for period in EVALUATION_PERIODS
    ]


def _recommended_actions_payload(recommended_actions: RecommendedActions) -> dict[str, dict[str, str]]:
    """流動区分キー → 状況テンプレート・推奨アクション・責任部署（05 design §6.2）。"""
    return {
        action.key: {
            "statusTemplate": action.status_template,
            "action": action.action,
            "departments": RESPONSIBLE_DEPARTMENT_SEPARATOR.join(action.departments),
        }
        for action in recommended_actions
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
    recommended_actions: RecommendedActions = DEFAULT_RECOMMENDED_ACTIONS,
) -> dict[str, object]:
    actions_payload = _recommended_actions_payload(recommended_actions)
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
        "sortOnlyColumns": [{"key": key, "label": label} for key, label in SORT_ONLY_COLUMNS],
        "defaultSortSpecs": _sort_specs_to_payload(DEFAULT_SORT_SPECS),
        "evaluationPeriods": _evaluation_periods_payload(),
        "defaultPeriodKey": DEFAULT_EVALUATION_PERIOD.key,
        "flowQuadrantLabels": dict(FLOW_QUADRANT_LABELS),
        "flowQuadrantDepartments": {key: entry["departments"] for key, entry in actions_payload.items()},
        "flowQuadrantOrder": [FLOW_QUADRANT_KEYS[quadrant] for quadrant in FLOW_QUADRANTS],
        "recommendedActions": actions_payload,
    }
