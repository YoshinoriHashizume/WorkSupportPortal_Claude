from __future__ import annotations

from collections.abc import Callable

from apps.inventory_order_alert.domain.list_filter import (
    ListFilterParams,
    apply_list_filters,
    list_filter_params_from_client_payload,
)
from apps.inventory_order_alert.domain.confirmation import ConfirmationInput, parse_confirmation_payload
from apps.inventory_order_alert.domain.ports import LoadSummary
from apps.inventory_order_alert.domain.alert_level import ALERT_NONE, lookup_alert_level_for_row
from apps.inventory_order_alert.domain.confirmation import confirmation_label
from apps.inventory_order_alert.domain.row_counts import RowCounts, count_rows
from apps.inventory_order_alert.domain.row_display import row_alert_class

SaveConfirmation = Callable[..., None]


def _counts_to_response(counts: RowCounts) -> dict[str, int]:
    return {
        "critical": counts.critical,
        "warningShip": counts.warning_ship,
        "warningIncoming": counts.warning_incoming,
        "alertNone": counts.alert_none,
        "unconfirmed": counts.unconfirmed,
        "inProgress": counts.in_progress,
        "confirmed": counts.confirmed,
    }


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
            "alert_level": ALERT_NONE,
            "confirmation_status": confirmation_label(input_data.status),
        }

    return {
        "ok": True,
        "confirmationStatusKey": input_data.status,
        "alertRowClass": row_alert_class(target_row),
        "counts": _counts_to_response(counts),
    }


class SaveConfirmationUsecase:
    def __init__(self, load_summary: LoadSummary, save_confirmation: SaveConfirmation) -> None:
        self._load_summary = load_summary
        self._save_confirmation = save_confirmation

    def execute(self, payload: dict[str, object], *, confirmed_by: str) -> dict[str, object]:
        input_data = parse_confirmation_payload(payload)
        summary = self._load_summary()
        alert_level = lookup_alert_level_for_row(
            summary.rows if summary else [],
            cust_code=input_data.cust_code,
            item_cd=input_data.item_cd,
        )
        self._save_confirmation(
            input_data,
            confirmed_by=confirmed_by,
            alert_level=alert_level,
        )
        filter_params = list_filter_params_from_client_payload(payload)
        summary = self._load_summary()
        return _build_save_result(
            input_data,
            filter_params=filter_params,
            rows=summary.rows if summary else [],
        )
