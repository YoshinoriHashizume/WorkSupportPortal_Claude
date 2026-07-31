from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from application.inventory_order_alert.domain.value_objects.dates import format_display_datetime

STATUS_UNCONFIRMED = "unconfirmed"
STATUS_IN_PROGRESS = "in_progress"
STATUS_CONFIRMED = "confirmed"
MAX_MEMO_LENGTH = 500

VALID_STATUSES = frozenset(
    {
        STATUS_UNCONFIRMED,
        STATUS_IN_PROGRESS,
        STATUS_CONFIRMED,
    }
)

ACTIVE_STATUSES = frozenset(
    {
        STATUS_IN_PROGRESS,
        STATUS_CONFIRMED,
    }
)

STATUS_LABELS: dict[str, str] = {
    STATUS_UNCONFIRMED: "未確認",
    STATUS_IN_PROGRESS: "確認中",
    STATUS_CONFIRMED: "確認済み",
}

STATUS_CHOICES: list[tuple[str, str]] = [
    (STATUS_UNCONFIRMED, STATUS_LABELS[STATUS_UNCONFIRMED]),
    (STATUS_IN_PROGRESS, STATUS_LABELS[STATUS_IN_PROGRESS]),
    (STATUS_CONFIRMED, STATUS_LABELS[STATUS_CONFIRMED]),
]

CONFIRMATION_STATUS_SORT_RANK: dict[str, int] = {
    STATUS_UNCONFIRMED: 0,
    STATUS_IN_PROGRESS: 1,
    STATUS_CONFIRMED: 2,
}


def confirmation_label(status: str) -> str:
    return STATUS_LABELS.get(status, STATUS_LABELS[STATUS_UNCONFIRMED])


def confirmation_status_key(row: dict[str, object]) -> str:
    label = str(row.get("confirmation_status") or STATUS_LABELS[STATUS_UNCONFIRMED])
    for value, choice_label in STATUS_CHOICES:
        if choice_label == label:
            return value
    return STATUS_UNCONFIRMED


def confirmation_status_sort_rank(status_key: str) -> int:
    return CONFIRMATION_STATUS_SORT_RANK.get(status_key, 99)


def confirmation_status_sort_key(row: dict[str, object]) -> int:
    return confirmation_status_sort_rank(confirmation_status_key(row))


@dataclass(frozen=True)
class MemoEntryRecord:
    created_at: datetime | None
    created_by: str
    content: str


@dataclass(frozen=True)
class ConfirmationRecord:
    cust_code: str
    item_cd: str
    status: str
    memo: str
    confirmed_alert_level: str
    confirmed_at: datetime | None
    confirmed_by: str
    memo_history: str = ""
    memo_entries: tuple[MemoEntryRecord, ...] = ()


@dataclass(frozen=True)
class ConfirmationInput:
    cust_code: str
    item_cd: str
    status: str


@dataclass(frozen=True)
class MemoEntryInput:
    cust_code: str
    item_cd: str
    content: str


def parse_confirmation_payload(data: object) -> ConfirmationInput:
    if not isinstance(data, dict):
        raise ValueError("JSON の形式が不正です。")

    cust_code = str(data.get("custCode") or "").strip()
    item_cd = str(data.get("itemCd") or "").strip()
    status = str(data.get("status") or "").strip()

    if not cust_code:
        raise ValueError("custCode は必須です。")
    if not item_cd:
        raise ValueError("itemCd は必須です。")
    if status not in VALID_STATUSES:
        raise ValueError("status が不正です。")

    return ConfirmationInput(
        cust_code=cust_code,
        item_cd=item_cd,
        status=status,
    )


def parse_memo_payload(data: object) -> str:
    if not isinstance(data, dict):
        raise ValueError("JSON の形式が不正です。")
    memo = str(data.get("memo") or "").strip()
    if len(memo) > MAX_MEMO_LENGTH:
        raise ValueError(f"メモは {MAX_MEMO_LENGTH} 文字以内で入力してください。")
    return memo


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


def memo_entry_to_dict(
    entry: MemoEntryRecord,
    *,
    author_names: dict[str, str] | None = None,
) -> dict[str, str]:
    username = entry.created_by or ""
    return {
        "createdAt": format_display_datetime(entry.created_at),
        "createdBy": (author_names or {}).get(username, username) or "-",
        "content": entry.content,
    }


def format_memo_history_csv(
    entries: list[MemoEntryRecord],
    *,
    author_names: dict[str, str] | None = None,
) -> str:
    names = author_names or {}
    parts: list[str] = []
    for entry in entries:
        created_at = format_display_datetime(entry.created_at)
        author = names.get(entry.created_by, entry.created_by) or "-"
        parts.append(f"{created_at} {author}: {entry.content}")
    return " | ".join(parts)


def attach_confirmation_fields(
    rows: list[dict[str, object]],
    confirmations: dict[tuple[str, str], ConfirmationRecord],
) -> list[dict[str, object]]:
    enriched: list[dict[str, object]] = []
    for row in rows:
        copied = dict(row)
        key = (str(copied.get("cust_code") or ""), str(copied.get("item_cd") or ""))
        confirmation = confirmations.get(key)
        if confirmation:
            copied["confirmation_status"] = confirmation_label(confirmation.status)
            copied["confirmed_at"] = format_display_datetime(confirmation.confirmed_at)
            copied["confirmed_by"] = confirmation.confirmed_by
            copied["confirmation_memo"] = confirmation.memo
            copied["confirmation_memo_history"] = confirmation.memo_history
        else:
            copied.setdefault("confirmation_status", "未確認")
            copied.setdefault("confirmed_at", "")
            copied.setdefault("confirmed_by", "")
            copied.setdefault("confirmation_memo", "")
            copied.setdefault("confirmation_memo_history", "")
        enriched.append(copied)
    return enriched
