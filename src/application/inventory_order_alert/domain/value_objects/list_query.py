from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings
from application.inventory_order_alert.domain.value_objects.dates import parse_optional_ymd
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    DEFAULT_FLOW_AXIS,
    EVALUATION_PERIODS,
    FLOW_QUADRANT_LABELS,
    REFERENCE_FLOW_SELECTION,
    FlowSelection,
)


@dataclass(frozen=True)
class ListQuery:
    as_of_date: date
    cust_code: str = ""
    vend_code: str = ""
    hide_confirmed: bool = False
    flow_selection: FlowSelection = REFERENCE_FLOW_SELECTION
    flow_quadrant: str = ""
    attention_only: bool = False


def parse_flow_selection(params: dict[str, str]) -> FlowSelection:
    """判定軸・判定期間を解釈する（§6.1）。不正値は静かに既定値へ倒す。"""
    axis = params.get("axis", "").strip()
    if not EVALUATION_PERIODS.for_axis(axis):
        # 判定軸が未指定・不正なら判定期間も当該軸の既定値へリセットする（design.md §6.1）。
        return FlowSelection(EVALUATION_PERIODS.default_for_axis(DEFAULT_FLOW_AXIS))
    raw_period = params.get("period", "").strip()
    for period in EVALUATION_PERIODS.for_axis(axis):
        if raw_period == str(period.value):
            return FlowSelection(period)
    return FlowSelection(EVALUATION_PERIODS.default_for_axis(axis))


def parse_flow_quadrant(params: dict[str, str]) -> str:
    """流動区分の絞り込みキーを解釈する。未知のキーは絞り込みなし（空）にする。"""
    value = params.get("flow_quadrant", "").strip()
    return value if value in FLOW_QUADRANT_LABELS else ""


def parse_list_query(params: dict[str, str], *, today: date | None = None) -> ListQuery:
    return ListQuery(
        as_of_date=parse_optional_ymd(params.get("asOfDate", ""), today=today),
        cust_code=params.get("custCode", "").strip(),
        vend_code=params.get("vendCode", "").strip(),
        hide_confirmed=params.get("hideConfirmed", "false").lower() in {"true", "1", "on"},
        flow_selection=parse_flow_selection(params),
        flow_quadrant=parse_flow_quadrant(params),
        attention_only=params.get("attentionOnly", "false").lower() in {"true", "1", "on"},
    )


def merge_query_with_settings(query: ListQuery, settings: AppSettings) -> ListQuery:
    """判定条件は設定値で上書きしない（§6.1 / REQ-LFV-F-015）。

    判定軸・判定期間は利用者が画面・URL で選ぶ値であり、管理者設定の対象外である。
    設定値（`warning_days` / `stock_stale_days`）は一覧の別の用途で使用する。
    """
    _ = settings
    return query
