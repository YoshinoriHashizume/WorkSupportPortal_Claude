from __future__ import annotations

from collections.abc import Callable

from application.inventory_order_alert.domain.value_objects.list_filter import (
    apply_list_filters,
    list_filter_params_from_client_payload,
)
from application.inventory_order_alert.domain.repositories.ports import LoadSummary
from application.inventory_order_alert.domain.value_objects.row_counts import RowCounts, count_rows

ResetAllConfirmations = Callable[[], int]


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


class ResetConfirmations:
    def __init__(
        self,
        load_summary: LoadSummary,
        reset_all_confirmations: ResetAllConfirmations,
    ) -> None:
        self._load_summary = load_summary
        self._reset_all_confirmations = reset_all_confirmations

    def execute(self, payload: dict[str, object]) -> dict[str, object]:
        filter_params = list_filter_params_from_client_payload(payload)
        reset_count = self._reset_all_confirmations()
        summary = self._load_summary()
        filtered_rows = apply_list_filters(summary.rows if summary else [], filter_params)
        counts = count_rows(filtered_rows)
        return {
            "ok": True,
            "resetCount": reset_count,
            "counts": _counts_to_response(counts),
        }
