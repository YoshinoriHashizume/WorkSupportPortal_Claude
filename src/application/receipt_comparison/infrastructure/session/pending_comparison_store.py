from __future__ import annotations

from datetime import date

from django.http import HttpRequest

from application.receipt_comparison.domain.value_objects.comparison import ComparisonRow
from application.receipt_comparison.domain.value_objects.comparison_display import pending_matches
from application.receipt_comparison.infrastructure.session import pending_comparison_session as session


class HttpPendingComparisonStore:
    def __init__(self, request: HttpRequest) -> None:
        self._request = request

    def get(self) -> dict[str, object] | None:
        return session.get_pending_comparison(self._request)

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
    ) -> None:
        session.store_pending_comparison(
            self._request,
            comparison_type=comparison_type,
            supplier_id=supplier_id,
            start_date=start_date,
            end_date=end_date,
            file_name=file_name,
            file_content=file_content,
            rows=rows,
        )

    def clear(self) -> None:
        session.clear_pending_comparison(self._request)

    def rows_for_register(self, pending: dict[str, object], post_values: dict[str, str]) -> list[ComparisonRow]:
        rows: list[ComparisonRow] = []
        from application.receipt_comparison.domain.value_objects.comparison_display import comparison_row_from_dict

        for index, row_data in enumerate(pending.get("rows") or []):
            if not isinstance(row_data, dict):
                continue
            row = comparison_row_from_dict(row_data)
            row.receipt_flag = int(post_values.get(f"receipt_flag_pending_{index}", row.receipt_flag))
            row.remarks = post_values.get(f"remarks_pending_{index}", row.remarks)
            rows.append(row)
        return rows


def pending_matches_scope(
    pending: dict[str, object] | None,
    comparison_type: str,
    supplier_id: int,
    start_date: date,
    end_date: date,
) -> bool:
    return pending_matches(pending, comparison_type, supplier_id, start_date, end_date)
