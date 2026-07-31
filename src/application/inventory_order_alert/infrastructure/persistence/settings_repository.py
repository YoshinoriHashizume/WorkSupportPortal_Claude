from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings, clamp_warning_months
from application.inventory_order_alert.models import InventoryOrderAlertSettings


def load_app_settings() -> AppSettings:
    settings_row, _ = InventoryOrderAlertSettings.objects.get_or_create(pk=1)
    return AppSettings(
        warning_days=settings_row.warning_days,
        warning_shipment_months=clamp_warning_months(settings_row.warning_shipment_months),
        warning_incoming_months=clamp_warning_months(settings_row.warning_incoming_months),
        critical_enabled=settings_row.critical_enabled,
        stock_stale_days=settings_row.stock_stale_days,
    )


def save_warning_month_settings(
    *,
    warning_shipment_months: int,
    warning_incoming_months: int,
    updated_by: object | None = None,
) -> AppSettings:
    settings_row, _ = InventoryOrderAlertSettings.objects.get_or_create(pk=1)
    shipment_months = clamp_warning_months(warning_shipment_months)
    incoming_months = clamp_warning_months(warning_incoming_months)
    settings_row.warning_shipment_months = shipment_months
    settings_row.warning_incoming_months = incoming_months
    settings_row.balance_shipment_months = shipment_months
    update_fields = [
        "warning_shipment_months",
        "warning_incoming_months",
        "balance_shipment_months",
        "updated_at",
    ]
    if updated_by is not None:
        settings_row.updated_by = updated_by
        update_fields.append("updated_by")
    settings_row.save(update_fields=update_fields)
    return load_app_settings()
