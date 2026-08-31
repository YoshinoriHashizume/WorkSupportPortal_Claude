from __future__ import annotations

from application.receipt_comparison.domain.value_objects.comparison_type import (
    FINISHED_PRODUCT,
    SUPPLIED_PARTS,
    ReceiptComparisonType,
    comparison_type_from_slug,
    is_finished_product,
)
from application.receipt_comparison.domain.value_objects.receipt_flag import ReceiptFlag
from application.receipt_comparison.models import (
    ReceiptComparisonType as OrmComparisonType,
    ReceiptFlag as OrmReceiptFlag,
)


def test_domain_receipt_flag_labels_and_choices():
    assert ReceiptFlag.NG.label == "×"
    assert ReceiptFlag.OK.label == "〇"
    assert ReceiptFlag.PENDING.label == "△"
    assert ReceiptFlag(1).label == "〇"
    assert ReceiptFlag.choices() == [(0, "×"), (1, "〇"), (2, "△")]


def test_domain_comparison_type_values_match_orm():
    assert ReceiptComparisonType.FINISHED_PRODUCT == OrmComparisonType.FINISHED_PRODUCT
    assert ReceiptComparisonType.SUPPLIED_PARTS == OrmComparisonType.SUPPLIED_PARTS
    assert ReceiptComparisonType.FINISHED_PRODUCT.label == "完成品"
    assert FINISHED_PRODUCT == "finished_product"
    assert SUPPLIED_PARTS == "supplied_parts"
    assert is_finished_product(FINISHED_PRODUCT) is True
    assert comparison_type_from_slug("supplied-parts") == SUPPLIED_PARTS


def test_orm_receipt_flag_values_match_domain():
    assert OrmReceiptFlag.NG == ReceiptFlag.NG
    assert OrmReceiptFlag.OK == ReceiptFlag.OK
    assert OrmReceiptFlag.PENDING == ReceiptFlag.PENDING
    assert OrmReceiptFlag.NG.label == ReceiptFlag.NG.label
