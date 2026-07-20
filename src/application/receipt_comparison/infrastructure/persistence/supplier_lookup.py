from __future__ import annotations

from application.receipt_comparison.infrastructure.persistence.supplier_repository import (
    mari_vendor_codes_for_supplier,
    vendor_match_codes_for_supplier,
)
from application.receipt_comparison.models import FinishedProductReceiptSupplier, SuppliedPartsReceiptSupplier


def receiving_places_for_supplier(supplier: object) -> list[str]:
    return list(supplier.receiving_settings.values_list("delivery_place", flat=True))


def subcontractor_codes(supplier: object) -> list[str]:
    if isinstance(supplier, FinishedProductReceiptSupplier):
        return []
    return vendor_match_codes_for_supplier(supplier)


class DjangoSupplierLookup:
    def receiving_places(self, supplier: object) -> list[str]:
        return receiving_places_for_supplier(supplier)

    def subcontractor_codes(self, supplier: object) -> list[str]:
        return subcontractor_codes(supplier)
