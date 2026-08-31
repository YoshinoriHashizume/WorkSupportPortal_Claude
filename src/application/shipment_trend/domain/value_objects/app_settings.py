from __future__ import annotations

from dataclasses import dataclass

DEFAULT_DECREASE_THRESHOLD_PCT = 20.0
DEFAULT_INCREASE_THRESHOLD_PCT = 20.0
MIN_THRESHOLD_PCT = 1.0
MAX_THRESHOLD_PCT = 100.0


def _require_threshold(value: float, *, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label}は数値で指定してください。")
    if not MIN_THRESHOLD_PCT <= value <= MAX_THRESHOLD_PCT:
        raise ValueError(f"{label}は {MIN_THRESHOLD_PCT}〜{MAX_THRESHOLD_PCT} で指定してください。")


@dataclass(frozen=True)
class AppSettings:
    """出荷トレンド一覧のアラート閾値。範囲外の値では生成できない。"""

    decrease_threshold_pct: float
    increase_threshold_pct: float

    def __post_init__(self) -> None:
        _require_threshold(self.decrease_threshold_pct, label="減少アラート閾値")
        _require_threshold(self.increase_threshold_pct, label="増加アラート閾値")


def clamp_threshold(value: float) -> float:
    return max(MIN_THRESHOLD_PCT, min(MAX_THRESHOLD_PCT, value))


def parse_alert_settings_payload(payload: dict[str, object]) -> AppSettings:
    decrease_raw = payload.get("decreaseThresholdPct")
    increase_raw = payload.get("increaseThresholdPct")
    if decrease_raw is None or increase_raw is None:
        raise ValueError("decreaseThresholdPct と increaseThresholdPct を指定してください。")
    try:
        decrease = float(decrease_raw)
        increase = float(increase_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("閾値は数値で指定してください。") from exc
    return AppSettings(
        decrease_threshold_pct=clamp_threshold(decrease),
        increase_threshold_pct=clamp_threshold(increase),
    )
