from __future__ import annotations

from enum import StrEnum


class ReceiptComparisonType(StrEnum):
    """検収書比較の区分（完成品 / 支給品）。Django 非依存の正。"""

    FINISHED_PRODUCT = "finished_product"
    SUPPLIED_PARTS = "supplied_parts"

    @property
    def label(self) -> str:
        return COMPARISON_TYPE_PAGE_LABELS[self.value]


FINISHED_PRODUCT = ReceiptComparisonType.FINISHED_PRODUCT
SUPPLIED_PARTS = ReceiptComparisonType.SUPPLIED_PARTS

COMPARISON_TYPE_SLUGS: dict[str, str] = {
    "finished-product": ReceiptComparisonType.FINISHED_PRODUCT.value,
    "supplied-parts": ReceiptComparisonType.SUPPLIED_PARTS.value,
}
COMPARISON_SLUG_BY_TYPE: dict[str, str] = {value: slug for slug, value in COMPARISON_TYPE_SLUGS.items()}
COMPARISON_TYPE_PAGE_LABELS: dict[str, str] = {
    ReceiptComparisonType.FINISHED_PRODUCT.value: "完成品",
    ReceiptComparisonType.SUPPLIED_PARTS.value: "支給品",
}


class UnknownComparisonTypeError(LookupError):
    pass


def comparison_type_from_slug(slug: str) -> str:
    comparison_type = COMPARISON_TYPE_SLUGS.get(slug)
    if comparison_type is None:
        raise UnknownComparisonTypeError(slug)
    return comparison_type


def comparison_type_page_label(comparison_type: str) -> str:
    return COMPARISON_TYPE_PAGE_LABELS[comparison_type]


def comparison_type_slug(comparison_type: str) -> str:
    return COMPARISON_SLUG_BY_TYPE[comparison_type]


def is_finished_product(comparison_type: str) -> bool:
    return comparison_type == ReceiptComparisonType.FINISHED_PRODUCT
