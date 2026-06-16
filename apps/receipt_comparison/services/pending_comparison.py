from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import date

from django.http import HttpRequest

from apps.receipt_comparison.domain.comparison import ComparisonRow

PENDING_SESSION_KEY = "receipt_comparison_pending"


@dataclass
class DisplayRow:
    id: int | None
    pending_index: int | None
    receipt_flag: int
    mari_item_cd: str
    mari_date: str
    mari_qty: str
    delivery_place: str
    supplier_item_cd: str
    supplier_delivery_month_day: str
    supplier_qty: str
    supplier_cancel_qty: str
    supplier_name: str
    remarks: str

    @property
    def is_pending(self) -> bool:
        return self.pending_index is not None

    @property
    def flag_label(self) -> str:
        from apps.receipt_comparison.models import ReceiptFlag

        return ReceiptFlag(self.receipt_flag).label


def comparison_row_to_dict(row: ComparisonRow) -> dict[str, object]:
    return {
        "existing_id": row.existing_id,
        "receipt_flag": row.receipt_flag,
        "mari_item_cd": row.mari_item_cd,
        "mari_date": row.mari_date,
        "mari_qty": row.mari_qty,
        "delivery_place": row.delivery_place,
        "supplier_item_cd": row.supplier_item_cd,
        "supplier_delivery_month_day": row.supplier_delivery_month_day,
        "supplier_qty": row.supplier_qty,
        "supplier_cancel_qty": row.supplier_cancel_qty,
        "supplier_name": row.supplier_name,
        "remarks": row.remarks,
    }


def comparison_row_from_dict(data: dict[str, object]) -> ComparisonRow:
    return ComparisonRow(
        existing_id=data.get("existing_id"),
        receipt_flag=int(data["receipt_flag"]),
        mari_item_cd=str(data.get("mari_item_cd") or ""),
        mari_date=str(data.get("mari_date") or ""),
        mari_qty=str(data.get("mari_qty") or ""),
        delivery_place=str(data.get("delivery_place") or ""),
        supplier_item_cd=str(data.get("supplier_item_cd") or ""),
        supplier_delivery_month_day=str(data.get("supplier_delivery_month_day") or ""),
        supplier_qty=str(data.get("supplier_qty") or ""),
        supplier_cancel_qty=str(data.get("supplier_cancel_qty") or ""),
        supplier_name=str(data.get("supplier_name") or ""),
        remarks=str(data.get("remarks") or ""),
    )


def pending_scope(
    comparison_type: str,
    supplier_id: int,
    start_date: date,
    end_date: date,
) -> dict[str, str | int]:
    return {
        "comparison_type": comparison_type,
        "supplier_id": supplier_id,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }


def pending_matches(
    pending: dict[str, object] | None,
    comparison_type: str,
    supplier_id: int,
    start_date: date,
    end_date: date,
) -> bool:
    if pending is None:
        return False
    scope = pending_scope(comparison_type, supplier_id, start_date, end_date)
    return all(pending.get(key) == value for key, value in scope.items())


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


def pending_display_rows(pending: dict[str, object]) -> list[DisplayRow]:
    rows: list[DisplayRow] = []
    for index, row_data in enumerate(pending.get("rows") or []):
        if not isinstance(row_data, dict):
            continue
        rows.append(
            DisplayRow(
                id=None,
                pending_index=index,
                receipt_flag=int(row_data.get("receipt_flag", 0)),
                mari_item_cd=str(row_data.get("mari_item_cd") or ""),
                mari_date=str(row_data.get("mari_date") or ""),
                mari_qty=str(row_data.get("mari_qty") or ""),
                delivery_place=str(row_data.get("delivery_place") or ""),
                supplier_item_cd=str(row_data.get("supplier_item_cd") or ""),
                supplier_delivery_month_day=str(row_data.get("supplier_delivery_month_day") or ""),
                supplier_qty=str(row_data.get("supplier_qty") or ""),
                supplier_cancel_qty=str(row_data.get("supplier_cancel_qty") or ""),
                supplier_name=str(row_data.get("supplier_name") or ""),
                remarks=str(row_data.get("remarks") or ""),
            )
        )
    return rows


def saved_display_rows(rows: list[object]) -> list[DisplayRow]:
    return [
        DisplayRow(
            id=row.id,
            pending_index=None,
            receipt_flag=row.receipt_flag,
            mari_item_cd=row.mari_item_cd,
            mari_date=row.mari_date,
            mari_qty=row.mari_qty,
            delivery_place=row.delivery_place,
            supplier_item_cd=row.supplier_item_cd,
            supplier_delivery_month_day=row.supplier_delivery_month_day,
            supplier_qty=row.supplier_qty,
            supplier_cancel_qty=row.supplier_cancel_qty,
            supplier_name=row.supplier_name,
            remarks=row.remarks,
        )
        for row in rows
    ]


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
