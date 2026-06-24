from __future__ import annotations

import pytest

from apps.inventory_order_alert.domain.app_settings import AppSettings
from apps.inventory_order_alert.infrastructure.persistence.settings_repository import load_app_settings
from apps.inventory_order_alert.models import InventoryOrderAlertSettings


@pytest.mark.django_db
def test_load_app_settings_returns_defaults():
    settings = load_app_settings()
    assert settings == AppSettings(
        warning_days=365,
        warning_shipment_months=12,
        warning_incoming_months=12,
        critical_enabled=True,
        stock_stale_days=7,
    )
    assert InventoryOrderAlertSettings.objects.filter(pk=1).exists()


@pytest.mark.django_db
def test_load_app_settings_reads_saved_values():
    InventoryOrderAlertSettings.objects.update_or_create(
        pk=1,
        defaults={
            "warning_days": 730,
            "warning_shipment_months": 18,
            "warning_incoming_months": 9,
            "critical_enabled": False,
            "stock_stale_days": 3,
        },
    )
    settings = load_app_settings()
    assert settings.warning_days == 730
    assert settings.warning_shipment_months == 18
    assert settings.warning_incoming_months == 9
    assert settings.critical_enabled is False
    assert settings.stock_stale_days == 3
