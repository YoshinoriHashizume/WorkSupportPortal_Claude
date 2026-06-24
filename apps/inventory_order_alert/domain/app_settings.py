from __future__ import annotations

from dataclasses import dataclass

MIN_WARNING_MONTHS = 1
MAX_WARNING_MONTHS = 36


@dataclass(frozen=True)
class AppSettings:
    warning_days: int = 365
    warning_shipment_months: int = 12
    warning_incoming_months: int = 12
    critical_enabled: bool = True
    stock_stale_days: int = 7


@dataclass(frozen=True)
class AlertSettingsInput:
    warning_shipment_months: int
    warning_incoming_months: int


def clamp_warning_months(value: int) -> int:
    return max(MIN_WARNING_MONTHS, min(MAX_WARNING_MONTHS, int(value)))


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
