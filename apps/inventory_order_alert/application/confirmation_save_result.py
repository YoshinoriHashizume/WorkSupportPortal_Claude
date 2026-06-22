from __future__ import annotations

from apps.inventory_order_alert.application.confirmation import confirmation_label
from apps.inventory_order_alert.application.dashboard_summary import RowCounts, count_rows
from apps.inventory_order_alert.application.list_filter import ListFilterParams, apply_list_filters
from apps.inventory_order_alert.application.save_confirmation import ConfirmationInput
from apps.inventory_order_alert.application.summary_storage import load_latest_summary
from apps.inventory_order_alert.domain.alert_level import ALERT_NONE
from apps.inventory_order_alert.domain.row_display import row_alert_class


def counts_to_response(counts: RowCounts) -> dict[str, int]:
    return {
        "critical": counts.critical,
        "warningShip": counts.warning_ship,
        "warningIncoming": counts.warning_incoming,
        "alertNone": counts.alert_none,
        "unconfirmed": counts.unconfirmed,
        "inProgress": counts.in_progress,
        "confirmed": counts.confirmed,
    }


def build_confirmation_save_result(
    input_data: ConfirmationInput,
    *,
    filter_params: ListFilterParams,
) -> dict[str, object]:
    summary = load_latest_summary()
    rows = summary.rows if summary else []
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
            "alert_level": ALERT_NONE,
            "confirmation_status": confirmation_label(input_data.status),
        }

    return {
        "ok": True,
        "confirmationStatusKey": input_data.status,
        "alertRowClass": row_alert_class(target_row),
        "counts": counts_to_response(counts),
    }
