from __future__ import annotations

from decimal import Decimal

from application.inventory_order_alert.domain.value_objects.confirmation import STATUS_CHOICES, confirmation_status_key
from application.inventory_order_alert.domain.value_objects.demand_forecast import BASIS_NONE
from application.inventory_order_alert.domain.value_objects.ordering_profile import ORDERING_METHOD_KEYS, ORDERING_UNKNOWN
from application.inventory_order_alert.domain.value_objects.stockout_risk import (
    RISK_NONE,
    STOCKOUT_RISK_KEYS,
    STOCKOUT_RISK_LABELS,
    STOCKOUT_RISKS,
    row_stockout_risk,
)
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
    if column == "stockout_risk":
        risk = row_stockout_risk(row)
        # 対象外は空。旧行（キーなし）も一覧では空にし、絞り込み・並び替えでは監視として扱う
        return "" if risk == RISK_NONE or "stockout_risk" not in row else risk
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
    # 流動区分の判定根拠（07 REQ-FQR-F-005）。詳細ダイアログの流動区分セクションに出す。
    # 理由は判定期間で変わるため 3 期間ぶん渡し、期間切替ではクライアントが引き直す（07 design §1-6）
    client_row["flowReasons"] = [str(reason) for reason in (row.get("flow_reasons") or [])]
    reasons_by_period = row.get("flow_reasons_by_period") or {}
    client_row["flowReasonsByPeriod"] = {
        period.key: [str(reason) for reason in (reasons_by_period.get(period.key) or [])]
        for period in EVALUATION_PERIODS
    }
    client_row["recommendedAction"] = str(row.get("recommended_action") or "")
    client_row["responsibleDepartment"] = str(row.get("responsible_department") or "")
    # 第 2 段階（05 design §6.2）: 需要予測。旧スナップショット（キーなし）は basis「なし」で値は空
    client_row["internalItemCd"] = str(row.get("internal_item_cd") or "")
    client_row["unconfirmedOrderTrend"] = list(row.get("unconfirmed_order_trend") or [])
    client_row["reconciliationUnitKey"] = str(row.get("reconciliation_unit_key") or "")
    client_row["demandForecast"] = _demand_forecast_payload(row)
    # 06: 在庫切れリスク（S-204）。旧行は監視
    risk = row_stockout_risk(row)
    client_row["stockoutRisk"] = risk
    client_row["stockoutRiskKey"] = STOCKOUT_RISK_KEYS[risk]
    client_row["stockoutRiskReasons"] = [str(reason) for reason in (row.get("stockout_risk_reasons") or [])]
    client_row["daysUntilStockout"] = _optional_int(row.get("days_until_stockout"))
    client_row["shortageQty"] = _optional_int(row.get("shortage_qty"))
    client_row["replenishment"] = {
        "qty": _optional_int(row.get("replenishment_qty")) or 0,
        "laterQty": _optional_int(row.get("replenishment_later_qty")) or 0,
        "staleQty": _optional_int(row.get("replenishment_stale_qty")) or 0,
        "earliestDue": str(row.get("replenishment_earliest_due") or ""),
        "hasOverdue": bool(row.get("replenishment_has_overdue")),
        "unknown": bool(row.get("replenishment_unknown")),
    }
    client_row["upstreamOrder"] = {
        "qty": _optional_int(row.get("upstream_order_qty")) or 0,
        "overdue": bool(row.get("upstream_order_overdue")),
        "earliestDue": str(row.get("upstream_order_earliest_due") or ""),
    }
    # 工程の連鎖（直下 → 上流）と各工程の発注残（詳細ダイアログ用。06 design §4.1a）
    orders = [o for o in (row.get("open_purchase_orders") or []) if isinstance(o, dict)]
    client_row["processChain"] = [
        {
            "level": _optional_int(stage.get("level")) or 0,
            "itemCd": str(stage.get("item_cd") or ""),
            "vendCd": str(stage.get("vend_cd") or ""),
            "vendName": str(stage.get("vend_name") or ""),
            "leadTimeDays": _optional_int(stage.get("lead_time_days")) or 0,
            "leadTimeSource": str(stage.get("lead_time_source") or ""),
            "openOrders": [
                {"dueDate": str(o.get("due_date") or ""), "remainingQty": _optional_int(o.get("remaining_qty")) or 0}
                for o in orders
                if str(o.get("item_cd") or "") == str(stage.get("item_cd") or "") and str(o.get("vend_cd") or "") == str(stage.get("vend_cd") or "")
            ],
        }
        for stage in (row.get("process_chain") or [])
        if isinstance(stage, dict)
    ]
    client_row["leadTimeDays"] = _optional_int(row.get("lead_time_days"))
    client_row["leadTimeSource"] = str(row.get("lead_time_source") or "")
    ordering_method = str(row.get("ordering_method") or ORDERING_UNKNOWN)
    client_row["orderingMethod"] = ordering_method
    client_row["orderingMethodKey"] = ORDERING_METHOD_KEYS.get(ordering_method, "unknown")
    # MARI 在庫は行の生値（mari_stock_qty）がソートに、display が表示に使われる。
    # camelCase の別名は増やさない（同じ値を二重に配信することになるため。design.md §6.4）。
    client_row["display"] = {
        column: _display_cell(row, column, quadrant)
        for column, _label in SORTABLE_COLUMNS
        if column != "confirmation_status"
    }
    return client_row


def _optional_int(value: object) -> int | None:
    number = _optional_number(value)
    return None if number is None else int(number)


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
        "stockoutRiskOrder": [STOCKOUT_RISK_KEYS[risk] for risk in STOCKOUT_RISKS],
        "stockoutRiskLabels": dict(STOCKOUT_RISK_LABELS),
    }
