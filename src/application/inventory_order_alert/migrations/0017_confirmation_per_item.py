"""確認記録を得意先品番ごとに 1 件にする（spec/13 design §5.3・REQ-RUR-F-013）。

1. 確認メモにメモ識別子（entry_group）を足す
2. 得意先品番ごとに、最も新しく更新された確認記録を残す。残さない記録の確認メモは残す記録へ付け替える
   （メモは 1 件も削除しない。移行の前後でメモの件数が変わったら例外にして中止する）
3. 一意制約を（得意先コード, 得意先品番）から得意先品番に付け替える

逆方向は制約を戻すだけで、統合した記録は元の得意先ごとに分け直さない（分け直す情報がないため）。
どれを残してどのメモを付け替えるかの判断は DB に依存しない `plan_confirmation_merge` に置く（テストで確かめる）。
"""

from dataclasses import dataclass, field
from datetime import datetime

from django.db import migrations, models


@dataclass(frozen=True)
class ConfirmationSnapshot:
    pk: int
    item_cd: str
    updated_at: datetime | None
    memo_ids: tuple[int, ...] = ()


@dataclass
class ConfirmationMergePlan:
    kept_pks: set[int] = field(default_factory=set)
    dropped_pks: set[int] = field(default_factory=set)
    #: 付け替える確認メモの id → 付け替え先の確認記録の pk
    memo_moves: dict[int, int] = field(default_factory=dict)


def plan_confirmation_merge(records: list[ConfirmationSnapshot]) -> ConfirmationMergePlan:
    """得意先品番ごとに最も新しく更新された記録を残し、他の記録のメモを付け替える計画を立てる。"""
    plan = ConfirmationMergePlan()
    by_item: dict[str, list[ConfirmationSnapshot]] = {}
    for record in records:
        by_item.setdefault(record.item_cd, []).append(record)
    for group in by_item.values():
        ordered = sorted(
            group,
            key=lambda record: (record.updated_at is not None, record.updated_at or datetime.min, record.pk),
            reverse=True,
        )
        kept, *dropped = ordered
        plan.kept_pks.add(kept.pk)
        for record in dropped:
            plan.dropped_pks.add(record.pk)
            for memo_id in record.memo_ids:
                plan.memo_moves[memo_id] = kept.pk
    return plan


def merge_confirmations_per_item(apps, schema_editor):
    confirmation_model = apps.get_model("inventory_order_alert", "InventoryOrderAlertConfirmation")
    memo_model = apps.get_model("inventory_order_alert", "InventoryOrderAlertConfirmationMemoEntry")

    memo_count_before = memo_model.objects.count()
    record_count_before = confirmation_model.objects.count()

    memo_ids_by_record: dict[int, list[int]] = {}
    for memo_id, confirmation_id in memo_model.objects.values_list("id", "confirmation_id"):
        memo_ids_by_record.setdefault(confirmation_id, []).append(memo_id)
    snapshots = [
        ConfirmationSnapshot(
            pk=pk,
            item_cd=item_cd,
            updated_at=updated_at,
            memo_ids=tuple(memo_ids_by_record.get(pk, ())),
        )
        for pk, item_cd, updated_at in confirmation_model.objects.values_list("pk", "item_cd", "updated_at")
    ]
    plan = plan_confirmation_merge(snapshots)

    moves_by_target: dict[int, list[int]] = {}
    for memo_id, target_pk in plan.memo_moves.items():
        moves_by_target.setdefault(target_pk, []).append(memo_id)
    for target_pk, memo_ids in moves_by_target.items():
        memo_model.objects.filter(id__in=memo_ids).update(confirmation_id=target_pk)
        latest = memo_model.objects.filter(confirmation_id=target_pk).order_by("-created_at", "-id").first()
        if latest is not None:
            confirmation_model.objects.filter(pk=target_pk).update(memo=latest.content)
    confirmation_model.objects.filter(pk__in=plan.dropped_pks).delete()

    memo_count_after = memo_model.objects.count()
    record_count_after = confirmation_model.objects.count()
    print(
        f"\n  確認記録: {record_count_before} 件 → {record_count_after} 件"
        f" / 確認メモ: {memo_count_before} 件 → {memo_count_after} 件"
    )
    if memo_count_after != memo_count_before:
        raise RuntimeError(f"確認メモの件数が変わったため移行を中止します: {memo_count_before} → {memo_count_after}")


class Migration(migrations.Migration):

    dependencies = [
        ("inventory_order_alert", "0016_direct_shipment_suppliers"),
    ]

    operations = [
        migrations.AddField(
            model_name="inventoryorderalertconfirmationmemoentry",
            name="entry_group",
            field=models.CharField(blank=True, default="", max_length=36),
        ),
        migrations.RunPython(merge_confirmations_per_item, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="inventoryorderalertconfirmation",
            name="unique_inventory_order_alert_confirmation",
        ),
        migrations.AddConstraint(
            model_name="inventoryorderalertconfirmation",
            constraint=models.UniqueConstraint(fields=("item_cd",), name="unique_inventory_order_alert_confirmation_item"),
        ),
    ]
