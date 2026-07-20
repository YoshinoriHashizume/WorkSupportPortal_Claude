from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from application.receipt_comparison.domain.value_objects.comparison_display import DisplayRow
from application.receipt_comparison.domain.value_objects.constants import RESULT_COLUMNS
from application.receipt_comparison.domain.repositories.ports import PendingComparisonStore
from application.receipt_comparison.use_cases.comparison_page import ComparisonPage, comparison_export_filename


@dataclass(frozen=True)
class ExportCsvOutcome:
    filename: str
    columns: list[str]
    rows: list[list[str]]


class ExportCsv:
    def __init__(self, comparison_page_usecase: ComparisonPage) -> None:
        self._comparison_page_usecase = comparison_page_usecase

    def execute(
        self,
        pending_store: PendingComparisonStore,
        *,
        comparison_type: str,
        supplier: object,
        start_date: date,
        end_date: date,
        sort_key: str,
        sort_direction: str,
    ) -> ExportCsvOutcome:
        rows, _has_pending = self._comparison_page_usecase.rows_for_page(
            pending_store,
            comparison_type,
            supplier,
            start_date,
            end_date,
            sort_key,
            sort_direction,
        )
        return ExportCsvOutcome(
            filename=comparison_export_filename(comparison_type),
            columns=list(RESULT_COLUMNS),
            rows=[self._row_values(row) for row in rows],
        )

    def _row_values(self, row: DisplayRow) -> list[str]:
        return [
            row.flag_label,
            row.mari_item_cd,
            row.mari_date,
            row.mari_qty,
            row.delivery_place,
            row.supplier_item_cd,
            row.supplier_delivery_month_day,
            row.supplier_qty,
            row.supplier_cancel_qty,
            row.supplier_name,
            row.remarks,
        ]
