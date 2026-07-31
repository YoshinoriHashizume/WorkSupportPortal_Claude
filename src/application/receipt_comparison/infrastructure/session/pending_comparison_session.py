from __future__ import annotations

import base64
from datetime import date

from django.http import HttpRequest

from application.receipt_comparison.domain.value_objects.comparison import ComparisonRow
from application.receipt_comparison.domain.value_objects.comparison_display import (
    comparison_row_from_dict,
    comparison_row_to_dict,
    pending_scope,
)

PENDING_SESSION_KEY = "receipt_comparison_pending"


def store_pending_comparison(
    request: HttpRequest,
    *,
    comparison_type: str,
    supplier_id: int,
    start_date: date,
    end_date: date,
    file_name: str,
    file_content: bytes,
    rows: list[ComparisonRow],
) -> None:
    request.session[PENDING_SESSION_KEY] = {
        **pending_scope(comparison_type, supplier_id, start_date, end_date),
        "file_name": file_name,
        "file_content_b64": base64.b64encode(file_content).decode("ascii"),
        "rows": [comparison_row_to_dict(row) for row in rows],
    }
    request.session.modified = True


def get_pending_comparison(request: HttpRequest) -> dict[str, object] | None:
    pending = request.session.get(PENDING_SESSION_KEY)
    if not isinstance(pending, dict):
        return None
    return pending


def clear_pending_comparison(request: HttpRequest) -> None:
    if PENDING_SESSION_KEY in request.session:
        del request.session[PENDING_SESSION_KEY]
        request.session.modified = True


def pending_rows_for_register(request: HttpRequest, pending: dict[str, object]) -> list[ComparisonRow]:
    rows: list[ComparisonRow] = []
    for index, row_data in enumerate(pending.get("rows") or []):
        if not isinstance(row_data, dict):
            continue
        row = comparison_row_from_dict(row_data)
        row.receipt_flag = int(request.POST.get(f"receipt_flag_pending_{index}", row.receipt_flag))
        row.remarks = request.POST.get(f"remarks_pending_{index}", row.remarks)
        rows.append(row)
    return rows
