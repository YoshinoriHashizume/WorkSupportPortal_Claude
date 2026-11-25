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
    #: 照合単位行に追加したときの複製を束ねる識別子（spec/13 design §4.1）。空は移行前のメモ
    entry_group: str = ""
    entry_id: int = 0


@dataclass(frozen=True)
class ConfirmationRecord:
    cust_code: str
    item_cd: str
    status: str
    memo: str
    #: 確認時点の流動区分（design.md §5.2）。既存データには旧アラートレベルのラベルが入りうる。
    confirmed_flow_quadrant: str
    confirmed_at: datetime | None
    confirmed_by: str
    memo_history: str = ""
    memo_entries: tuple[MemoEntryRecord, ...] = ()
    #: 照合単位行で最も新しい記録を選ぶために使う（spec/13 REQ-RUR-F-012）
    updated_at: datetime | None = None


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


def row_item_cds(row: dict[str, object]) -> list[str]:
    """照合単位行（T-213）に属する得意先品番。まとめる前の行は自分の得意先品番だけ。"""
    values = row.get("item_cds")
    if isinstance(values, list) and values:
        return [str(value) for value in values if str(value or "").strip()]
    item_cd = str(row.get("item_cd") or "").strip()
    return [item_cd] if item_cd else []


def unit_confirmation(item_cds, confirmations: dict[str, ConfirmationRecord]) -> ConfirmationRecord | None:
    """照合単位行の確認記録: 単位内の得意先品番の記録のうち最も新しく更新されたもの（spec/13 REQ-RUR-F-012）。

    照合単位が分かれても、各単位は自分の得意先品番の記録を引き継ぐ。品番が加わっても既存の記録を引き継ぐ。
    """
    records = [confirmations[item_cd] for item_cd in item_cds if item_cd in confirmations]
    if not records:
        return None
    return max(records, key=lambda record: (record.updated_at is not None, record.updated_at or 0, record.item_cd))


def merge_memo_entries(records) -> list[MemoEntryRecord]:
    """照合単位行の確認メモ: メモ識別子（空なら id）で 1 件にまとめ、新しい順に並べる（spec/13 design §4.1）。"""
    entries: dict[str, MemoEntryRecord] = {}
    for record in records:
        for entry in record.memo_entries:
            identity = f"g:{entry.entry_group}" if entry.entry_group else f"id:{entry.entry_id}"
            entries.setdefault(identity, entry)
    return sorted(
        entries.values(),
        key=lambda entry: (entry.created_at is not None, entry.created_at or 0, entry.entry_id),
        reverse=True,
    )


def attach_confirmation_fields(
    rows: list[dict[str, object]],
    confirmations: dict[str, ConfirmationRecord],
    *,
    author_names: dict[str, str] | None = None,
) -> list[dict[str, object]]:
    """行に確認状態を付ける。確認記録は得意先品番ごと（spec/13 REQ-RUR-F-011）。

    照合単位行は `item_cds` の記録から最も新しいものを採り、確認メモは単位内の記録から集めて 1 件にまとめる。
    """
    enriched: list[dict[str, object]] = []
    for row in rows:
        copied = dict(row)
        item_cds = row_item_cds(copied)
        confirmation = unit_confirmation(item_cds, confirmations)
        if confirmation:
            records = [confirmations[item_cd] for item_cd in item_cds if item_cd in confirmations]
            copied["confirmation_status"] = confirmation_label(confirmation.status)
            copied["confirmed_at"] = format_display_datetime(confirmation.confirmed_at)
            copied["confirmed_by"] = confirmation.confirmed_by
            if len(records) == 1:
                copied["confirmation_memo"] = confirmation.memo
                copied["confirmation_memo_history"] = confirmation.memo_history
            else:
                entries = merge_memo_entries(records)
                copied["confirmation_memo"] = entries[0].content if entries else ""
                copied["confirmation_memo_history"] = format_memo_history_csv(entries, author_names=author_names)
        else:
            copied.setdefault("confirmation_status", "未確認")
            copied.setdefault("confirmed_at", "")
            copied.setdefault("confirmed_by", "")
            copied.setdefault("confirmation_memo", "")
            copied.setdefault("confirmation_memo_history", "")
        enriched.append(copied)
    return enriched
