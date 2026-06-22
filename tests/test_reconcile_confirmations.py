from __future__ import annotations

import pytest

from apps.inventory_order_alert.application.reconcile_confirmations import reconcile_confirmations_after_import, reset_all_confirmations
from apps.inventory_order_alert.domain.alert_level import (
    ALERT_CRITICAL,
    ALERT_NONE,
    ALERT_WARNING_INCOMING,
    ALERT_WARNING_SHIP,
    is_alert_escalated,
)
from apps.inventory_order_alert.models import ConfirmationStatus, InventoryOrderAlertConfirmation


@pytest.mark.parametrize(
    ("previous_level", "current_level", "expected"),
    [
        (ALERT_NONE, ALERT_WARNING_SHIP, True),
        (ALERT_NONE, ALERT_WARNING_INCOMING, True),
        (ALERT_NONE, ALERT_CRITICAL, True),
        (ALERT_WARNING_INCOMING, ALERT_WARNING_SHIP, True),
        (ALERT_WARNING_INCOMING, ALERT_CRITICAL, True),
        (ALERT_WARNING_SHIP, ALERT_CRITICAL, True),
        (ALERT_NONE, ALERT_NONE, False),
        (ALERT_WARNING_SHIP, ALERT_WARNING_SHIP, False),
        (ALERT_WARNING_SHIP, ALERT_WARNING_INCOMING, False),
        (ALERT_CRITICAL, ALERT_WARNING_SHIP, False),
        ("問題なし", ALERT_CRITICAL, True),
    ],
)
def test_is_alert_escalated(previous_level, current_level, expected):
    assert is_alert_escalated(previous_level, current_level) is expected


@pytest.mark.django_db
def test_reconcile_confirmations_resets_when_alert_escalates_to_critical():
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.CONFIRMED,
        confirmed_alert_level=ALERT_NONE,
        confirmed_by="10001",
    )
    rows = [
        {
            "cust_code": "112",
            "item_cd": "ITEM-A",
            "alert_level": ALERT_CRITICAL,
        }
    ]

    reset_count = reconcile_confirmations_after_import(rows)

    confirmation = InventoryOrderAlertConfirmation.objects.get(cust_code="112", item_cd="ITEM-A")
    assert reset_count == 1
    assert confirmation.status == ConfirmationStatus.UNCONFIRMED
    assert confirmation.confirmed_alert_level == ""
    assert confirmation.confirmed_by == ""


@pytest.mark.django_db
def test_reconcile_confirmations_keeps_status_when_alert_unchanged():
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.CONFIRMED,
        confirmed_alert_level=ALERT_NONE,
        confirmed_by="10001",
    )
    rows = [
        {
            "cust_code": "112",
            "item_cd": "ITEM-A",
            "alert_level": ALERT_NONE,
        }
    ]

    reset_count = reconcile_confirmations_after_import(rows)

    confirmation = InventoryOrderAlertConfirmation.objects.get(cust_code="112", item_cd="ITEM-A")
    assert reset_count == 0
    assert confirmation.status == ConfirmationStatus.CONFIRMED


@pytest.mark.django_db
def test_reset_all_confirmations_clears_active_statuses_and_keeps_memo():
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.CONFIRMED,
        memo="回答あり",
        confirmed_alert_level="重点",
        confirmed_by="10001",
    )
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-B",
        status=ConfirmationStatus.IN_PROGRESS,
        memo="確認中メモ",
        confirmed_alert_level="警告（出荷あり）",
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
    assert confirmed.confirmed_alert_level == ""
    assert confirmed.confirmed_by == ""
    assert in_progress.status == ConfirmationStatus.UNCONFIRMED
    assert in_progress.memo == "確認中メモ"
    assert unconfirmed.status == ConfirmationStatus.UNCONFIRMED


@pytest.mark.django_db
def test_reconcile_confirmations_skips_without_confirmed_alert_level():
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.CONFIRMED,
        confirmed_alert_level="",
        confirmed_by="10001",
    )
    rows = [
        {
            "cust_code": "112",
            "item_cd": "ITEM-A",
            "alert_level": ALERT_CRITICAL,
        }
    ]

    reset_count = reconcile_confirmations_after_import(rows)

    confirmation = InventoryOrderAlertConfirmation.objects.get(cust_code="112", item_cd="ITEM-A")
    assert reset_count == 0
    assert confirmation.status == ConfirmationStatus.CONFIRMED
