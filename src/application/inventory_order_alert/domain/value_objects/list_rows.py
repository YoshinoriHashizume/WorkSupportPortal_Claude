from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.confirmation import ConfirmationRecord, attach_confirmation_fields
from application.inventory_order_alert.domain.value_objects.dates import parse_optional_ymd
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    FLOW_QUADRANT_KEYS,
    FLOW_QUADRANT_LABELS,
    QUADRANT_NORMAL_FLOW,
    RESPONSIBLE_DEPARTMENT_SEPARATOR,
    flow_quadrant_sort_rank,
    is_no_incoming_record,
    resolve_flow_quadrant,
    resolve_flow_quadrant_matrix,
)
from application.inventory_order_alert.domain.value_objects.list_query import ListQuery
from application.inventory_order_alert.domain.value_objects.recommended_action import (
    DEFAULT_RECOMMENDED_ACTIONS,
    RecommendedActions,
    render_status,
)
from application.inventory_order_alert.domain.value_objects.slims_stock import SlimsStockLocationLine
from application.inventory_order_alert.domain.value_objects.stock_join import attach_stock_fields


def _row_date(row: dict[str, object], key: str, *, as_of_date: date) -> date | None:
    """行の日付文字列を date に直す。空・解析不能はいずれも None（＝期間外）とする（design.md §8）。"""
    raw = str(row.get(key) or "")
    if not raw:
        return None
    try:
        return parse_optional_ymd(raw, today=as_of_date)
    except ValueError:
        return None


def apply_flow_quadrants_to_rows(
    rows: list[dict[str, object]],
    *,
    as_of_date: date,
    query: ListQuery,
    recommended_actions: RecommendedActions = DEFAULT_RECOMMENDED_ACTIONS,
) -> list[dict[str, object]]:
    """行に流動区分（S-203）・状況・推奨アクション（T-207）・責任部署（R-201）を付与する。

    判定期間 3 値ぶんの結果（`flow_quadrants`、キー Y1/Y3/Y5）も併せて持たせ、判定期間の切り替えを
    クライアント側で再判定なしに行えるようにする（05 design §3.1）。
    状況（`flow_status`）は選択中の判定期間で描画した文字列。通常流動品は状況・推奨アクションとも空。
    """
    selection = query.flow_selection
    enriched: list[dict[str, object]] = []
    for row in rows:
        copied = dict(row)
        last_incoming = _row_date(copied, "last_incoming_date", as_of_date=as_of_date)
        last_ship = _row_date(copied, "last_ship_date", as_of_date=as_of_date)
        quadrant = resolve_flow_quadrant(
            last_incoming,
            last_ship,
            as_of_date=as_of_date,
            selection=selection,
        )
        no_incoming_record = is_no_incoming_record(last_incoming)
        recommended = recommended_actions.for_quadrant(quadrant)
        copied["flow_quadrant"] = quadrant
        copied["flow_quadrant_key"] = FLOW_QUADRANT_KEYS[quadrant]
        copied["flow_quadrants"] = resolve_flow_quadrant_matrix(
            last_incoming,
            last_ship,
            as_of_date=as_of_date,
        )
        copied["no_incoming_record"] = no_incoming_record
        copied["flow_status"] = render_status(
            recommended,
            period=selection.period,
            last_incoming=str(copied.get("last_incoming_date") or ""),
            last_ship=str(copied.get("last_ship_date") or ""),
            no_incoming_record=no_incoming_record,
        )
        copied["recommended_action"] = recommended.action
        copied["responsible_department"] = RESPONSIBLE_DEPARTMENT_SEPARATOR.join(recommended.departments)
        enriched.append(copied)
    return enriched


def enrich_summary_rows(
    rows: list[dict[str, object]],
    *,
    as_of_date: date,
    query: ListQuery,
    stock_lines: list[SlimsStockLocationLine] | None = None,
    stock_as_of_date: date | None = None,
    confirmations: dict[tuple[str, str], ConfirmationRecord] | None = None,
    recommended_actions: RecommendedActions = DEFAULT_RECOMMENDED_ACTIONS,
) -> list[dict[str, object]]:
    rows_with_stock = attach_stock_fields(rows, stock_lines, stock_as_of_date=stock_as_of_date)
    enriched = apply_flow_quadrants_to_rows(
        rows_with_stock,
        as_of_date=as_of_date,
        query=query,
        recommended_actions=recommended_actions,
    )
    confirmation_map = confirmations if confirmations is not None else {}
    return attach_confirmation_fields(enriched, confirmation_map)


def filter_summary_rows(rows: list[dict[str, object]], query: ListQuery) -> list[dict[str, object]]:
    #: 未知のキーは絞り込みなしに倒す（design.md §8）。
    selected_quadrant = FLOW_QUADRANT_LABELS.get(query.flow_quadrant, "")
    filtered: list[dict[str, object]] = []
    for row in rows:
        if query.cust_code and str(row.get("cust_code") or "") != query.cust_code:
            continue
        if query.vend_code and str(row.get("level1_vend_cd") or "") != query.vend_code:
            continue
        quadrant = str(row.get("flow_quadrant") or "")
        if selected_quadrant and quadrant != selected_quadrant:
            continue
        if query.attention_only and quadrant == QUADRANT_NORMAL_FLOW:
            continue
        if query.hide_confirmed and str(row.get("confirmation_status") or "") == "確認済み":
            continue
        filtered.append(row)
    return filtered


def sort_summary_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    def sort_key(row: dict[str, object]) -> tuple[int, int]:
        quadrant = str(row.get("flow_quadrant") or QUADRANT_NORMAL_FLOW)
        qty = int(row.get("post_shipment_total_qty") or 0)
        return (flow_quadrant_sort_rank(quadrant), -qty)

    return sorted(rows, key=sort_key)
