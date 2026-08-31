from __future__ import annotations

import pytest

from application.receipt_comparison.domain.value_objects.customer_vendor_link import (
    resolve_purchase_vendor_code,
    vendor_match_codes,
)
from application.receipt_comparison.infrastructure.oracle.linkage import (
    get_customer_vendor_link,
    mock_customer_vendor_link,
)


def test_resolve_purchase_vendor_code_prefers_cust_vend_cd():
    assert (
        resolve_purchase_vendor_code(
            "101",
            cust_vend_cd="9101",
            vendor_exists_for_customer_code=False,
        )
        == "9101"
    )


def test_resolve_purchase_vendor_code_uses_same_code_when_vendor_exists():
    assert (
        resolve_purchase_vendor_code(
            "137",
            cust_vend_cd="",
            vendor_exists_for_customer_code=True,
        )
        == "137"
    )


def test_resolve_purchase_vendor_code_returns_none_without_link():
    assert (
        resolve_purchase_vendor_code(
            "999",
            cust_vend_cd="",
            vendor_exists_for_customer_code=False,
        )
        is None
    )


def test_vendor_match_codes_collects_customer_purchase_and_extra_codes():
    assert vendor_match_codes("101", "9101", ["9200"]) == ["101", "9101", "9200"]


def test_mock_customer_vendor_link_returns_purchase_vendor_code():
    link = mock_customer_vendor_link("101")
    assert link["purchaseVendorCode"] == "9101"


@pytest.mark.django_db
def test_get_customer_vendor_link_uses_mock(monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")
    link = get_customer_vendor_link("137")
    assert link["customerCode"] == "137"
    assert link["purchaseVendorCode"] == "137"
