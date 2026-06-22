from __future__ import annotations

from apps.inventory_order_alert.application.memo_history import format_memo_history_csv
from apps.inventory_order_alert.application.user_display import resolve_user_display_names
from apps.inventory_order_alert.models import ConfirmationStatus, InventoryOrderAlertConfirmation


def confirmation_label(status: str) -> str:
    return ConfirmationStatus(status).label if status in ConfirmationStatus.values else "未確認"


def confirmation_status_key(row: dict[str, object]) -> str:
    label = str(row.get("confirmation_status") or "未確認")
    for value, choice_label in ConfirmationStatus.choices:
        if choice_label == label:
            return value
    return ConfirmationStatus.UNCONFIRMED


def load_confirmation_map() -> dict[tuple[str, str], InventoryOrderAlertConfirmation]:
    return {
        (row.cust_code, row.item_cd): row
        for row in InventoryOrderAlertConfirmation.objects.prefetch_related("memo_entries").all()
    }


def attach_confirmation_fields(
    rows: list[dict[str, object]],
    confirmations: dict[tuple[str, str], InventoryOrderAlertConfirmation],
) -> list[dict[str, object]]:
    enriched: list[dict[str, object]] = []
    for row in rows:
        copied = dict(row)
        key = (str(copied.get("cust_code") or ""), str(copied.get("item_cd") or ""))
        confirmation = confirmations.get(key)
        if confirmation:
            copied["confirmation_status"] = confirmation_label(confirmation.status)
            copied["confirmed_at"] = (
                confirmation.confirmed_at.strftime("%Y/%m/%d %H:%M") if confirmation.confirmed_at else ""
            )
            copied["confirmed_by"] = confirmation.confirmed_by
            copied["confirmation_memo"] = confirmation.memo
            copied["confirmation_memo_history"] = format_memo_history_csv(
                list(confirmation.memo_entries.all()),
                author_names=resolve_user_display_names(
                    {entry.created_by for entry in confirmation.memo_entries.all()}
                ),
            )
        else:
            copied.setdefault("confirmation_status", "未確認")
            copied.setdefault("confirmed_at", "")
            copied.setdefault("confirmed_by", "")
            copied.setdefault("confirmation_memo", "")
            copied.setdefault("confirmation_memo_history", "")
        enriched.append(copied)
    return enriched
