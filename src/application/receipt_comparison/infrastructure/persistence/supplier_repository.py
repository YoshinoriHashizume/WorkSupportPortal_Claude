from __future__ import annotations

from application.receipt_comparison.models import SuppliedPartsReceiptSupplier


def vendor_codes_for_supplier(supplier: SuppliedPartsReceiptSupplier) -> list[str]:
    """旧 SUBCONTRACTOR_INFO の VENDOR_CODE 一覧。MARI取得・TXT 2列目照合に使用。"""
    return sorted(
        {
            str(code).strip()
            for code in supplier.subcontractors.values_list("vendor_code", flat=True)
            if str(code).strip()
        }
    )


def vendor_match_codes_for_supplier(supplier: SuppliedPartsReceiptSupplier) -> list[str]:
    return vendor_codes_for_supplier(supplier)


def mari_vendor_codes_for_supplier(supplier: SuppliedPartsReceiptSupplier) -> list[str]:
    return vendor_codes_for_supplier(supplier)
