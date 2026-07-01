from __future__ import annotations

from dataclasses import dataclass

from applications.shipment_trend.domain.app_settings import AppSettings, parse_alert_settings_payload
from applications.shipment_trend.infrastructure.persistence.settings_repository import save_alert_settings


class SaveAlertSettingsUsecase:
    def execute(self, payload: dict[str, object], *, updated_by: object) -> AppSettings:
        settings = parse_alert_settings_payload(payload)
        save_alert_settings(settings, updated_by=updated_by)
        return settings
