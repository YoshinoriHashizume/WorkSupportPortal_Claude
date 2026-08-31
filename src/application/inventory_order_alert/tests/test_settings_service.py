from __future__ import annotations

import pytest

from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings
from application.inventory_order_alert.infrastructure.persistence import settings_repository
from application.inventory_order_alert.infrastructure.persistence.settings_repository import load_app_settings
from application.inventory_order_alert.models import InventoryOrderAlertSettings

#: 警告条件の保存経路は撤去した（design.md §6.5）。
REMOVED_REPOSITORY_ATTRIBUTES = ("save_warning_month_settings",)


def test_settings_repository_has_no_save_warning_month_settings():
    for attribute in REMOVED_REPOSITORY_ATTRIBUTES:
        assert not hasattr(settings_repository, attribute)


@pytest.mark.django_db
def test_load_app_settings_returns_defaults():
    settings = load_app_settings()
    assert settings == AppSettings(warning_days=365, stock_stale_days=7)
    assert InventoryOrderAlertSettings.objects.filter(pk=1).exists()


@pytest.mark.django_db
def test_load_app_settings_reads_saved_values():
    InventoryOrderAlertSettings.objects.update_or_create(
        pk=1,
        defaults={"warning_days": 730, "stock_stale_days": 3},
    )
    settings = load_app_settings()
    assert settings.warning_days == 730
    assert settings.stock_stale_days == 3


@pytest.mark.django_db
def test_load_app_settings_does_not_read_legacy_columns():
    # 残置カラムに値が入っていても読み取らない（design.md §5.3）。
    InventoryOrderAlertSettings.objects.update_or_create(
        pk=1,
        defaults={
            "warning_days": 365,
            "stock_stale_days": 7,
            "warning_shipment_months": 18,
            "warning_incoming_months": 9,
            "critical_enabled": False,
        },
    )
    settings = load_app_settings()

    assert settings == AppSettings(warning_days=365, stock_stale_days=7)
    for field_name in ("warning_shipment_months", "warning_incoming_months", "critical_enabled"):
        assert not hasattr(settings, field_name)
