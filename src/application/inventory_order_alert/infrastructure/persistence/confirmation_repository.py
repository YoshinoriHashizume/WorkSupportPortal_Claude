from __future__ import annotations

import uuid

from django.db import transaction
from django.utils import timezone

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    QUADRANT_NORMAL_FLOW,
    is_flow_escalated,
    normalize_flow_quadrant,
)
from application.inventory_order_alert.domain.value_objects.confirmation import (
    ACTIVE_STATUSES,
    ConfirmationInput,
    ConfirmationRecord,
    MemoEntryRecord,
    STATUS_UNCONFIRMED,
    format_memo_history_csv,
    memo_entry_to_dict,
    merge_memo_entries,
    row_item_cds,
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
        entry_group=entry.entry_group or "",
        entry_id=entry.pk or 0,
    )


def _confirmation_from_model(confirmation: InventoryOrderAlertConfirmation) -> ConfirmationRecord:
    entries = tuple(_memo_entry_from_model(entry) for entry in confirmation.memo_entries.all())
    author_names = resolve_user_display_names({entry.created_by for entry in entries})
    return ConfirmationRecord(
        cust_code=confirmation.cust_code,
        item_cd=confirmation.item_cd,
        status=confirmation.status,
        memo=confirmation.memo,
        confirmed_flow_quadrant=confirmation.confirmed_flow_quadrant,
        confirmed_at=confirmation.confirmed_at,
        confirmed_by=confirmation.confirmed_by,
        memo_history=format_memo_history_csv(list(entries), author_names=author_names),
        memo_entries=entries,
        updated_at=confirmation.updated_at,
    )


def load_confirmation_map() -> dict[str, ConfirmationRecord]:
    """確認記録を得意先品番ごとに返す（spec/13 REQ-RUR-F-011）。"""
    return {
        row.item_cd: _confirmation_from_model(row)
        for row in InventoryOrderAlertConfirmation.objects.prefetch_related("memo_entries").all()
    }


def memo_author_names(confirmations: dict[str, ConfirmationRecord]) -> dict[str, str]:
    """照合単位行でまとめた確認メモの作成者を表示名に解決する。"""
    return resolve_user_display_names(
        {entry.created_by for record in confirmations.values() for entry in record.memo_entries}
    )


def has_resettable_confirmations() -> bool:
    return InventoryOrderAlertConfirmation.objects.filter(
        status__in=ACTIVE_STATUSES,
    ).exists()


def _target_item_cds(item_cd: str, item_cds: tuple[str, ...]) -> list[str]:
    targets = [value for value in dict.fromkeys(item_cds or ()) if value]
    return targets or [item_cd]


def _save_item_confirmation(item_cd: str, *, cust_code: str, defaults: dict[str, object]) -> InventoryOrderAlertConfirmation:
    confirmation, _created = InventoryOrderAlertConfirmation.objects.update_or_create(
        item_cd=item_cd,
        defaults={"cust_code": cust_code, **defaults},
    )
    return confirmation


def save_confirmation(
    input_data: ConfirmationInput,
    *,
    confirmed_by: str,
    flow_quadrant: str = "",
    item_cds: tuple[str, ...] = (),
) -> ConfirmationRecord:
    """照合単位行の得意先品番すべてに同じ確認状態を 1 トランザクションで保存する（spec/13 REQ-RUR-F-011）。

    途中で失敗したら全件取り消す。返すのは受け取った得意先品番（代表）の記録。
    """
    confirmed_at = None
    confirmed_by_value = ""
    confirmed_flow_quadrant = ""
    if input_data.status in {ConfirmationStatus.IN_PROGRESS, ConfirmationStatus.CONFIRMED}:
        confirmed_at = timezone.now()
        confirmed_by_value = confirmed_by
        confirmed_flow_quadrant = normalize_flow_quadrant(flow_quadrant or QUADRANT_NORMAL_FLOW)
    defaults = {
        "status": input_data.status,
        "confirmed_at": confirmed_at,
        "confirmed_by": confirmed_by_value,
        "confirmed_flow_quadrant": confirmed_flow_quadrant,
    }

    saved: dict[str, InventoryOrderAlertConfirmation] = {}
    with transaction.atomic():
        for item_cd in _target_item_cds(input_data.item_cd, item_cds):
            saved[item_cd] = _save_item_confirmation(item_cd, cust_code=input_data.cust_code, defaults=defaults)
    representative = saved.get(input_data.item_cd) or next(iter(saved.values()))
    return _confirmation_from_model(representative)


def list_confirmation_memos(*, cust_code: str, item_cd: str, item_cds: tuple[str, ...] = ()) -> list[dict[str, str]]:
    """照合単位行の得意先品番の確認メモを集め、メモ識別子で 1 件にまとめて新しい順に返す（spec/13）。"""
    targets = _target_item_cds(item_cd, item_cds)
    records = [
        _confirmation_from_model(row)
        for row in InventoryOrderAlertConfirmation.objects.filter(item_cd__in=targets).prefetch_related("memo_entries")
    ]
    entries = merge_memo_entries(records)
    author_names = resolve_user_display_names({entry.created_by for entry in entries})
    return [memo_entry_to_dict(entry, author_names=author_names) for entry in entries]


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
    item_cds: tuple[str, ...] = (),
) -> MemoEntryRecord:
    """確認メモを照合単位行の得意先品番の数だけ、同じメモ識別子で複製して追加する（spec/13 design §4.1）。"""
    entry_group = str(uuid.uuid4())
    created: InventoryOrderAlertConfirmationMemoEntry | None = None
    with transaction.atomic():
        for target in _target_item_cds(item_cd, item_cds):
            confirmation, _created = InventoryOrderAlertConfirmation.objects.get_or_create(
                item_cd=target,
                defaults={"cust_code": cust_code, "status": ConfirmationStatus.UNCONFIRMED},
            )
            entry = InventoryOrderAlertConfirmationMemoEntry.objects.create(
                confirmation=confirmation,
                content=content,
                created_by=created_by,
                entry_group=entry_group,
            )
            _sync_confirmation_latest_memo(confirmation)
            if created is None or target == item_cd:
                created = entry
    return _memo_entry_from_model(created)


def reconcile_confirmations_after_import(rows: list[dict[str, object]]) -> int:
    """照合単位行の流動区分が悪化したら、その単位の得意先品番の確認状態を未確認に戻す（spec/13 REQ-RUR-F-014）。

    `rows` は照合単位行（`unit_rows_with_reference_flow` を通したもの）。まとめる前の行でも各行の得意先品番で判定する。
    """
    quadrant_by_item: dict[str, str] = {}
    for row in rows:
        # 行の流動区分は取込側が基準判定条件で付けたもの。利用者の画面選択には依存しない（design.md §5.2）。
        quadrant = normalize_flow_quadrant(str(row.get("flow_quadrant") or ""))
        for item_cd in row_item_cds(row):
            quadrant_by_item[item_cd] = quadrant
    reset_count = 0
    confirmations = InventoryOrderAlertConfirmation.objects.filter(
        status__in=ACTIVE_STATUSES,
    )
    for confirmation in confirmations:
        if not confirmation.confirmed_flow_quadrant:
            continue
        current_quadrant = quadrant_by_item.get(confirmation.item_cd)
        if current_quadrant is None:
            continue
        if not is_flow_escalated(confirmation.confirmed_flow_quadrant, current_quadrant):
            continue
        confirmation.status = STATUS_UNCONFIRMED
        confirmation.confirmed_flow_quadrant = ""
        confirmation.confirmed_at = None
        confirmation.confirmed_by = ""
        confirmation.save(
            update_fields=[
                "status",
                "confirmed_flow_quadrant",
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
        confirmed_flow_quadrant="",
        confirmed_at=None,
        confirmed_by="",
        updated_at=timezone.now(),
    )


__all__ = [
    "add_confirmation_memo",
    "has_resettable_confirmations",
    "list_confirmation_memos",
    "load_confirmation_map",
    "memo_author_names",
    "reconcile_confirmations_after_import",
    "reset_all_confirmations",
    "save_confirmation",
]
