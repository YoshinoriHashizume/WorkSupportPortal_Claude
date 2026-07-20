from __future__ import annotations


ROW_DECREASE_STRONG = "st-row-decrease-strong"
ROW_DECREASE_MILD = "st-row-decrease-mild"
ROW_INCREASE_STRONG = "st-row-increase-strong"
ROW_NEUTRAL = "st-row-neutral"


def alert_row_class(
    change_rate_pct: float | None,
    *,
    decrease_threshold_pct: float,
    increase_threshold_pct: float,
) -> str:
    if change_rate_pct is None:
        return ROW_NEUTRAL
    if change_rate_pct < 0:
        if change_rate_pct <= -decrease_threshold_pct:
            return ROW_DECREASE_STRONG
        return ROW_DECREASE_MILD
    if change_rate_pct > 0:
        if change_rate_pct >= increase_threshold_pct:
            return ROW_INCREASE_STRONG
        return ROW_NEUTRAL
    return ROW_NEUTRAL


def build_alert_rule_rows(
    *,
    decrease_threshold_pct: float,
    increase_threshold_pct: float,
) -> list[dict[str, str]]:
    return [
        {
            "condition": f"変動率 ≤ −{decrease_threshold_pct:g}%",
            "color": "薄い赤",
            "class_key": "decrease-strong",
        },
        {
            "condition": f"−{decrease_threshold_pct:g}% ＜ 変動率 ＜ 0%",
            "color": "薄い黄",
            "class_key": "decrease-mild",
        },
        {
            "condition": f"変動率 ≥ +{increase_threshold_pct:g}%",
            "color": "薄い緑",
            "class_key": "increase-strong",
        },
        {
            "condition": f"0% ≤ 変動率 ＜ +{increase_threshold_pct:g}%",
            "color": "白",
            "class_key": "neutral",
        },
    ]
