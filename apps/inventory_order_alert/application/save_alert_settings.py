from __future__ import annotations

from dataclasses import dataclass

from apps.inventory_order_alert.application.settings_service import (
    MAX_WARNING_MONTHS,
    MIN_WARNING_MONTHS,
    save_warning_month_settings,
)


@dataclass(frozen=True)
class AlertSettingsInput:
    warning_shipment_months: int
    warning_incoming_months: int


def parse_alert_settings_payload(data: object) -> AlertSettingsInput:
    if not isinstance(data, dict):
        raise ValueError("JSON の形式が不正です。")

    try:
        warning_shipment_months = int(data.get("warningShipmentMonths"))
        warning_incoming_months = int(data.get("warningIncomingMonths"))
    except (TypeError, ValueError) as exc:
        raise ValueError("月数は整数で指定してください。") from exc

    if not MIN_WARNING_MONTHS <= warning_shipment_months <= MAX_WARNING_MONTHS:
        raise ValueError(f"出荷ありの月数は {MIN_WARNING_MONTHS}〜{MAX_WARNING_MONTHS} で指定してください。")
    if not MIN_WARNING_MONTHS <= warning_incoming_months <= MAX_WARNING_MONTHS:
        raise ValueError(f"出荷なしの月数は {MIN_WARNING_MONTHS}〜{MAX_WARNING_MONTHS} で指定してください。")

    return AlertSettingsInput(
        warning_shipment_months=warning_shipment_months,
        warning_incoming_months=warning_incoming_months,
    )


def save_alert_settings(input_data: AlertSettingsInput, *, updated_by: object) -> None:
    save_warning_month_settings(
        warning_shipment_months=input_data.warning_shipment_months,
        warning_incoming_months=input_data.warning_incoming_months,
        updated_by=updated_by,
    )
