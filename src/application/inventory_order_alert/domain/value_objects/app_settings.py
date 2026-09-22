from __future__ import annotations

from dataclasses import dataclass

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    DEFAULT_RECENT_INCOMING_DAYS,
    MAX_RECENT_INCOMING_DAYS,
    MIN_RECENT_INCOMING_DAYS,
    FlowThresholds,
)
from application.inventory_order_alert.domain.value_objects.stockout_risk import StockoutRiskSettings

MIN_WARNING_DAYS = 1
MAX_WARNING_DAYS = 3650
MIN_STOCK_STALE_DAYS = 1
MAX_STOCK_STALE_DAYS = 365
# 在庫切れリスク（S-204）の閾値（06 design §4.4）
MIN_SAFETY_DAYS = 1
MAX_SAFETY_DAYS = 60
MIN_DEFAULT_LEAD_TIME_DAYS = 1
MAX_DEFAULT_LEAD_TIME_DAYS = 60
MIN_WATCH_MONTHS = 1
MAX_WATCH_MONTHS = 12
# 直近入荷の窓（07 design §5.2）。範囲・既定値は flow_quadrant の定数を正とする


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
    #: 在庫切れリスク（S-204）: 猶予日数がリードタイム＋安全日数以内なら「危険」
    safety_days: int = 14
    #: 品目マスタにリードタイムがない品番の代替値（日）
    default_lead_time_days: int = 5
    #: 在庫切れ予測がこの月数より先なら「監視」
    watch_months: int = 6
    #: 直近入荷とみなす日数（07 REQ-FQR-F-008）。欠品（T-209）の 2 区分の振り分けにのみ使う。判定期間（V-211）とは別物
    recent_incoming_days: int = DEFAULT_RECENT_INCOMING_DAYS

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
        _require_in_range(self.safety_days, label="安全日数", minimum=MIN_SAFETY_DAYS, maximum=MAX_SAFETY_DAYS)
        _require_in_range(
            self.default_lead_time_days,
            label="既定リードタイム（日）",
            minimum=MIN_DEFAULT_LEAD_TIME_DAYS,
            maximum=MAX_DEFAULT_LEAD_TIME_DAYS,
        )
        _require_in_range(self.watch_months, label="監視期間（か月）", minimum=MIN_WATCH_MONTHS, maximum=MAX_WATCH_MONTHS)
        _require_in_range(
            self.recent_incoming_days,
            label="直近入荷の日数",
            minimum=MIN_RECENT_INCOMING_DAYS,
            maximum=MAX_RECENT_INCOMING_DAYS,
        )

    def to_stockout_risk_settings(self) -> StockoutRiskSettings:
        return StockoutRiskSettings(
            safety_days=self.safety_days,
            default_lead_time_days=self.default_lead_time_days,
            watch_months=self.watch_months,
        )

    def to_flow_thresholds(self) -> FlowThresholds:
        return FlowThresholds(recent_incoming_days=self.recent_incoming_days)


@dataclass(frozen=True)
class SettingsInput:
    warning_days: int
    stock_stale_days: int
    safety_days: int = 14
    default_lead_time_days: int = 5
    watch_months: int = 6
    recent_incoming_days: int = DEFAULT_RECENT_INCOMING_DAYS


def clamp_warning_days(value: int) -> int:
    return max(MIN_WARNING_DAYS, min(MAX_WARNING_DAYS, int(value)))


def clamp_stock_stale_days(value: int) -> int:
    return max(MIN_STOCK_STALE_DAYS, min(MAX_STOCK_STALE_DAYS, int(value)))


def clamp_safety_days(value: int) -> int:
    return max(MIN_SAFETY_DAYS, min(MAX_SAFETY_DAYS, int(value)))


def clamp_default_lead_time_days(value: int) -> int:
    return max(MIN_DEFAULT_LEAD_TIME_DAYS, min(MAX_DEFAULT_LEAD_TIME_DAYS, int(value)))


def clamp_watch_months(value: int) -> int:
    return max(MIN_WATCH_MONTHS, min(MAX_WATCH_MONTHS, int(value)))


def clamp_recent_incoming_days(value: int) -> int:
    return max(MIN_RECENT_INCOMING_DAYS, min(MAX_RECENT_INCOMING_DAYS, int(value)))


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

    safety_days = base.safety_days
    if "safetyDays" in data:
        safety_days = _parse_int_in_range(data["safetyDays"], label="安全日数", minimum=MIN_SAFETY_DAYS, maximum=MAX_SAFETY_DAYS)
    default_lead_time_days = base.default_lead_time_days
    if "defaultLeadTimeDays" in data:
        default_lead_time_days = _parse_int_in_range(
            data["defaultLeadTimeDays"],
            label="既定リードタイム（日）",
            minimum=MIN_DEFAULT_LEAD_TIME_DAYS,
            maximum=MAX_DEFAULT_LEAD_TIME_DAYS,
        )
    watch_months = base.watch_months
    if "watchMonths" in data:
        watch_months = _parse_int_in_range(data["watchMonths"], label="監視期間（か月）", minimum=MIN_WATCH_MONTHS, maximum=MAX_WATCH_MONTHS)
    recent_incoming_days = base.recent_incoming_days
    if "recentIncomingDays" in data:
        recent_incoming_days = _parse_int_in_range(
            data["recentIncomingDays"],
            label="直近入荷の日数",
            minimum=MIN_RECENT_INCOMING_DAYS,
            maximum=MAX_RECENT_INCOMING_DAYS,
        )

    return SettingsInput(
        warning_days=warning_days,
        stock_stale_days=stock_stale_days,
        safety_days=safety_days,
        default_lead_time_days=default_lead_time_days,
        watch_months=watch_months,
        recent_incoming_days=recent_incoming_days,
    )


def settings_payload(settings: AppSettings) -> dict[str, object]:
    """設定 API（§8.10）・設定画面（§4.2）で用いる JSON 表現を返す。"""
    return {
        "warningDays": settings.warning_days,
        "stockStaleDays": settings.stock_stale_days,
        "safetyDays": settings.safety_days,
        "defaultLeadTimeDays": settings.default_lead_time_days,
        "watchMonths": settings.watch_months,
        "recentIncomingDays": settings.recent_incoming_days,
    }
