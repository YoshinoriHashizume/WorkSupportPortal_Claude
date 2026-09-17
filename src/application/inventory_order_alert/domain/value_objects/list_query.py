from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings
from application.inventory_order_alert.domain.value_objects.dates import parse_optional_ymd
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    DEFAULT_EVALUATION_PERIOD,
    EVALUATION_PERIODS,
    FLOW_QUADRANT_KEYS,
    FLOW_QUADRANT_LABELS,
    LEGACY_QUADRANT_ALIASES,
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
    """判定期間だけを解釈する（05_single-flow-view design.md §6.1）。axis は無視する。"""
    raw_period = params.get("period", "").strip()
    if raw_period.isdigit():
        found = EVALUATION_PERIODS.find_by_years(int(raw_period))
        if found is not None:
            return FlowSelection(found)
    found = EVALUATION_PERIODS.find(raw_period)
    if found is not None:
        return FlowSelection(found)
    return FlowSelection(DEFAULT_EVALUATION_PERIOD)


def parse_flow_quadrant(params: dict[str, str]) -> str:
    """流動区分の絞り込みキーを解釈する（05 design §6.1、REQ-SFV-F-010）。

    新キーはそのまま、区分ラベル・旧キー・旧称（`LEGACY_QUADRANT_ALIASES`）は新キーへ写像する。
    未知の値は絞り込みなし（空）にする。
    """
    value = params.get("flow_quadrant", "").strip()
    if value in FLOW_QUADRANT_LABELS:
        return value
    if value in FLOW_QUADRANT_KEYS:
        return FLOW_QUADRANT_KEYS[value]
    if value in LEGACY_QUADRANT_ALIASES:
        return FLOW_QUADRANT_KEYS[LEGACY_QUADRANT_ALIASES[value]]
    return ""


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

    判定期間は利用者が画面・URL で選ぶ値であり、管理者設定の対象外である。
    設定値（`warning_days` / `stock_stale_days`）は一覧の別の用途で使用する。
    """
    _ = settings
    return query
