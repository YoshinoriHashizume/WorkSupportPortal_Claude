from __future__ import annotations

import pytest

from apps.receipt_comparison.models import SuppliedPartsReceiptSupplier, SuppliedPartsSubcontractor
from apps.receipt_comparison.infrastructure.persistence.supplier_repository import (
    mari_vendor_codes_for_supplier,
    vendor_match_codes_for_supplier,
)


@pytest.mark.django_db
def test_vendor_match_codes_for_supplier_uses_subcontractor_vendor_codes():
    supplier = SuppliedPartsReceiptSupplier.objects.create(customer_code="191", name="テスト")
    SuppliedPartsSubcontractor.objects.create(supplier=supplier, vendor_code="9990")
    SuppliedPartsSubcontractor.objects.create(supplier=supplier, vendor_code="106")

    assert vendor_match_codes_for_supplier(supplier) == ["106", "9990"]


@pytest.mark.django_db
def test_mari_vendor_codes_for_supplier_returns_empty_without_subcontractors():
    supplier = SuppliedPartsReceiptSupplier.objects.create(customer_code="191", name="テスト")

    assert mari_vendor_codes_for_supplier(supplier) == []
