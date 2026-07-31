from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SummaryLoadResult:
    rows: list[dict[str, object]]
    as_of_date: date | None
    aggregation_error: str
    total_count: int
    refreshed_at: date | None
