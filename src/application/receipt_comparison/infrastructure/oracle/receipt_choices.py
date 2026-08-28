from __future__ import annotations

from application.sales.domain.value_objects.errors import OracleNotConfiguredError, OracleQueryError
from application.receipt_comparison.domain.value_objects.comparison_urls import is_fixed_digit_code
from application.receipt_comparison.infrastructure.oracle.customers import list_receipt_customers, lookup_receipt_customer_name
from application.receipt_comparison.infrastructure.oracle.vendors import VENDOR_CODE_DIGIT_LENGTH, list_receipt_vendors, lookup_receipt_vendor_name
from application.receipt_comparison.models import ReceiptComparisonType
from application.receipt_comparison.domain.value_objects.settings_labels import customer_digit_length


def list_customer_choices(comparison_type: str) -> tuple[list[dict[str, str]], str]:
    errors: list[str] = []
    digit_length = customer_digit_length(comparison_type)
    try:
        customers = [
            row
            for row in list_receipt_customers(digit_length=digit_length)
            if is_fixed_digit_code(row["custCode"], digit_length)
        ]
    except (OracleNotConfiguredError, OracleQueryError) as exc:
        customers = []
        errors.append(str(exc))
    return customers, " / ".join(errors)


def list_vendor_choices() -> tuple[list[dict[str, str]], str]:
    errors: list[str] = []
    try:
        vendors = [
            row
            for row in list_receipt_vendors()
            if is_fixed_digit_code(row.get("vendorCode"), VENDOR_CODE_DIGIT_LENGTH)
        ]
    except (OracleNotConfiguredError, OracleQueryError) as exc:
        vendors = []
        errors.append(str(exc))
    return vendors, " / ".join(errors)


def lookup_customer_name(customer_code: str, *, fallback: object = "") -> str:
    if not customer_code:
        return str(fallback or "").strip()
    try:
        name = lookup_receipt_customer_name(customer_code)
    except (OracleNotConfiguredError, OracleQueryError):
        name = None
    if name:
        return name
    return str(fallback or "").strip() or customer_code


def lookup_vendor_name(vendor_code: str) -> str:
    return lookup_receipt_vendor_name(vendor_code)


class OracleReceiptChoiceGateway:
    def list_customers(self, digit_length: int) -> tuple[list[dict[str, str]], str]:
        try:
            customers = [
                row
                for row in list_receipt_customers(digit_length=digit_length)
                if is_fixed_digit_code(row["custCode"], digit_length)
            ]
            return customers, ""
        except (OracleNotConfiguredError, OracleQueryError) as exc:
            return [], str(exc)

    def list_vendors(self) -> tuple[list[dict[str, str]], str]:
        return list_vendor_choices()

    def lookup_customer_name(self, customer_code: str) -> str:
        return lookup_customer_name(customer_code)

    def lookup_vendor_name(self, vendor_code: str) -> str:
        return lookup_vendor_name(vendor_code)
