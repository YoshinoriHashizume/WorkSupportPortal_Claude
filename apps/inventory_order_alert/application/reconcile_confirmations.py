from __future__ import annotations

from django.utils import timezone

from apps.inventory_order_alert.domain.alert_level import ALERT_NONE, is_alert_escalated, normalize_alert_level
from apps.inventory_order_alert.models import ConfirmationStatus, InventoryOrderAlertConfirmation

ACTIVE_CONFIRMATION_STATUSES = frozenset(
    {
        ConfirmationStatus.IN_PROGRESS,
        ConfirmationStatus.CONFIRMED,
    }
)


def lookup_alert_level_for_row(
    rows: list[dict[str, object]],
    *,
    cust_code: str,
    item_cd: str,
) -> str:
    for row in rows:
        if str(row.get("cust_code") or "") == cust_code and str(row.get("item_cd") or "") == item_cd:
            return normalize_alert_level(str(row.get("alert_level") or ""))
    return ALERT_NONE


def reconcile_confirmations_after_import(rows: list[dict[str, object]]) -> int:
    """再取込後、確認時よりアラートが深刻化した行を未確認に戻す。"""
    row_by_key = {
        (str(row.get("cust_code") or ""), str(row.get("item_cd") or "")): row for row in rows
    }
    reset_count = 0
    confirmations = InventoryOrderAlertConfirmation.objects.filter(
        status__in=ACTIVE_CONFIRMATION_STATUSES,
    )
    for confirmation in confirmations:
        if not confirmation.confirmed_alert_level:
            continue
        row = row_by_key.get((confirmation.cust_code, confirmation.item_cd))
        if row is None:
            continue
        current_level = normalize_alert_level(str(row.get("alert_level") or ""))
        if not is_alert_escalated(confirmation.confirmed_alert_level, current_level):
            continue
        confirmation.status = ConfirmationStatus.UNCONFIRMED
        confirmation.confirmed_alert_level = ""
        confirmation.confirmed_at = None
        confirmation.confirmed_by = ""
        confirmation.save(
            update_fields=[
                "status",
                "confirmed_alert_level",
                "confirmed_at",
                "confirmed_by",
                "updated_at",
            ]
        )
        reset_count += 1
    return reset_count


def reset_all_confirmations() -> int:
    """確認中・確認済みをすべて未確認に戻す（メモは維持）。"""
    return InventoryOrderAlertConfirmation.objects.filter(
        status__in=ACTIVE_CONFIRMATION_STATUSES,
    ).update(
        status=ConfirmationStatus.UNCONFIRMED,
        confirmed_alert_level="",
        confirmed_at=None,
        confirmed_by="",
        updated_at=timezone.now(),
    )
