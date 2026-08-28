from __future__ import annotations

import pytest

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    QUADRANT_DORMANT_STOCK,
    QUADRANT_EXCESS_STOCK_RISK,
    QUADRANT_NORMAL_FLOW,
    QUADRANT_SUPPLY_RISK,
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
        (QUADRANT_NORMAL_FLOW, QUADRANT_EXCESS_STOCK_RISK, True),
        (QUADRANT_NORMAL_FLOW, QUADRANT_DORMANT_STOCK, True),
        (QUADRANT_NORMAL_FLOW, QUADRANT_SUPPLY_RISK, True),
        (QUADRANT_EXCESS_STOCK_RISK, QUADRANT_DORMANT_STOCK, True),
        (QUADRANT_EXCESS_STOCK_RISK, QUADRANT_SUPPLY_RISK, True),
        (QUADRANT_DORMANT_STOCK, QUADRANT_SUPPLY_RISK, True),
        (QUADRANT_NORMAL_FLOW, QUADRANT_NORMAL_FLOW, False),
        (QUADRANT_DORMANT_STOCK, QUADRANT_DORMANT_STOCK, False),
        (QUADRANT_DORMANT_STOCK, QUADRANT_EXCESS_STOCK_RISK, False),
        (QUADRANT_SUPPLY_RISK, QUADRANT_DORMANT_STOCK, False),
        ("問題なし", QUADRANT_SUPPLY_RISK, True),
        (LEGACY_CRITICAL, QUADRANT_DORMANT_STOCK, False),
        (LEGACY_WARNING_SHIP, QUADRANT_SUPPLY_RISK, True),
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
    rows = [{"cust_code": "112", "item_cd": "ITEM-A", "flow_quadrant": QUADRANT_SUPPLY_RISK}]

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
    rows = [{"cust_code": "112", "item_cd": "ITEM-A", "flow_quadrant": QUADRANT_SUPPLY_RISK}]

    reset_count = reconcile_confirmations_after_import(rows)

    assert reset_count == 1


@pytest.mark.django_db
def test_reconcile_confirmations_keeps_status_when_legacy_label_is_already_most_severe():
    # 旧「重点」は供給リスク品へ正規化されるため、これ以上の深刻化はない（§9 R-2）。
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
        confirmed_flow_quadrant=QUADRANT_SUPPLY_RISK,
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
    rows = [{"cust_code": "112", "item_cd": "ITEM-A", "flow_quadrant": QUADRANT_SUPPLY_RISK}]

    reset_count = reconcile_confirmations_after_import(rows)

    confirmation = InventoryOrderAlertConfirmation.objects.get(cust_code="112", item_cd="ITEM-A")
    assert reset_count == 0
    assert confirmation.status == ConfirmationStatus.CONFIRMED
