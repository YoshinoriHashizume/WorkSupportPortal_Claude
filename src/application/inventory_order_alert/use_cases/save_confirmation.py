from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.list_filter import (
    ListFilterParams,
    apply_list_filters,
    list_filter_params_from_client_payload,
)
from application.inventory_order_alert.domain.value_objects.confirmation import ConfirmationInput, parse_confirmation_payload
from application.inventory_order_alert.domain.repositories.ports import LoadSummary, SaveConfirmation
from application.inventory_order_alert.domain.value_objects.confirmation import confirmation_label
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    QUADRANT_NORMAL_FLOW,
    REFERENCE_FLOW_SELECTION,
    normalize_flow_quadrant,
)
from application.inventory_order_alert.domain.value_objects.list_query import ListQuery
from application.inventory_order_alert.domain.value_objects.list_rows import apply_flow_quadrants_to_rows
from application.inventory_order_alert.domain.value_objects.row_counts import RowCounts, count_rows
from application.inventory_order_alert.domain.value_objects.row_display import row_alert_class


def _counts_to_response(counts: RowCounts) -> dict[str, int]:
    return {
        "supplyRisk": counts.supply_risk,
        "dormantStock": counts.dormant_stock,
        "excessStockRisk": counts.excess_stock_risk,
        "normalFlow": counts.normal_flow,
        "attention": counts.attention,
        "unconfirmed": counts.unconfirmed,
        "inProgress": counts.in_progress,
        "confirmed": counts.confirmed,
    }


def lookup_flow_quadrant_for_row(
    rows: list[dict[str, object]],
    *,
    cust_code: str,
    item_cd: str,
) -> str:
    """確認記録に残す流動区分を引く。見つからない行は安全側の通常流動品に倒す（design.md §5.2）。"""
    for row in rows:
        if str(row.get("cust_code") or "") == cust_code and str(row.get("item_cd") or "") == item_cd:
            return normalize_flow_quadrant(str(row.get("flow_quadrant") or ""))
    return QUADRANT_NORMAL_FLOW


def _build_save_result(
    input_data: ConfirmationInput,
    *,
    filter_params: ListFilterParams,
    rows: list[dict[str, object]],
) -> dict[str, object]:
    filtered_rows = apply_list_filters(rows, filter_params)
    counts = count_rows(filtered_rows)

    target_row = next(
        (
            row
            for row in rows
            if str(row.get("cust_code") or "") == input_data.cust_code
            and str(row.get("item_cd") or "") == input_data.item_cd
        ),
        None,
    )
    if target_row is None:
        target_row = {
            "flow_quadrant": QUADRANT_NORMAL_FLOW,
            "confirmation_status": confirmation_label(input_data.status),
        }

    return {
        "ok": True,
        "confirmationStatusKey": input_data.status,
        "alertRowClass": row_alert_class(target_row),
        "counts": _counts_to_response(counts),
    }


class SaveConfirmationUseCase:
    def __init__(self, load_summary: LoadSummary, save_confirmation: SaveConfirmation) -> None:
        self._load_summary = load_summary
        self._save_confirmation = save_confirmation

    def execute(self, payload: dict[str, object], *, confirmed_by: str) -> dict[str, object]:
        input_data = parse_confirmation_payload(payload)
        summary = self._load_summary()
        # 保存する流動区分は基準判定条件で固定する。利用者の画面選択には依存しない（design.md §5.2）。
        self._save_confirmation(
            input_data,
            confirmed_by=confirmed_by,
            flow_quadrant=lookup_flow_quadrant_for_row(
                self._rows_with_reference_quadrant(summary),
                cust_code=input_data.cust_code,
                item_cd=input_data.item_cd,
            ),
        )
        filter_params = list_filter_params_from_client_payload(payload)
        summary = self._load_summary()
        return _build_save_result(
            input_data,
            filter_params=filter_params,
            rows=self._rows_with_reference_quadrant(summary),
        )

    @staticmethod
    def _rows_with_reference_quadrant(summary: object | None) -> list[dict[str, object]]:
        rows = list(getattr(summary, "rows", None) or [])
        as_of_date = getattr(summary, "as_of_date", None)
        if not rows or as_of_date is None:
            return rows
        return apply_flow_quadrants_to_rows(
            rows,
            as_of_date=as_of_date,
            query=ListQuery(as_of_date=as_of_date, flow_selection=REFERENCE_FLOW_SELECTION),
        )
