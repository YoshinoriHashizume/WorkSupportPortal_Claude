from __future__ import annotations

from dataclasses import dataclass

from apps.shipment_trend.domain.app_settings import AppSettings, parse_alert_settings_payload
from apps.shipment_trend.infrastructure.persistence.settings_repository import save_alert_settings


class SaveAlertSettingsUsecase:
    def execute(self, payload: dict[str, object], *, updated_by: object) -> AppSettings:
        settings = parse_alert_settings_payload(payload)
        save_alert_settings(settings, updated_by=updated_by)
        return settings
