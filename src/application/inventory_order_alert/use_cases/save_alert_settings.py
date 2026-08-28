from __future__ import annotations

from application.inventory_order_alert.domain.repositories.ports import SaveWarningMonthSettings
from application.inventory_order_alert.domain.value_objects.app_settings import parse_alert_settings_payload


class SaveAlertSettings:
    def __init__(self, save_warning_months: SaveWarningMonthSettings) -> None:
        self._save_warning_months = save_warning_months

    def execute(self, payload: dict[str, object], *, updated_by: object) -> None:
        input_data = parse_alert_settings_payload(payload)
        self._save_warning_months(
            warning_shipment_months=input_data.warning_shipment_months,
            warning_incoming_months=input_data.warning_incoming_months,
            updated_by=updated_by,
        )
