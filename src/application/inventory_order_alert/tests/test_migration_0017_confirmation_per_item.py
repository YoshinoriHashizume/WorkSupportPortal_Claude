"""確認記録の移行（migration 0017。spec/13 test-design TC-RUR-I-020〜025）。

テストのスキーマはマイグレーションを使わずモデルから作る（ルートの conftest.py `django_db_use_migrations`）。
そのため 0016 に戻して重複した記録を作ることはできない。移行の判断（どの記録を残し、どのメモを付け替えるか）は
マイグレーションの DB 非依存の関数 `plan_confirmation_merge` で確かめ、実際の移行はタスク25 で開発 DB に migrate して確かめる。
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from importlib import import_module

import pytest
from django.db import IntegrityError, transaction

from application.inventory_order_alert.models import InventoryOrderAlertConfirmation

migration_module = import_module("application.inventory_order_alert.migrations.0017_confirmation_per_item")
plan_confirmation_merge = migration_module.plan_confirmation_merge
ConfirmationSnapshot = migration_module.ConfirmationSnapshot


def _at(day: int) -> datetime:
    return datetime(2026, 11, day, 9, 0, tzinfo=dt_timezone.utc)


def _record(pk: int, item_cd: str, updated_day: int, memo_ids: tuple[int, ...] = ()) -> ConfirmationSnapshot:
    return ConfirmationSnapshot(pk=pk, item_cd=item_cd, updated_at=_at(updated_day), memo_ids=memo_ids)


def test_i020_newest_record_is_kept_for_the_same_item():
    plan = plan_confirmation_merge([_record(1, "X", 20), _record(2, "X", 24)])

    assert plan.kept_pks == {2}
    assert plan.dropped_pks == {1}


def test_i021_memos_of_dropped_records_move_to_the_kept_record():
    plan = plan_confirmation_merge([_record(1, "X", 20, (11, 12)), _record(2, "X", 24, (13,))])

    assert plan.memo_moves == {11: 2, 12: 2}


def test_i022_memo_count_is_unchanged():
    records = [
        _record(1, "X", 20, (11, 12)),
        _record(2, "X", 24, (13,)),
        _record(3, "X", 22, (14,)),
        _record(4, "Y", 20, (15, 16, 17)),
        _record(5, "Z", 21),
    ]

    plan = plan_confirmation_merge(records)

    all_memos = {memo for record in records for memo in record.memo_ids}
    kept_memos = {memo for record in records if record.pk in plan.kept_pks for memo in record.memo_ids}
    assert kept_memos | set(plan.memo_moves) == all_memos
    assert len(all_memos) == 7
    assert plan.kept_pks == {2, 4, 5}


def test_i023_records_without_duplicates_are_kept_as_is():
    plan = plan_confirmation_merge([_record(4, "Y", 20, (15,))])

    assert plan.kept_pks == {4}
    assert plan.dropped_pks == set()
    assert plan.memo_moves == {}


@pytest.mark.django_db
def test_i024_item_is_unique_after_migration():
    InventoryOrderAlertConfirmation.objects.create(cust_code="104", item_cd="X", status="confirmed")

    with pytest.raises(IntegrityError), transaction.atomic():
        InventoryOrderAlertConfirmation.objects.create(cust_code="999", item_cd="X", status="unconfirmed")


def test_i025_empty_table_migrates():
    plan = plan_confirmation_merge([])

    assert plan.kept_pks == set()
    assert plan.dropped_pks == set()
