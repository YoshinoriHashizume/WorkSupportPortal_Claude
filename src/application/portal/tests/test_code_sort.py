from __future__ import annotations

from application.portal.domain.value_objects.code_sort import numeric_code_sort_key


def test_numeric_code_sort_key_orders_digits_numerically():
    codes = ["100", "2", "10", "A01"]
    assert sorted(codes, key=numeric_code_sort_key) == ["2", "10", "100", "A01"]
