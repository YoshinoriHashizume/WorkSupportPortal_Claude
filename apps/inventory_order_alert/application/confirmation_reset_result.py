from __future__ import annotations

from apps.inventory_order_alert.application.confirmation_save_result import counts_to_response
from apps.inventory_order_alert.application.dashboard_summary import count_rows
from apps.inventory_order_alert.application.list_filter import ListFilterParams, apply_list_filters
from apps.inventory_order_alert.application.reconcile_confirmations import reset_all_confirmations
from apps.inventory_order_alert.application.summary_storage import load_latest_summary


def build_confirmation_reset_result(
    *,
    filter_params: ListFilterParams,
) -> dict[str, object]:
    reset_count = reset_all_confirmations()
    summary = load_latest_summary()
    rows = summary.rows if summary else []
    filtered_rows = apply_list_filters(rows, filter_params)
    counts = count_rows(filtered_rows)
    return {
        "ok": True,
        "resetCount": reset_count,
        "counts": counts_to_response(counts),
    }
