from __future__ import annotations

from apps.shipment_trend.domain.app_settings import AppSettings, DEFAULT_DECREASE_THRESHOLD_PCT, DEFAULT_INCREASE_THRESHOLD_PCT
from apps.shipment_trend.models import ShipmentTrendSettings


def load_app_settings() -> AppSettings:
    settings_row, _ = ShipmentTrendSettings.objects.get_or_create(
        pk=1,
        defaults={
            "decrease_threshold_pct": DEFAULT_DECREASE_THRESHOLD_PCT,
            "increase_threshold_pct": DEFAULT_INCREASE_THRESHOLD_PCT,
        },
    )
    return AppSettings(
        decrease_threshold_pct=float(settings_row.decrease_threshold_pct),
        increase_threshold_pct=float(settings_row.increase_threshold_pct),
    )


def save_alert_settings(settings: AppSettings, *, updated_by: object | None) -> None:
    ShipmentTrendSettings.objects.update_or_create(
        pk=1,
        defaults={
            "decrease_threshold_pct": settings.decrease_threshold_pct,
            "increase_threshold_pct": settings.increase_threshold_pct,
            "updated_by": updated_by,
        },
    )
