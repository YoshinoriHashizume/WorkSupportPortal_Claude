from __future__ import annotations

import pytest

from apps.inventory_order_alert.domain.confirmation import (
    STATUS_CHOICES,
    STATUS_CONFIRMED,
    STATUS_IN_PROGRESS,
    STATUS_UNCONFIRMED,
    confirmation_label,
    confirmation_status_key,
)


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


def test_status_choices_cover_all_valid_statuses():
    values = {value for value, _label in STATUS_CHOICES}
    assert values == {STATUS_UNCONFIRMED, STATUS_IN_PROGRESS, STATUS_CONFIRMED}


@pytest.mark.django_db
def test_load_confirmation_map_includes_memo_history():
    from apps.inventory_order_alert.infrastructure.persistence.confirmation_repository import load_confirmation_map
    from apps.inventory_order_alert.models import ConfirmationStatus, InventoryOrderAlertConfirmation

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
    from apps.inventory_order_alert.infrastructure.persistence.confirmation_repository import (
        has_resettable_confirmations,
    )
    from apps.inventory_order_alert.models import ConfirmationStatus, InventoryOrderAlertConfirmation

    assert has_resettable_confirmations() is False
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.IN_PROGRESS,
    )
    assert has_resettable_confirmations() is True
