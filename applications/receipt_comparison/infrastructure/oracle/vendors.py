from __future__ import annotations

from applications.gonenkukumi.infrastructure.oracle.client import OracleNotConfiguredError, OracleQueryError

from .client import list_vendors

VENDOR_CODE_DIGIT_LENGTH = 4

__all__ = [
    "VENDOR_CODE_DIGIT_LENGTH",
    "list_receipt_vendors",
    "lookup_receipt_vendor_name",
]


def list_receipt_vendors(keyword: str = "") -> list[dict[str, str]]:
    return list_vendors(keyword=keyword)


def lookup_receipt_vendor_name(vendor_code: str) -> str:
    code = str(vendor_code or "").strip()
    if not code:
        return ""
    for row in list_receipt_vendors():
        if row.get("vendorCode") == code:
            return str(row.get("vendorName") or "").strip()
    return ""
