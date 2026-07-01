from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from django.utils import timezone

from applications.inventory_order_alert.domain.dates import format_stock_as_of_label
from applications.inventory_order_alert.domain.summary import StockImportInfo


def row_to_storable(row: dict[str, object]) -> dict[str, object]:
    stored: dict[str, object] = {}
    for key, value in row.items():
        if isinstance(value, Decimal):
            stored[key] = str(value)
        elif isinstance(value, (date, datetime)):
            stored[key] = value.isoformat()
        else:
            stored[key] = value
    return stored


def row_from_stored(row: dict[str, object]) -> dict[str, object]:
    return dict(row)


def stock_info_from_import(import_record: object) -> StockImportInfo:
    stock_date = timezone.localdate(import_record.imported_at)
    return StockImportInfo(
        imported_at=import_record.imported_at,
        row_count=import_record.row_count,
        file_name=import_record.file_name,
        stock_as_of_date=stock_date,
        stock_as_of_label=format_stock_as_of_label(stock_date),
    )
