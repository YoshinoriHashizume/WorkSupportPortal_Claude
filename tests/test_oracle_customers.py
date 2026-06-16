from __future__ import annotations

import pytest

from apps.gonenkukumi.infrastructure.oracle.customers import (
    CUSTOMER_CODE_DIGIT_LENGTH_3,
    CUSTOMER_CODE_DIGIT_LENGTH_4,
    customer_code_digit_pattern,
    list_customers,
    list_customers_3,
    list_customers_4,
    list_customers_by_digit_length,
    lookup_customer_name,
    mock_customers_all,
)
from apps.receipt_comparison.infrastructure.oracle.customers import (
    list_receipt_customers,
    lookup_receipt_customer_name,
)


def test_customer_code_digit_pattern_uses_single_backslash():
    assert customer_code_digit_pattern(3) == "^\\d{3}$"
    assert customer_code_digit_pattern(4) == "^\\d{4}$"
    assert customer_code_digit_pattern(3).count("\\") == 1


def test_customer_code_digit_pattern_rejects_invalid_length():
    with pytest.raises(ValueError, match="桁数"):
        customer_code_digit_pattern(5)


def test_list_customers_by_digit_length_filters_mock_data(monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")

    customers_3 = list_customers_by_digit_length(digit_length=3)
    customers_4 = list_customers_by_digit_length(digit_length=4)

    assert all(len(row["custCode"]) == 3 for row in customers_3)
    assert all(len(row["custCode"]) == 4 for row in customers_4)
    assert any(row["custCode"] == "101" for row in customers_3)
    assert any(row["custCode"] == "9001" for row in customers_4)


def test_list_customers_named_wrappers_match_core(monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")

    assert list_customers() == list_customers_3()
    assert list_customers_4() == list_customers_by_digit_length(digit_length=4)


def test_lookup_customer_name_uses_shared_mock(monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")

    assert lookup_customer_name("101") == "サンプル得意先A"
    assert lookup_customer_name("9001") == "丸栄－豊橋"
    assert lookup_customer_name("9999") is None


def test_receipt_customers_module_delegates_to_shared_module(monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")

    assert list_receipt_customers(digit_length=3) == list_customers_by_digit_length(digit_length=3)
    assert list_receipt_customers(digit_length=4) == list_customers_by_digit_length(digit_length=4)
    assert lookup_receipt_customer_name("191") == lookup_customer_name("191")


def test_mock_customers_all_contains_both_digit_lengths():
    codes = {row["custCode"] for row in mock_customers_all()}

    assert "101" in codes
    assert "9001" in codes


def test_customer_digit_length_constants():
    assert CUSTOMER_CODE_DIGIT_LENGTH_3 == 3
    assert CUSTOMER_CODE_DIGIT_LENGTH_4 == 4
