from __future__ import annotations

import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from application.inventory_order_alert.domain.value_objects.confirmation import parse_memo_entry_payload
from application.inventory_order_alert.domain.value_objects.confirmation import (
    ConfirmationInput,
    parse_confirmation_payload,
)
from application.inventory_order_alert.infrastructure.persistence.confirmation_repository import (
    add_confirmation_memo,
    save_confirmation,
)
from application.inventory_order_alert.models import ConfirmationStatus, InventoryOrderAlertConfirmation
from application.portal.models import PortalMenuGroupAccess


@pytest.fixture
def production_user(db):
    user = get_user_model().objects.create_user(username="10002", last_name="生産", first_name="担当")
    admin_group, _ = Group.objects.get_or_create(name="管理者")
    user.groups.add(admin_group)
    PortalMenuGroupAccess.objects.get_or_create(user=user, group_key="production")
    return user


def test_parse_confirmation_payload_accepts_valid_input():
    parsed = parse_confirmation_payload(
        {
            "custCode": "112",
            "itemCd": "90249-10112",
            "status": "confirmed",
        }
    )
    assert parsed == ConfirmationInput(
        cust_code="112",
        item_cd="90249-10112",
        status="confirmed",
    )


def test_parse_confirmation_payload_rejects_invalid_status():
    with pytest.raises(ValueError, match="status"):
        parse_confirmation_payload(
            {
                "custCode": "112",
                "itemCd": "90249-10112",
                "status": "invalid",
            }
        )


@pytest.mark.django_db
def test_save_confirmation_upserts_and_sets_confirmed_metadata(production_user):
    save_confirmation(
        ConfirmationInput(
            cust_code="112",
            item_cd="ITEM-A",
            status=ConfirmationStatus.CONFIRMED,
        ),
        confirmed_by=production_user.username,
        flow_quadrant="通常流動品",
    )

    confirmation = InventoryOrderAlertConfirmation.objects.get(cust_code="112", item_cd="ITEM-A")
    assert confirmation.status == ConfirmationStatus.CONFIRMED
    assert confirmation.confirmed_by == "10002"
    assert confirmation.confirmed_at is not None
    assert confirmation.confirmed_flow_quadrant == "通常流動品"


@pytest.mark.django_db
def test_save_confirmation_preserves_existing_memo(production_user):
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.CONFIRMED,
        confirmed_by="10001",
        memo="旧メモ",
    )
    add_confirmation_memo(
        cust_code="112",
        item_cd="ITEM-A",
        content="旧メモ",
        created_by="10001",
    )

    save_confirmation(
        ConfirmationInput(
            cust_code="112",
            item_cd="ITEM-A",
            status=ConfirmationStatus.UNCONFIRMED,
        ),
        confirmed_by=production_user.username,
    )

    confirmation = InventoryOrderAlertConfirmation.objects.get(cust_code="112", item_cd="ITEM-A")
    assert confirmation.status == ConfirmationStatus.UNCONFIRMED
    assert confirmation.memo == "旧メモ"
    assert confirmation.confirmed_by == ""
    assert confirmation.confirmed_at is None
    assert confirmation.confirmed_flow_quadrant == ""


@pytest.mark.django_db
def test_api_save_confirmation_returns_ok(client, production_user):
    client.force_login(production_user)
    response = client.put(
        "/api/inventory-order-alert/confirmation",
        data=json.dumps(
            {
                "custCode": "112",
                "itemCd": "ITEM-B",
                "status": "confirmed",
            }
        ),
        content_type="application/json",
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["confirmationStatusKey"] == "confirmed"
    assert payload["alertRowClass"] == "確認済"
    assert "counts" in payload
    confirmation = InventoryOrderAlertConfirmation.objects.get(cust_code="112", item_cd="ITEM-B")
    assert confirmation.status == ConfirmationStatus.CONFIRMED


@pytest.mark.django_db
def test_api_reset_confirmations_resets_all_active_statuses(client, production_user):
    confirmation = InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.CONFIRMED,
        memo="回答あり",
        confirmed_by="10001",
    )
    add_confirmation_memo(
        cust_code="112",
        item_cd="ITEM-A",
        content="回答あり",
        created_by="10001",
    )
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-B",
        status=ConfirmationStatus.IN_PROGRESS,
        memo="確認中",
        confirmed_by="10002",
    )

    client.force_login(production_user)
    response = client.post(
        "/api/inventory-order-alert/confirmation/reset",
        data=json.dumps({}),
        content_type="application/json",
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["resetCount"] == 2
    assert payload["counts"]["confirmed"] == 0
    assert payload["counts"]["inProgress"] == 0
    assert InventoryOrderAlertConfirmation.objects.filter(
        status__in=(ConfirmationStatus.CONFIRMED, ConfirmationStatus.IN_PROGRESS),
    ).count() == 0
    assert InventoryOrderAlertConfirmation.objects.get(cust_code="112", item_cd="ITEM-A").memo == "回答あり"
    assert confirmation.memo_entries.count() == 1


@pytest.mark.django_db
def test_api_reset_confirmations_requires_login(client):
    response = client.post("/api/inventory-order-alert/confirmation/reset")
    assert response.status_code == 302
