from __future__ import annotations

from django.utils import timezone

from application.inventory_order_alert.domain.value_objects.alert_level import ALERT_NONE, is_alert_escalated, normalize_alert_level
from application.inventory_order_alert.domain.value_objects.confirmation import (
    ACTIVE_STATUSES,
    ConfirmationInput,
    ConfirmationRecord,
    MemoEntryRecord,
    STATUS_UNCONFIRMED,
    format_memo_history_csv,
    memo_entry_to_dict,
)
from application.inventory_order_alert.infrastructure.persistence.user_display_repository import resolve_user_display_names
from application.inventory_order_alert.models import (
    ConfirmationStatus,
    InventoryOrderAlertConfirmation,
    InventoryOrderAlertConfirmationMemoEntry,
)


def _memo_entry_from_model(entry: InventoryOrderAlertConfirmationMemoEntry) -> MemoEntryRecord:
    return MemoEntryRecord(
        created_at=entry.created_at,
        created_by=entry.created_by or "",
        content=entry.content,
    )


def _confirmation_from_model(confirmation: InventoryOrderAlertConfirmation) -> ConfirmationRecord:
    entries = tuple(_memo_entry_from_model(entry) for entry in confirmation.memo_entries.all())
    author_names = resolve_user_display_names({entry.created_by for entry in entries})
    return ConfirmationRecord(
        cust_code=confirmation.cust_code,
        item_cd=confirmation.item_cd,
        status=confirmation.status,
        memo=confirmation.memo,
        confirmed_alert_level=confirmation.confirmed_alert_level,
        confirmed_at=confirmation.confirmed_at,
        confirmed_by=confirmation.confirmed_by,
        memo_history=format_memo_history_csv(list(entries), author_names=author_names),
        memo_entries=entries,
    )


def load_confirmation_map() -> dict[tuple[str, str], ConfirmationRecord]:
    return {
        (row.cust_code, row.item_cd): _confirmation_from_model(row)
        for row in InventoryOrderAlertConfirmation.objects.prefetch_related("memo_entries").all()
    }


def has_resettable_confirmations() -> bool:
    return InventoryOrderAlertConfirmation.objects.filter(
        status__in=ACTIVE_STATUSES,
    ).exists()


def save_confirmation(
    input_data: ConfirmationInput,
    *,
    confirmed_by: str,
    alert_level: str = "",
) -> ConfirmationRecord:
    confirmed_at = None
    confirmed_by_value = ""
    confirmed_alert_level = ""
    if input_data.status in {ConfirmationStatus.IN_PROGRESS, ConfirmationStatus.CONFIRMED}:
        confirmed_at = timezone.now()
        confirmed_by_value = confirmed_by
        confirmed_alert_level = normalize_alert_level(alert_level or ALERT_NONE)

    confirmation, _created = InventoryOrderAlertConfirmation.objects.update_or_create(
        cust_code=input_data.cust_code,
        item_cd=input_data.item_cd,
        defaults={
            "status": input_data.status,
            "confirmed_at": confirmed_at,
            "confirmed_by": confirmed_by_value,
            "confirmed_alert_level": confirmed_alert_level,
        },
    )
    return _confirmation_from_model(confirmation)


def list_confirmation_memos(*, cust_code: str, item_cd: str) -> list[dict[str, str]]:
    confirmation = InventoryOrderAlertConfirmation.objects.filter(
        cust_code=cust_code,
        item_cd=item_cd,
    ).first()
    if confirmation is None:
        return []
    entries = list(confirmation.memo_entries.order_by("-created_at", "-id"))
    author_names = resolve_user_display_names({entry.created_by for entry in entries})
    return [memo_entry_to_dict(_memo_entry_from_model(entry), author_names=author_names) for entry in entries]


def _sync_confirmation_latest_memo(confirmation: InventoryOrderAlertConfirmation) -> None:
    latest = confirmation.memo_entries.order_by("-created_at", "-id").first()
    confirmation.memo = latest.content if latest else ""
    confirmation.save(update_fields=["memo", "updated_at"])


def add_confirmation_memo(
    *,
    cust_code: str,
    item_cd: str,
    content: str,
    created_by: str,
) -> MemoEntryRecord:
    confirmation, _created = InventoryOrderAlertConfirmation.objects.get_or_create(
        cust_code=cust_code,
        item_cd=item_cd,
        defaults={"status": ConfirmationStatus.UNCONFIRMED},
    )
    entry = InventoryOrderAlertConfirmationMemoEntry.objects.create(
        confirmation=confirmation,
        content=content,
        created_by=created_by,
    )
    _sync_confirmation_latest_memo(confirmation)
    return _memo_entry_from_model(entry)


def reconcile_confirmations_after_import(rows: list[dict[str, object]]) -> int:
    row_by_key = {
        (str(row.get("cust_code") or ""), str(row.get("item_cd") or "")): row for row in rows
    }
    reset_count = 0
    confirmations = InventoryOrderAlertConfirmation.objects.filter(
        status__in=ACTIVE_STATUSES,
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
        confirmation.status = STATUS_UNCONFIRMED
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
    return InventoryOrderAlertConfirmation.objects.filter(
        status__in=ACTIVE_STATUSES,
    ).update(
        status=STATUS_UNCONFIRMED,
        confirmed_alert_level="",
        confirmed_at=None,
        confirmed_by="",
        updated_at=timezone.now(),
    )


__all__ = [
    "add_confirmation_memo",
    "has_resettable_confirmations",
    "list_confirmation_memos",
    "load_confirmation_map",
    "reconcile_confirmations_after_import",
    "reset_all_confirmations",
    "save_confirmation",
]
