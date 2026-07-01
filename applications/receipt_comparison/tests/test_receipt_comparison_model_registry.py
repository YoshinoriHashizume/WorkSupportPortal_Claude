from __future__ import annotations

import pytest

from applications.receipt_comparison.domain.comparison_type import FINISHED_PRODUCT, SUPPLIED_PARTS, is_finished_product
from applications.receipt_comparison.domain.settings_labels import (
    customer_digit_length,
    settings_exclusion_label,
    settings_target_label,
)
from applications.receipt_comparison.infrastructure.persistence.model_registry import (
    comparison_result_model,
    supplier_model,
)
from applications.receipt_comparison.models import (
    FinishedProductComparisonResult,
    FinishedProductReceiptSupplier,
    ReceiptComparisonType,
    SuppliedPartsComparisonResult,
    SuppliedPartsReceiptSupplier,
)


def test_model_registry_returns_split_models():
    assert supplier_model(ReceiptComparisonType.FINISHED_PRODUCT) is FinishedProductReceiptSupplier
    assert supplier_model(ReceiptComparisonType.SUPPLIED_PARTS) is SuppliedPartsReceiptSupplier
    assert comparison_result_model(ReceiptComparisonType.FINISHED_PRODUCT) is FinishedProductComparisonResult
    assert is_finished_product(ReceiptComparisonType.FINISHED_PRODUCT) is True


def test_customer_digit_length_for_both_types():
    assert customer_digit_length(FINISHED_PRODUCT) == 3
    assert customer_digit_length(SUPPLIED_PARTS) == 3


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
