from __future__ import annotations

import pytest

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
    QUADRANT_LOW_FLOW_NO_INCOMING,
    is_flow_escalated,
)
from application.inventory_order_alert.infrastructure.persistence.confirmation_repository import (
    reconcile_confirmations_after_import,
    reset_all_confirmations,
)
from application.inventory_order_alert.models import ConfirmationStatus, InventoryOrderAlertConfirmation

#: 移行直後は確認記録に旧アラートレベルのラベルが残る（design.md §5.2 / §9 R-2）。
LEGACY_CRITICAL = "重点"
LEGACY_ALERT_NONE = "アラート無し"
LEGACY_WARNING_SHIP = "警告（出荷あり）"


@pytest.mark.parametrize(
    ("previous_quadrant", "current_quadrant", "expected"),
    [
        (QUADRANT_NORMAL_FLOW, QUADRANT_LOW_FLOW_NO_SHIPMENT, True),
        (QUADRANT_NORMAL_FLOW, QUADRANT_DORMANT_STOCK, True),
        (QUADRANT_NORMAL_FLOW, QUADRANT_LOW_FLOW_NO_INCOMING, True),
        (QUADRANT_LOW_FLOW_NO_SHIPMENT, QUADRANT_DORMANT_STOCK, True),
        (QUADRANT_LOW_FLOW_NO_SHIPMENT, QUADRANT_LOW_FLOW_NO_INCOMING, True),
        (QUADRANT_DORMANT_STOCK, QUADRANT_LOW_FLOW_NO_INCOMING, True),
        (QUADRANT_NORMAL_FLOW, QUADRANT_NORMAL_FLOW, False),
        (QUADRANT_DORMANT_STOCK, QUADRANT_DORMANT_STOCK, False),
        (QUADRANT_DORMANT_STOCK, QUADRANT_LOW_FLOW_NO_SHIPMENT, False),
        (QUADRANT_LOW_FLOW_NO_INCOMING, QUADRANT_DORMANT_STOCK, False),
        ("問題なし", QUADRANT_LOW_FLOW_NO_INCOMING, True),
        (LEGACY_CRITICAL, QUADRANT_DORMANT_STOCK, False),
        (LEGACY_WARNING_SHIP, QUADRANT_LOW_FLOW_NO_INCOMING, True),
    ],
)
def test_is_flow_escalated(previous_quadrant, current_quadrant, expected):
    assert is_flow_escalated(previous_quadrant, current_quadrant) is expected


@pytest.mark.django_db
def test_reconcile_confirmations_resets_when_flow_quadrant_escalates():
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.CONFIRMED,
        confirmed_flow_quadrant=QUADRANT_NORMAL_FLOW,
        confirmed_by="10001",
    )
    rows = [{"cust_code": "112", "item_cd": "ITEM-A", "flow_quadrant": QUADRANT_LOW_FLOW_NO_INCOMING}]

    reset_count = reconcile_confirmations_after_import(rows)

    confirmation = InventoryOrderAlertConfirmation.objects.get(cust_code="112", item_cd="ITEM-A")
    assert reset_count == 1
    assert confirmation.status == ConfirmationStatus.UNCONFIRMED
    assert confirmation.confirmed_flow_quadrant == ""
    assert confirmation.confirmed_by == ""


@pytest.mark.django_db
def test_reconcile_confirmations_keeps_status_when_flow_quadrant_unchanged():
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.CONFIRMED,
        confirmed_flow_quadrant=QUADRANT_NORMAL_FLOW,
        confirmed_by="10001",
    )
    rows = [{"cust_code": "112", "item_cd": "ITEM-A", "flow_quadrant": QUADRANT_NORMAL_FLOW}]

    reset_count = reconcile_confirmations_after_import(rows)

    confirmation = InventoryOrderAlertConfirmation.objects.get(cust_code="112", item_cd="ITEM-A")
    assert reset_count == 0
    assert confirmation.status == ConfirmationStatus.CONFIRMED


@pytest.mark.django_db
def test_reconcile_confirmations_normalizes_legacy_label_before_comparing():
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.CONFIRMED,
        confirmed_flow_quadrant=LEGACY_ALERT_NONE,
        confirmed_by="10001",
    )
    rows = [{"cust_code": "112", "item_cd": "ITEM-A", "flow_quadrant": QUADRANT_LOW_FLOW_NO_INCOMING}]

    reset_count = reconcile_confirmations_after_import(rows)

    assert reset_count == 1


@pytest.mark.django_db
def test_reconcile_confirmations_keeps_status_when_legacy_label_is_already_most_severe():
    # 旧「重点」は低流動品（入荷なし）へ正規化されるため、これ以上の深刻化はない（§9 R-2）。
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.CONFIRMED,
        confirmed_flow_quadrant=LEGACY_CRITICAL,
        confirmed_by="10001",
    )
    rows = [{"cust_code": "112", "item_cd": "ITEM-A", "flow_quadrant": QUADRANT_DORMANT_STOCK}]

    reset_count = reconcile_confirmations_after_import(rows)

    assert reset_count == 0


@pytest.mark.django_db
def test_reconcile_confirmations_ignores_rows_not_in_snapshot():
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.CONFIRMED,
        confirmed_flow_quadrant=QUADRANT_NORMAL_FLOW,
        confirmed_by="10001",
    )

    reset_count = reconcile_confirmations_after_import([])

    assert reset_count == 0


@pytest.mark.django_db
def test_reset_all_confirmations_clears_active_statuses_and_keeps_memo():
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.CONFIRMED,
        memo="回答あり",
        confirmed_flow_quadrant=QUADRANT_LOW_FLOW_NO_INCOMING,
        confirmed_by="10001",
    )
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-B",
        status=ConfirmationStatus.IN_PROGRESS,
        memo="確認中メモ",
        confirmed_flow_quadrant=QUADRANT_DORMANT_STOCK,
        confirmed_by="10002",
    )
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-C",
        status=ConfirmationStatus.UNCONFIRMED,
        memo="未確認メモ",
    )

    reset_count = reset_all_confirmations()

    assert reset_count == 2
    confirmed = InventoryOrderAlertConfirmation.objects.get(cust_code="112", item_cd="ITEM-A")
    in_progress = InventoryOrderAlertConfirmation.objects.get(cust_code="112", item_cd="ITEM-B")
    unconfirmed = InventoryOrderAlertConfirmation.objects.get(cust_code="112", item_cd="ITEM-C")
    assert confirmed.status == ConfirmationStatus.UNCONFIRMED
    assert confirmed.memo == "回答あり"
    assert confirmed.confirmed_flow_quadrant == ""
    assert confirmed.confirmed_by == ""
    assert in_progress.status == ConfirmationStatus.UNCONFIRMED
    assert in_progress.memo == "確認中メモ"
    assert unconfirmed.status == ConfirmationStatus.UNCONFIRMED


@pytest.mark.django_db
def test_reconcile_confirmations_skips_without_confirmed_flow_quadrant():
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.CONFIRMED,
        confirmed_flow_quadrant="",
        confirmed_by="10001",
    )
    rows = [{"cust_code": "112", "item_cd": "ITEM-A", "flow_quadrant": QUADRANT_LOW_FLOW_NO_INCOMING}]

    reset_count = reconcile_confirmations_after_import(rows)

    confirmation = InventoryOrderAlertConfirmation.objects.get(cust_code="112", item_cd="ITEM-A")
    assert reset_count == 0
    assert confirmation.status == ConfirmationStatus.CONFIRMED


# --- 05_single-flow-view: TC-SFV-A-006（新ランクで判定）・TC-SFV-I-010（旧称の確認記録） ---


@pytest.mark.parametrize(
    ("previous_quadrant", "current_quadrant", "expected"),
    [
        (QUADRANT_DORMANT_STOCK, QUADRANT_LOW_FLOW_NO_INCOMING, True),
        (QUADRANT_LOW_FLOW_NO_INCOMING, QUADRANT_DORMANT_STOCK, False),
        # 旧称で保存された確認記録は新区分として比較する
        ("供給リスク品", QUADRANT_LOW_FLOW_NO_INCOMING, False),
        ("在庫過剰リスク品", QUADRANT_DORMANT_STOCK, True),
        ("在庫過剰リスク品", QUADRANT_LOW_FLOW_NO_SHIPMENT, False),
        # 旧キーでも同じ
        ("excess-stock-risk", "low-flow-no-incoming", True),
    ],
)
def test_a006_is_flow_escalated_uses_new_rank_and_normalizes_legacy_names(previous_quadrant, current_quadrant, expected):
    assert is_flow_escalated(previous_quadrant, current_quadrant) is expected


@pytest.mark.django_db
def test_i010_legacy_confirmed_quadrant_is_treated_as_new_quadrant_on_reconcile():
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.CONFIRMED,
        confirmed_flow_quadrant="供給リスク品",
    )
    # 現在も低流動品（入荷なし）なら深刻化ではないので確認状態は保たれる
    rows = [{"cust_code": "112", "item_cd": "ITEM-A", "flow_quadrant": QUADRANT_LOW_FLOW_NO_INCOMING}]

    assert reconcile_confirmations_after_import(rows) == 0
    assert InventoryOrderAlertConfirmation.objects.get(cust_code="112", item_cd="ITEM-A").status == ConfirmationStatus.CONFIRMED


@pytest.mark.django_db
def test_i010_legacy_excess_stock_risk_record_resets_when_row_becomes_dormant():
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.CONFIRMED,
        confirmed_flow_quadrant="在庫過剰リスク品",
    )
    rows = [{"cust_code": "112", "item_cd": "ITEM-A", "flow_quadrant": QUADRANT_DORMANT_STOCK}]

    assert reconcile_confirmations_after_import(rows) == 1
    assert InventoryOrderAlertConfirmation.objects.get(cust_code="112", item_cd="ITEM-A").status == ConfirmationStatus.UNCONFIRMED
