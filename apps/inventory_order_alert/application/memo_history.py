from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.inventory_order_alert.application.user_display import resolve_user_display_names, user_display_name_from_model
from apps.inventory_order_alert.models import (
    ConfirmationStatus,
    InventoryOrderAlertConfirmation,
    InventoryOrderAlertConfirmationMemoEntry,
)

MAX_MEMO_LENGTH = 500


@dataclass(frozen=True)
class MemoEntryInput:
    cust_code: str
    item_cd: str
    content: str


def parse_memo_entry_payload(data: object) -> MemoEntryInput:
    if not isinstance(data, dict):
        raise ValueError("JSON の形式が不正です。")

    cust_code = str(data.get("custCode") or "").strip()
    item_cd = str(data.get("itemCd") or "").strip()
    content = str(data.get("content") or "").strip()

    if not cust_code:
        raise ValueError("custCode は必須です。")
    if not item_cd:
        raise ValueError("itemCd は必須です。")
    if not content:
        raise ValueError("メモ内容を入力してください。")
    if len(content) > MAX_MEMO_LENGTH:
        raise ValueError(f"メモは {MAX_MEMO_LENGTH} 文字以内で入力してください。")

    return MemoEntryInput(cust_code=cust_code, item_cd=item_cd, content=content)


def format_memo_created_at(value) -> str:
    if value is None:
        return ""
    return timezone.localtime(value).strftime("%Y/%m/%d %H:%M")


def memo_entry_to_dict(
    entry: InventoryOrderAlertConfirmationMemoEntry,
    *,
    author_names: dict[str, str] | None = None,
) -> dict[str, str]:
    username = entry.created_by or ""
    return {
        "createdAt": format_memo_created_at(entry.created_at),
        "createdBy": (author_names or {}).get(username, username) or "-",
        "content": entry.content,
    }


def list_confirmation_memos(*, cust_code: str, item_cd: str) -> list[dict[str, str]]:
    confirmation = InventoryOrderAlertConfirmation.objects.filter(
        cust_code=cust_code,
        item_cd=item_cd,
    ).first()
    if confirmation is None:
        return []
    entries = list(confirmation.memo_entries.order_by("-created_at", "-id"))
    author_names = resolve_user_display_names({entry.created_by for entry in entries})
    return [memo_entry_to_dict(entry, author_names=author_names) for entry in entries]


def format_memo_history_csv(
    entries: list[InventoryOrderAlertConfirmationMemoEntry],
    *,
    author_names: dict[str, str] | None = None,
) -> str:
    names = author_names or resolve_user_display_names({entry.created_by for entry in entries})
    parts: list[str] = []
    for entry in entries:
        created_at = format_memo_created_at(entry.created_at)
        author = names.get(entry.created_by, entry.created_by) or "-"
        parts.append(f"{created_at} {author}: {entry.content}")
    return " | ".join(parts)


def sync_confirmation_latest_memo(confirmation: InventoryOrderAlertConfirmation) -> None:
    latest = confirmation.memo_entries.order_by("-created_at", "-id").first()
    confirmation.memo = latest.content if latest else ""
    confirmation.save(update_fields=["memo", "updated_at"])


def add_confirmation_memo(
    input_data: MemoEntryInput,
    *,
    created_by: str,
) -> InventoryOrderAlertConfirmationMemoEntry:
    confirmation, _created = InventoryOrderAlertConfirmation.objects.get_or_create(
        cust_code=input_data.cust_code,
        item_cd=input_data.item_cd,
        defaults={"status": ConfirmationStatus.UNCONFIRMED},
    )
    entry = InventoryOrderAlertConfirmationMemoEntry.objects.create(
        confirmation=confirmation,
        content=input_data.content,
        created_by=created_by,
    )
    sync_confirmation_latest_memo(confirmation)
    return entry
