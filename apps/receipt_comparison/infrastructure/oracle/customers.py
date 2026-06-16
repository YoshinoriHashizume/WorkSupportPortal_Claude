from __future__ import annotations

from apps.gonenkukumi.infrastructure.oracle.customers import (
    CUSTOMER_CODE_DIGIT_LENGTH_3,
    CUSTOMER_CODE_DIGIT_LENGTH_4,
    list_customers_3,
    list_customers_4,
    list_customers_by_digit_length,
    lookup_customer_name,
)

__all__ = [
    "CUSTOMER_CODE_DIGIT_LENGTH_3",
    "CUSTOMER_CODE_DIGIT_LENGTH_4",
    "list_customers_3",
    "list_customers_4",
    "list_customers_by_digit_length",
    "list_receipt_customers",
    "lookup_receipt_customer_name",
]


def list_receipt_customers(*, digit_length: int, keyword: str = "") -> list[dict[str, str]]:
    return list_customers_by_digit_length(digit_length=digit_length, keyword=keyword)


lookup_receipt_customer_name = lookup_customer_name
