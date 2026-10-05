from __future__ import annotations

import pytest

from application.inventory_order_alert.domain.value_objects.confirmation import (
    STATUS_CHOICES,
    STATUS_CONFIRMED,
    STATUS_IN_PROGRESS,
    STATUS_UNCONFIRMED,
    ConfirmationRecord,
    confirmation_label,
    confirmation_status_key,
    confirmation_status_sort_key,
    confirmation_status_sort_rank,
)
from application.inventory_order_alert.domain.value_objects.flow_quadrant import QUADRANT_LOW_FLOW_NO_INCOMING


def test_confirmation_record_has_confirmed_flow_quadrant_field():
    record = ConfirmationRecord(
        cust_code="112",
        item_cd="90249-10112",
        status=STATUS_CONFIRMED,
        memo="",
        confirmed_flow_quadrant=QUADRANT_LOW_FLOW_NO_INCOMING,
        confirmed_at=None,
        confirmed_by="10001",
    )

    assert record.confirmed_flow_quadrant == QUADRANT_LOW_FLOW_NO_INCOMING
    assert not hasattr(record, "confirmed_alert_level")


def test_confirmation_label_returns_japanese_label():
    assert confirmation_label(STATUS_UNCONFIRMED) == "未確認"
    assert confirmation_label(STATUS_IN_PROGRESS) == "確認中"
    assert confirmation_label(STATUS_CONFIRMED) == "確認済み"
    assert confirmation_label("unknown") == "未確認"


def test_confirmation_status_key_maps_from_row_label():
    row = {"confirmation_status": "確認済み"}
    assert confirmation_status_key(row) == STATUS_CONFIRMED


def test_confirmation_status_key_defaults_to_unconfirmed():
    assert confirmation_status_key({}) == STATUS_UNCONFIRMED


def test_confirmation_status_sort_rank_orders_statuses():
    assert confirmation_status_sort_rank(STATUS_UNCONFIRMED) == 0
    assert confirmation_status_sort_rank(STATUS_IN_PROGRESS) == 1
    assert confirmation_status_sort_rank(STATUS_CONFIRMED) == 2
    assert confirmation_status_sort_rank("unknown") == 99


def test_confirmation_status_sort_key_uses_row_label():
    assert confirmation_status_sort_key({"confirmation_status": "未確認"}) == 0
    assert confirmation_status_sort_key({"confirmation_status": "確認中"}) == 1
    assert confirmation_status_sort_key({"confirmation_status": "確認済み"}) == 2


def test_status_choices_cover_all_valid_statuses():
    values = {value for value, _label in STATUS_CHOICES}
    assert values == {STATUS_UNCONFIRMED, STATUS_IN_PROGRESS, STATUS_CONFIRMED}


@pytest.mark.django_db
def test_load_confirmation_map_includes_memo_history():
    from application.inventory_order_alert.infrastructure.persistence.confirmation_repository import load_confirmation_map
    from application.inventory_order_alert.models import ConfirmationStatus, InventoryOrderAlertConfirmation

    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.UNCONFIRMED,
        memo="最新メモ",
    )
    confirmation_map = load_confirmation_map()
    record = confirmation_map[("112", "ITEM-A")]
    assert record.memo == "最新メモ"
    assert record.status == STATUS_UNCONFIRMED


@pytest.mark.django_db
def test_has_resettable_confirmations():
    from application.inventory_order_alert.infrastructure.persistence.confirmation_repository import (
        has_resettable_confirmations,
    )
    from application.inventory_order_alert.models import ConfirmationStatus, InventoryOrderAlertConfirmation

    assert has_resettable_confirmations() is False
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.IN_PROGRESS,
    )
    assert has_resettable_confirmations() is True
