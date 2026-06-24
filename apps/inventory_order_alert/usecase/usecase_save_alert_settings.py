from __future__ import annotations

from collections.abc import Callable

from apps.inventory_order_alert.domain.app_settings import parse_alert_settings_payload
from apps.inventory_order_alert.domain.app_settings import AppSettings

SaveWarningMonthSettings = Callable[..., AppSettings]


class SaveAlertSettingsUsecase:
    def __init__(self, save_warning_months: SaveWarningMonthSettings) -> None:
        self._save_warning_months = save_warning_months

    def execute(self, payload: dict[str, object], *, updated_by: object) -> None:
        input_data = parse_alert_settings_payload(payload)
        self._save_warning_months(
            warning_shipment_months=input_data.warning_shipment_months,
            warning_incoming_months=input_data.warning_incoming_months,
            updated_by=updated_by,
        )
