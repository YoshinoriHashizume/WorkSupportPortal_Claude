from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any, Protocol

from application.receipt_comparison.domain.value_objects.comparison import ComparisonRow


class PendingComparisonStore(Protocol):
    def get(self) -> dict[str, object] | None: ...

    def store(
        self,
        *,
        comparison_type: str,
        supplier_id: int,
        start_date: date,
        end_date: date,
        file_name: str,
        file_content: bytes,
        rows: list[ComparisonRow],
    ) -> None: ...

    def clear(self) -> None: ...

    def rows_for_register(self, pending: dict[str, object], post_values: dict[str, str]) -> list[ComparisonRow]: ...


class ComparisonResultRepository(Protocol):
    def existing_rows_for_display(
        self,
        comparison_type: str,
        supplier_id: int,
        start_date: date,
        end_date: date,
    ) -> list[Any]: ...

    def existing_rows_for_comparison(
        self,
        comparison_type: str,
        supplier_id: int,
        start_date: date,
        end_date: date,
    ) -> list[ComparisonRow]: ...

    def save_comparison_rows(
        self,
        comparison_type: str,
        supplier_id: int,
        file_import_id: int,
        rows: list[ComparisonRow],
        user_id: int,
    ) -> None: ...

    def update_existing_results_from_post(
        self,
        comparison_type: str,
        result_ids: list[str],
        post_values: dict[str, str],
        user_id: int,
    ) -> None: ...


class FileImportRepository(Protocol):
    def save_upload_file(
        self,
        comparison_type: str,
        supplier_id: int,
        original_name: str,
        content: bytes,
        receipt_date: date,
        user_id: int,
    ) -> int: ...


class MariRowGateway(Protocol):
    def fetch_mari_rows(
        self,
        *,
        comparison_type: str,
        supplier: object,
        start_date: date,
        end_date: date,
        receiving_places: list[str],
    ) -> list[Any]: ...


class SupplierLookup(Protocol):
    def receiving_places(self, supplier: object) -> list[str]: ...

    def subcontractor_codes(self, supplier: object) -> list[str]: ...


class ReceiptChoiceGateway(Protocol):
    def list_customers(self, digit_length: int) -> tuple[list[dict[str, str]], str]: ...

    def list_vendors(self) -> tuple[list[dict[str, str]], str]: ...

    def lookup_customer_name(self, customer_code: str) -> str: ...

    def lookup_vendor_name(self, vendor_code: str) -> str: ...


class SettingsRepository(Protocol):
    def handle_post(
        self,
        comparison_type: str,
        action: str | None,
        post_data: dict[str, str],
        user: object,
    ) -> list[object]: ...


ListSuppliers = Callable[[str], list[Any]]
ListSuppliersForSettings = Callable[[str], list[Any]]
