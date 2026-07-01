from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from applications.inventory_order_alert.composition import save_alert_settings_usecase
from applications.inventory_order_alert.domain.app_settings import parse_alert_settings_payload
from applications.inventory_order_alert.infrastructure.persistence.settings_repository import load_app_settings
from applications.inventory_order_alert.models import InventoryOrderAlertSettings
from applications.portal.models import PortalMenuGroupAccess


@pytest.fixture
def production_user(db):
    user = get_user_model().objects.create_user(username="10002", last_name="生産", first_name="担当")
    admin_group, _ = Group.objects.get_or_create(name="管理者")
    user.groups.add(admin_group)
    PortalMenuGroupAccess.objects.get_or_create(user=user, group_key="production")
    return user


def test_parse_alert_settings_payload_accepts_valid_months():
    parsed = parse_alert_settings_payload(
        {"warningShipmentMonths": 18, "warningIncomingMonths": 6}
    )
    assert parsed.warning_shipment_months == 18
    assert parsed.warning_incoming_months == 6


def test_parse_alert_settings_payload_rejects_out_of_range():
    with pytest.raises(ValueError, match="出荷あり"):
        parse_alert_settings_payload({"warningShipmentMonths": 37, "warningIncomingMonths": 6})
    with pytest.raises(ValueError, match="出荷なし"):
        parse_alert_settings_payload({"warningShipmentMonths": 12, "warningIncomingMonths": 0})


@pytest.mark.django_db
def test_save_alert_settings_persists_values(production_user):
    save_alert_settings_usecase().execute(
        {"warningShipmentMonths": 24, "warningIncomingMonths": 9},
        updated_by=production_user,
    )
    settings = load_app_settings()
    assert settings.warning_shipment_months == 24
    assert settings.warning_incoming_months == 9
    row = InventoryOrderAlertSettings.objects.get(pk=1)
    assert row.balance_shipment_months == 24
