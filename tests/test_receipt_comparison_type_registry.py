from __future__ import annotations

import pytest

from apps.receipt_comparison.models import ReceiptComparisonType
from apps.receipt_comparison.type_registry import (
    settings_exclusion_label,
    settings_target_label,
)


@pytest.mark.parametrize(
    ("comparison_type", "expected"),
    [
        (ReceiptComparisonType.FINISHED_PRODUCT, "受入/納品場所"),
        (ReceiptComparisonType.SUPPLIED_PARTS, "品番"),
    ],
)
def test_settings_target_label_by_comparison_type(comparison_type, expected):
    assert settings_target_label(comparison_type) == expected


@pytest.mark.parametrize(
    ("comparison_type", "expected"),
    [
        (ReceiptComparisonType.FINISHED_PRODUCT, "設定した受入/納品場所を除外する"),
        (ReceiptComparisonType.SUPPLIED_PARTS, "設定した品番を除外する"),
    ],
)
def test_settings_exclusion_label_by_comparison_type(comparison_type, expected):
    assert settings_exclusion_label(comparison_type) == expected
