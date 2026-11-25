"""確認記録を得意先品番ごとに保存し、照合単位行（T-213）で読み書きする（spec/13 test-design TC-RUR-I-001〜011）。"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest
from django.utils import timezone

from application.inventory_order_alert.domain.value_objects.confirmation import ConfirmationInput
from application.inventory_order_alert.domain.value_objects.list_rows import unit_rows_with_reference_flow
from application.inventory_order_alert.domain.value_objects.reconciliation_unit_row import build_reconciliation_unit_rows
from application.inventory_order_alert.infrastructure.persistence import confirmation_repository as repo
from application.inventory_order_alert.infrastructure.persistence.summary_repository import load_latest_summary
from application.inventory_order_alert.models import (
    InventoryOrderAlertConfirmation,
    InventoryOrderAlertConfirmationMemoEntry,
    InventoryOrderAlertSummarySnapshot,
    SlimsStockImport,
)
from application.inventory_order_alert.tests.test_reconciliation_unit_row import (
    _single_s_row,
    _unit_a_rows,
    _unit_b_rows,
)

AS_OF = date(2026, 11, 25)


def _save(item_cds: tuple[str, ...], status: str = "confirmed", *, cust_code: str = "308", item_cd: str = "P"):
    return repo.save_confirmation(
        ConfirmationInput(cust_code=cust_code, item_cd=item_cd, status=status),
        confirmed_by="u1",
        flow_quadrant="通常流動品",
        item_cds=item_cds,
    )


# --- I-001〜005: 保存 ---


@pytest.mark.django_db
def test_i001_all_items_get_the_same_status():
    _save(("P", "Q"))

    records = list(InventoryOrderAlertConfirmation.objects.order_by("item_cd"))
    assert [(r.item_cd, r.status) for r in records] == [("P", "confirmed"), ("Q", "confirmed")]
    assert records[0].confirmed_by == records[1].confirmed_by == "u1"
    assert records[0].confirmed_at == records[1].confirmed_at


@pytest.mark.django_db
def test_i002_existing_records_are_updated_and_missing_ones_created():
    InventoryOrderAlertConfirmation.objects.create(cust_code="308", item_cd="P", status="in_progress")

    _save(("P", "Q"))

    assert InventoryOrderAlertConfirmation.objects.count() == 2
    assert set(InventoryOrderAlertConfirmation.objects.values_list("status", flat=True)) == {"confirmed"}


@pytest.mark.django_db(transaction=True)
def test_i003_failure_rolls_back_every_item():
    InventoryOrderAlertConfirmation.objects.create(cust_code="308", item_cd="P", status="in_progress")
    original = repo._save_item_confirmation

    def failing(item_cd, **kwargs):
        if item_cd == "Q":
            raise RuntimeError("保存失敗")
        return original(item_cd, **kwargs)

    with patch.object(repo, "_save_item_confirmation", side_effect=failing), pytest.raises(RuntimeError):
        _save(("P", "Q"))

    assert InventoryOrderAlertConfirmation.objects.get(item_cd="P").status == "in_progress"
    assert not InventoryOrderAlertConfirmation.objects.filter(item_cd="Q").exists()


@pytest.mark.django_db
def test_i004_same_item_from_another_customer_is_one_record():
    _save(("X",), cust_code="104", item_cd="X")
    _save(("X",), "in_progress", cust_code="176", item_cd="X")

    assert list(InventoryOrderAlertConfirmation.objects.values_list("item_cd", "status")) == [("X", "in_progress")]


@pytest.mark.django_db
def test_i005_memo_is_copied_to_every_item_with_one_group():
    repo.add_confirmation_memo(cust_code="308", item_cd="P", content="仕入先に確認", created_by="u1", item_cds=("P", "Q"))

    entries = list(InventoryOrderAlertConfirmationMemoEntry.objects.all())
    assert len(entries) == 2
    assert entries[0].entry_group and entries[0].entry_group == entries[1].entry_group
    assert len(repo.list_confirmation_memos(cust_code="308", item_cd="P", item_cds=("P", "Q"))) == 1


# --- I-006〜008: 読み込み ---


def _store_snapshot(rows: list[dict[str, object]]) -> None:
    record = SlimsStockImport.objects.create(file_name="test.csv", row_count=len(rows))
    InventoryOrderAlertSummarySnapshot.objects.create(import_record=record, as_of_date=AS_OF, rows=rows)


@pytest.mark.django_db
def test_i006_loaded_unit_row_carries_the_confirmation():
    _store_snapshot(_unit_a_rows())
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="176", item_cd="X", status="confirmed", confirmed_at=timezone.now(), confirmed_by="u1"
    )

    summary = load_latest_summary()

    assert len(summary.rows) == 1
    assert summary.rows[0]["confirmation_status"] == "確認済み"


@pytest.mark.django_db
def test_i007_loaded_rows_and_counts_are_unit_rows():
    _store_snapshot(_unit_a_rows() + _unit_b_rows() + [_single_s_row()])

    summary = load_latest_summary()

    assert len(summary.rows) == 3
    assert summary.total_count == 3


@pytest.mark.django_db
def test_i008_old_snapshot_rows_can_be_loaded():
    rows = _unit_a_rows()
    for row in rows:
        for key in ("reconciliation_unit_key", "ordering_method", "daily_shipment", "unconfirmed_order_trend"):
            row.pop(key, None)
    _store_snapshot(rows)

    summary = load_latest_summary()

    assert len(summary.rows) == 1


# --- I-010〜011: 取込後の確認リセット ---


def _confirmed(item_cd: str, quadrant: str) -> None:
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="308",
        item_cd=item_cd,
        status="confirmed",
        confirmed_flow_quadrant=quadrant,
        confirmed_at=timezone.now(),
        confirmed_by="u1",
    )


@pytest.mark.django_db
def test_i010_escalated_unit_resets_every_item():
    _confirmed("P", "通常流動品")
    _confirmed("Q", "通常流動品")
    [unit] = build_reconciliation_unit_rows(_unit_b_rows())
    unit["flow_quadrant"] = "欠品"

    assert repo.reconcile_confirmations_after_import([unit]) == 2
    assert set(InventoryOrderAlertConfirmation.objects.values_list("status", flat=True)) == {"unconfirmed"}


@pytest.mark.django_db
def test_i011_one_customer_stopping_does_not_reset_when_the_unit_is_fine():
    rows = _unit_a_rows()
    rows[1]["last_ship_date"] = "2024/01/10"  # 176 だけ出荷が止まっている
    [unit] = unit_rows_with_reference_flow(rows, as_of_date=AS_OF)
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="176",
        item_cd="X",
        status="confirmed",
        confirmed_flow_quadrant=unit["flow_quadrant"],
        confirmed_at=timezone.now(),
        confirmed_by="u1",
    )

    assert repo.reconcile_confirmations_after_import([unit]) == 0
    assert InventoryOrderAlertConfirmation.objects.get(item_cd="X").status == "confirmed"
