from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class StockImportInfo:
    imported_at: datetime
    row_count: int
    file_name: str
    stock_as_of_date: date
    stock_as_of_label: str
    summary_row_count: int = 0
    aggregation_error: str = ""
    confirmation_reset_count: int = 0

    @property
    def has_data(self) -> bool:
        return self.row_count > 0


@dataclass(frozen=True)
class SummaryLoadResult:
    rows: list[dict[str, object]]
    stock_info: StockImportInfo | None
    as_of_date: date | None
    aggregation_error: str
    total_count: int
    critical_count: int
    warning_count: int

    @property
    def has_summary(self) -> bool:
        return bool(self.rows) or bool(self.aggregation_error)


@dataclass(frozen=True)
class EditableSummarySnapshot:
    id: int
    as_of_date: date
    rows: list[dict[str, object]]
