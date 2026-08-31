from __future__ import annotations

from dataclasses import dataclass

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
    """在庫発注アラートの設定値（§13.1）。範囲外の値では生成できない。

    警告条件（出荷ありの月数・出荷なしの月数・重点アラート）は流動区分の判定に用いないため
    撤去した（design.md §6.5）。DB カラムは残置しており、ここからは参照しない（§5.3）。
    """

    warning_days: int = 365
    stock_stale_days: int = 7

    def __post_init__(self) -> None:
        _require_in_range(
            self.warning_days,
            label="警告アラート閾値（日数）",
            minimum=MIN_WARNING_DAYS,
            maximum=MAX_WARNING_DAYS,
        )
        _require_in_range(
            self.stock_stale_days,
            label="SLIMS 取込警告日数",
            minimum=MIN_STOCK_STALE_DAYS,
            maximum=MAX_STOCK_STALE_DAYS,
        )


@dataclass(frozen=True)
class SettingsInput:
    warning_days: int
    stock_stale_days: int


def clamp_warning_days(value: int) -> int:
    return max(MIN_WARNING_DAYS, min(MAX_WARNING_DAYS, int(value)))


def clamp_stock_stale_days(value: int) -> int:
    return max(MIN_STOCK_STALE_DAYS, min(MAX_STOCK_STALE_DAYS, int(value)))


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


def parse_settings_payload(data: object, *, current: AppSettings | None = None) -> SettingsInput:
    """設定 API（§8.10）の入力を検証する。未指定のキーは現在値を引き継ぐ。

    撤去済みの `criticalEnabled` などの未知のキーは静かに無視する（design.md §8）。
    """
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

    return SettingsInput(
        warning_days=warning_days,
        stock_stale_days=stock_stale_days,
    )


def settings_payload(settings: AppSettings) -> dict[str, object]:
    """設定 API（§8.10）・設定画面（§4.2）で用いる JSON 表現を返す。"""
    return {
        "warningDays": settings.warning_days,
        "stockStaleDays": settings.stock_stale_days,
    }
