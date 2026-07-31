from __future__ import annotations

"""得意先マスタ参照の共有 ACL。"""

from application.gonenkukumi.infrastructure.oracle.customers import (
    CUSTOMER_CODE_DIGIT_LENGTH_3,
    CUSTOMER_CODE_DIGIT_LENGTH_4,
    customer_code_digit_pattern,
    list_customers_3,
    list_customers_4,
    list_customers_by_digit_length,
    lookup_customer_name,
)

__all__ = [
    "CUSTOMER_CODE_DIGIT_LENGTH_3",
    "CUSTOMER_CODE_DIGIT_LENGTH_4",
    "customer_code_digit_pattern",
    "list_customers_3",
    "list_customers_4",
    "list_customers_by_digit_length",
    "lookup_customer_name",
]
