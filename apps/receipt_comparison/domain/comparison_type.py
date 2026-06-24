from __future__ import annotations


FINISHED_PRODUCT = "finished_product"
SUPPLIED_PARTS = "supplied_parts"

COMPARISON_TYPE_SLUGS: dict[str, str] = {
    "finished-product": FINISHED_PRODUCT,
    "supplied-parts": SUPPLIED_PARTS,
}
COMPARISON_SLUG_BY_TYPE: dict[str, str] = {value: slug for slug, value in COMPARISON_TYPE_SLUGS.items()}
COMPARISON_TYPE_PAGE_LABELS: dict[str, str] = {
    FINISHED_PRODUCT: "完成品",
    SUPPLIED_PARTS: "支給品",
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
    return comparison_type == FINISHED_PRODUCT
