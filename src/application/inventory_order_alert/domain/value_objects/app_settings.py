from __future__ import annotations

from dataclasses import dataclass

MIN_WARNING_MONTHS = 1
MAX_WARNING_MONTHS = 36
MIN_WARNING_DAYS = 1
MAX_WARNING_DAYS = 3650
MIN_STOCK_STALE_DAYS = 1
MAX_STOCK_STALE_DAYS = 365


def _require_in_range(value: int, *, label: str, minimum: int, maximum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{label}は整数で指定してください。")
    if not minimum <= value <= maximum:
        raise ValueError(f"{label}は {minimum}〜{maximum} で指定してください。")


@dataclass(frozen=True)
class AppSettings:
    """在庫発注アラートの設定値（§13.1）。範囲外の値では生成できない。"""

    warning_days: int = 365
    warning_shipment_months: int = 12
    warning_incoming_months: int = 12
    critical_enabled: bool = True
    stock_stale_days: int = 7

    def __post_init__(self) -> None:
        _require_in_range(
            self.warning_days,
            label="警告アラート閾値（日数）",
            minimum=MIN_WARNING_DAYS,
            maximum=MAX_WARNING_DAYS,
        )
        _require_in_range(
            self.warning_shipment_months,
            label="出荷ありの月数",
            minimum=MIN_WARNING_MONTHS,
            maximum=MAX_WARNING_MONTHS,
        )
        _require_in_range(
            self.warning_incoming_months,
            label="出荷なしの月数",
            minimum=MIN_WARNING_MONTHS,
            maximum=MAX_WARNING_MONTHS,
        )
        _require_in_range(
            self.stock_stale_days,
            label="SLIMS 取込警告日数",
            minimum=MIN_STOCK_STALE_DAYS,
            maximum=MAX_STOCK_STALE_DAYS,
        )
        if not isinstance(self.critical_enabled, bool):
            raise ValueError("重点アラートは true / false で指定してください。")


@dataclass(frozen=True)
class AlertSettingsInput:
    warning_shipment_months: int
    warning_incoming_months: int


@dataclass(frozen=True)
class SettingsInput:
    warning_days: int
    critical_enabled: bool
    stock_stale_days: int


def clamp_warning_months(value: int) -> int:
    return max(MIN_WARNING_MONTHS, min(MAX_WARNING_MONTHS, int(value)))


def clamp_warning_days(value: int) -> int:
    return max(MIN_WARNING_DAYS, min(MAX_WARNING_DAYS, int(value)))


def clamp_stock_stale_days(value: int) -> int:
    return max(MIN_STOCK_STALE_DAYS, min(MAX_STOCK_STALE_DAYS, int(value)))


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


def _parse_int_in_range(value: object, *, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{label}は整数で指定してください。")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}は整数で指定してください。") from exc
    if not minimum <= parsed <= maximum:
        raise ValueError(f"{label}は {minimum}〜{maximum} で指定してください。")
    return parsed


def _parse_bool(value: object, *, label: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in {"true", "1", "on"}:
        return True
    if isinstance(value, str) and value.strip().lower() in {"false", "0", "off"}:
        return False
    raise ValueError(f"{label}は true / false で指定してください。")


def parse_settings_payload(data: object, *, current: AppSettings | None = None) -> SettingsInput:
    """設定 API（§8.10）の入力を検証する。未指定のキーは現在値を引き継ぐ。"""
    if not isinstance(data, dict):
        raise ValueError("JSON の形式が不正です。")

    base = current or AppSettings()
    warning_days = base.warning_days
    if "warningDays" in data:
        warning_days = _parse_int_in_range(
            data["warningDays"],
            label="警告アラート閾値（日数）",
            minimum=MIN_WARNING_DAYS,
            maximum=MAX_WARNING_DAYS,
        )

    stock_stale_days = base.stock_stale_days
    if "stockStaleDays" in data:
        stock_stale_days = _parse_int_in_range(
            data["stockStaleDays"],
            label="SLIMS 取込警告日数",
            minimum=MIN_STOCK_STALE_DAYS,
            maximum=MAX_STOCK_STALE_DAYS,
        )

    critical_enabled = base.critical_enabled
    if "criticalEnabled" in data:
        critical_enabled = _parse_bool(data["criticalEnabled"], label="重点アラート")

    return SettingsInput(
        warning_days=warning_days,
        critical_enabled=critical_enabled,
        stock_stale_days=stock_stale_days,
    )


def settings_payload(settings: AppSettings) -> dict[str, object]:
    """設定 API（§8.10）・設定画面（§4.2）で用いる JSON 表現を返す。"""
    return {
        "warningDays": settings.warning_days,
        "warningShipmentMonths": settings.warning_shipment_months,
        "warningIncomingMonths": settings.warning_incoming_months,
        "criticalEnabled": settings.critical_enabled,
        "stockStaleDays": settings.stock_stale_days,
    }
