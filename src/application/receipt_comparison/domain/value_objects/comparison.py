from __future__ import annotations

from datetime import date, datetime

from application.receipt_comparison.domain.entities.comparison_row import ComparisonRow
from application.receipt_comparison.domain.value_objects.receipt_flag import ReceiptFlag

from .file_parser import normalize_supplied_parts_item_cd
from .records import MariReceiptRow, ReceiptFileRow



def normalize_item_cd(value: object) -> str:
    return str(value or "").strip().replace("-", "")


def normalize_compare_item_cd(value: object, *, supplied_parts: bool) -> str:
    item_cd = normalize_item_cd(value)
    if supplied_parts:
        return normalize_supplied_parts_item_cd(item_cd)
    return item_cd


def normalize_qty(value: object) -> str:
    """数量の表示・突合用正規化。Oracle の NULL は ``0`` として扱う。"""
    if value is None:
        return "0"
    raw = str(value).strip()
    if not raw:
        return ""
    try:
        number = float(raw)
    except ValueError:
        return raw
    return str(int(number)) if number.is_integer() else raw


def month_day(value: object) -> str:
    if isinstance(value, date | datetime):
        return value.strftime("%m%d")
    raw = str(value or "").strip()
    if not raw:
        return ""
    for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:10], fmt).strftime("%m%d")
        except ValueError:
            pass
    digits = "".join(ch for ch in raw if ch.isdigit())
    return digits[-4:] if len(digits) >= 4 else raw


def compare_receipts(
    mari_rows: list[MariReceiptRow],
    receipt_rows: list[ReceiptFileRow],
    existing_rows: list[ComparisonRow] | None = None,
    *,
    supplied_parts: bool = False,
) -> list[ComparisonRow]:
    results = [
        ComparisonRow(
            receipt_flag=ReceiptFlag.NG,
            mari_item_cd=row.item_cd,
            mari_date=row.ship_date,
            mari_qty=normalize_qty(row.ship_qty),
            delivery_place=row.delivery_place,
        )
        for row in mari_rows
    ]

    apply_existing_rows(results, existing_rows or [], supplied_parts=supplied_parts)

    remaining_receipts = list(receipt_rows)
    for result in results:
        match_index = find_receipt_match(result, remaining_receipts, supplied_parts=supplied_parts)
        if match_index is None:
            if result.receipt_flag not in {ReceiptFlag.OK, ReceiptFlag.PENDING}:
                result.receipt_flag = ReceiptFlag.NG
            continue
        receipt = remaining_receipts.pop(match_index)
        result.receipt_flag = ReceiptFlag.OK
        result.supplier_item_cd = receipt.item_cd
        result.supplier_delivery_month_day = receipt.delivery_month_day
        result.supplier_qty = normalize_qty(receipt.qty)
        result.supplier_cancel_qty = receipt.cancel_qty
        result.supplier_name = receipt.supplier_name

    for receipt in remaining_receipts:
        results.append(
            ComparisonRow(
                receipt_flag=ReceiptFlag.NG,
                supplier_item_cd=receipt.item_cd,
                supplier_delivery_month_day=receipt.delivery_month_day,
                supplier_qty=normalize_qty(receipt.qty),
                supplier_cancel_qty=receipt.cancel_qty,
                supplier_name=receipt.supplier_name,
            )
        )
    return results


def apply_existing_rows(
    results: list[ComparisonRow],
    existing_rows: list[ComparisonRow],
    *,
    supplied_parts: bool = False,
) -> None:
    for existing in existing_rows:
        match = find_mari_match(results, existing, supplied_parts=supplied_parts)
        if match is None:
            results.append(existing)
            continue
        match.existing_id = existing.existing_id
        match.receipt_flag = existing.receipt_flag
        match.supplier_item_cd = existing.supplier_item_cd
        match.supplier_delivery_month_day = existing.supplier_delivery_month_day
        match.supplier_qty = normalize_qty(existing.supplier_qty)
        match.supplier_cancel_qty = existing.supplier_cancel_qty
        match.supplier_name = existing.supplier_name
        match.remarks = existing.remarks


def find_mari_match(
    results: list[ComparisonRow],
    existing: ComparisonRow,
    *,
    supplied_parts: bool = False,
) -> ComparisonRow | None:
    for result in results:
        if normalize_compare_item_cd(result.mari_item_cd, supplied_parts=supplied_parts) != normalize_compare_item_cd(
            existing.mari_item_cd,
            supplied_parts=supplied_parts,
        ):
            continue
        if month_day(result.mari_date) != month_day(existing.mari_date):
            continue
        if normalize_qty(result.mari_qty) != normalize_qty(existing.mari_qty):
            continue
        return result
    return None


def find_receipt_match(
    result: ComparisonRow,
    receipt_rows: list[ReceiptFileRow],
    *,
    supplied_parts: bool = False,
) -> int | None:
    for index, receipt in enumerate(receipt_rows):
        if normalize_compare_item_cd(result.mari_item_cd, supplied_parts=supplied_parts) != normalize_compare_item_cd(
            receipt.item_cd,
            supplied_parts=supplied_parts,
        ):
            continue
        if month_day(result.mari_date) != receipt.delivery_month_day:
            continue
        if normalize_qty(result.mari_qty) != normalize_qty(receipt.qty):
            continue
        return index
    return None
