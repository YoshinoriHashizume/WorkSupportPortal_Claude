from __future__ import annotations

from application.inventory_order_alert.domain.repositories.ports import LoadAppSettings, SaveAppSettings
from application.inventory_order_alert.domain.value_objects.app_settings import (
    AppSettings,
    parse_settings_payload,
    settings_payload,
)


class AppSettingsUseCase:
    """設定画面（§4.2）・設定 API（§8.10）の取得／更新を担う。"""

    def __init__(self, load_app_settings: LoadAppSettings, save_app_settings: SaveAppSettings) -> None:
        self._load_app_settings = load_app_settings
        self._save_app_settings = save_app_settings

    def load(self) -> AppSettings:
        return self._load_app_settings()

    def load_payload(self) -> dict[str, object]:
        return settings_payload(self._load_app_settings())

    def save(self, payload: object, *, updated_by: object | None = None) -> dict[str, object]:
        current = self._load_app_settings()
        input_data = parse_settings_payload(payload, current=current)
        saved = self._save_app_settings(
            warning_days=input_data.warning_days,
            stock_stale_days=input_data.stock_stale_days,
            safety_days=input_data.safety_days,
            default_lead_time_days=input_data.default_lead_time_days,
            watch_months=input_data.watch_months,
            recent_incoming_days=input_data.recent_incoming_days,
            updated_by=updated_by,
        )
        return settings_payload(saved)
