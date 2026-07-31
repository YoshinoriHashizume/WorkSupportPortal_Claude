from __future__ import annotations

from dataclasses import dataclass

DEFAULT_DECREASE_THRESHOLD_PCT = 20.0
DEFAULT_INCREASE_THRESHOLD_PCT = 20.0
MIN_THRESHOLD_PCT = 1.0
MAX_THRESHOLD_PCT = 100.0


@dataclass(frozen=True)
class AppSettings:
    decrease_threshold_pct: float
    increase_threshold_pct: float


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
