from __future__ import annotations

from apps.receipt_comparison.domain.comparison_type import FINISHED_PRODUCT, SUPPLIED_PARTS


def settings_target_label(comparison_type: str) -> str:
    if comparison_type == SUPPLIED_PARTS:
        return "品番"
    return "受入/納品場所"


def settings_exclusion_label(comparison_type: str) -> str:
    return f"設定した{settings_target_label(comparison_type)}を除外する"


def customer_digit_length(comparison_type: str) -> int:
    if comparison_type in {FINISHED_PRODUCT, SUPPLIED_PARTS}:
        return 3
    raise ValueError("正しい比較区分が読み込まれませんでした。")
