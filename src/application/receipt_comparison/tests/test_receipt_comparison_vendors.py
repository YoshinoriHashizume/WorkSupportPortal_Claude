from __future__ import annotations

import pytest

from application.receipt_comparison.infrastructure.oracle.vendors import (
    VENDOR_CODE_DIGIT_LENGTH,
    list_receipt_vendors,
    lookup_receipt_vendor_name,
)
from application.receipt_comparison.infrastructure.oracle.receipt_choices import list_vendor_choices


def test_vendor_code_digit_length_is_four():
    assert VENDOR_CODE_DIGIT_LENGTH == 4


def test_list_receipt_vendors_returns_four_digit_codes(monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")

    vendors = list_receipt_vendors()

    assert all(len(row["vendorCode"]) == 4 for row in vendors)
    assert any(row["vendorCode"] == "9990" for row in vendors)


def test_lookup_receipt_vendor_name(monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")

    assert lookup_receipt_vendor_name("9990") == "サンプル仕入先E"
    assert lookup_receipt_vendor_name("UNKNOWN") == ""


def test_receipt_vendor_choices_filters_four_digit(monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")

    vendors, error = list_vendor_choices()

    assert not error
    assert all(len(row["vendorCode"]) == 4 for row in vendors)
