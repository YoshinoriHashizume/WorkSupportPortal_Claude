from __future__ import annotations

from application.shipment_trend.domain.repositories.ports import SaveAlertSettingsFn
from application.shipment_trend.domain.value_objects.app_settings import AppSettings, parse_alert_settings_payload


class SaveAlertSettings:
    def __init__(self, save: SaveAlertSettingsFn) -> None:
        self._save = save

    def execute(self, payload: dict[str, object], *, updated_by: object) -> AppSettings:
        settings = parse_alert_settings_payload(payload)
        self._save(settings, updated_by=updated_by)
        return settings
