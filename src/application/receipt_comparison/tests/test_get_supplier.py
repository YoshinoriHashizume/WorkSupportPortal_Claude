from __future__ import annotations

import pytest

from application.receipt_comparison.domain.value_objects.comparison_type import FINISHED_PRODUCT
from application.receipt_comparison.infrastructure.persistence.model_registry import get_supplier
from application.receipt_comparison.models import FinishedProductReceiptSupplier


@pytest.mark.django_db
def test_get_supplier_returns_none_when_missing():
    assert get_supplier(FINISHED_PRODUCT, 999999) is None
    assert get_supplier(FINISHED_PRODUCT, "not-an-id") is None


@pytest.mark.django_db
def test_get_supplier_returns_instance():
    supplier = FinishedProductReceiptSupplier.objects.create(
        name="テスト",
        customer_code="1001",
    )
    found = get_supplier(FINISHED_PRODUCT, supplier.id)
    assert found is not None
    assert found.id == supplier.id
