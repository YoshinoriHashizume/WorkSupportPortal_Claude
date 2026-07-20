from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from application.receipt_comparison.domain.value_objects.comparison_display import (
    DisplayRow,
    pending_display_rows,
    pending_matches,
    saved_display_rows,
)
from application.receipt_comparison.domain.value_objects.comparison_sort import (
    comparison_sort_headers,
    resolve_sort_params,
    sort_display_rows,
)
from application.receipt_comparison.domain.value_objects.comparison_type import FINISHED_PRODUCT, comparison_type_page_label
from application.receipt_comparison.domain.value_objects.comparison_urls import comparison_query, is_results_panel_active

_TZ = ZoneInfo("Asia/Tokyo")


def _localtime(at: datetime | None = None) -> datetime:
    if at is None:
        return datetime.now(_TZ)
    if at.tzinfo:
        return at.astimezone(_TZ)
    return at.replace(tzinfo=_TZ).astimezone(_TZ)


@dataclass(frozen=True)
class ComparisonSortHeader:
    key: str
    label: str
    sort_direction: str
    is_sorted: bool
    href: str


@dataclass(frozen=True)
class ComparisonPageContext:
    type_slug: str
    comparison_type: str
    comparison_type_page_label: str
    suppliers: list[object]
    supplier: object | None
    start_date: date
    end_date: date
    rows: list[DisplayRow]
    has_pending: bool
    results_panel_active: bool
    receipt_file_accept: str
    show_cancel_qty: bool
    show_supplier_name: bool
    sort_key: str
    sort_direction: str
    sort_headers: list[ComparisonSortHeader]
    comparison_query: str


class ComparisonPage:
    def __init__(
        self,
        comparison_result_repository: ComparisonResultRepository,
        list_suppliers: ListSuppliers,
        *,
        comparison_base_path: str,
    ) -> None:
        self._comparison_result_repository = comparison_result_repository
        self._list_suppliers = list_suppliers
        self._comparison_base_path = comparison_base_path

    def rows_for_page(
        self,
        pending_store: PendingComparisonStore,
        comparison_type: str,
        supplier: object | None,
        start_date: date,
        end_date: date,
        sort_key: str,
        sort_direction: str,
    ) -> tuple[list[DisplayRow], bool]:
        if supplier is None:
            return [], False
        supplier_id = supplier.id
        pending = pending_store.get()
        if pending_matches(pending, comparison_type, supplier_id, start_date, end_date):
            rows = sort_display_rows(pending_display_rows(pending), sort_key, sort_direction)
            return rows, True
        saved_rows = self._comparison_result_repository.existing_rows_for_display(
            comparison_type,
            supplier_id,
            start_date,
            end_date,
        )
        rows = sort_display_rows(saved_display_rows(saved_rows), sort_key, sort_direction)
        return rows, False

    def build_context(
        self,
        *,
        type_slug: str,
        comparison_type: str,
        supplier: object | None,
        start_date: date,
        end_date: date,
        rows: list[DisplayRow],
        has_pending: bool,
        results_panel_active: bool,
        sort_key: str,
        sort_direction: str,
        display: int | None = None,
        compared: int | None = None,
    ) -> ComparisonPageContext:
        supplier_id = supplier.id if supplier else None
        return ComparisonPageContext(
            type_slug=type_slug,
            comparison_type=comparison_type,
            comparison_type_page_label=comparison_type_page_label(comparison_type),
            suppliers=self._list_suppliers(comparison_type),
            supplier=supplier,
            start_date=start_date,
            end_date=end_date,
            rows=rows,
            has_pending=has_pending,
            results_panel_active=results_panel_active,
            receipt_file_accept=".csv" if comparison_type == FINISHED_PRODUCT else ".txt",
            show_cancel_qty=comparison_type == FINISHED_PRODUCT,
            show_supplier_name=comparison_type != FINISHED_PRODUCT,
            sort_key=sort_key,
            sort_direction=sort_direction,
            sort_headers=self._sort_headers(
                comparison_type,
                supplier_id,
                start_date,
                end_date,
                sort_key,
                sort_direction,
                display=display,
                compared=compared,
            ),
            comparison_query=comparison_query(
                comparison_type,
                supplier_id,
                start_date,
                end_date,
            ),
        )

    def resolve_sort(
        self,
        *,
        sort_key: str | None,
        sort_direction: str | None,
        reset_to_default: bool,
    ) -> tuple[str, str]:
        return resolve_sort_params(
            sort_key=sort_key,
            sort_direction=sort_direction,
            reset_to_default=reset_to_default,
        )

    def is_results_panel_active(
        self,
        *,
        method: str,
        get_display: str | None,
        get_compared: str | None,
        post_action: str | None,
        supplier: object | None,
        has_pending: bool,
    ) -> bool:
        return is_results_panel_active(
            method=method,
            get_display=get_display,
            get_compared=get_compared,
            post_action=post_action,
            supplier_selected=supplier is not None,
            has_pending=has_pending,
        )

    def _sort_headers(
        self,
        comparison_type: str,
        supplier_id: int | None,
        start_date: date,
        end_date: date,
        sort_key: str,
        sort_direction: str,
        *,
        display: int | None = None,
        compared: int | None = None,
    ) -> list[ComparisonSortHeader]:
        headers: list[ComparisonSortHeader] = []
        for header in comparison_sort_headers(sort_key, sort_direction):
            query = comparison_query(
                comparison_type,
                supplier_id,
                start_date,
                end_date,
                display=display,
                compared=compared,
                sort_key=str(header["key"]),
                sort_direction=str(header["sort_direction"]),
            )
            headers.append(
                ComparisonSortHeader(
                    key=str(header["key"]),
                    label=str(header["label"]),
                    sort_direction=str(header["sort_direction"]),
                    is_sorted=bool(header["is_sorted"]),
                    href=f"{self._comparison_base_path}?{query}",
                )
            )
        return headers


def comparison_export_filename(comparison_type: str, at: datetime | None = None) -> str:
    label = comparison_type_page_label(comparison_type)
    moment = _localtime(at)
    return f"検収書比較結果({label})_{moment:%Y%m%d%H%M%S}.csv"
