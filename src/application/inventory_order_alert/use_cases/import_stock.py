from __future__ import annotations

from application.inventory_order_alert.domain.repositories.ports import StockImporter
from application.inventory_order_alert.domain.value_objects.slims_stock import decode_slims_csv_bytes
from application.inventory_order_alert.domain.value_objects.summary import StockImportInfo


class ImportStock:
    def __init__(self, import_stock: StockImporter) -> None:
        self._import_stock = import_stock

    def execute(self, raw_bytes: bytes, *, user: object | None = None, file_name: str = "") -> StockImportInfo:
        return self._import_stock(
            decode_slims_csv_bytes(raw_bytes),
            user=user,
            file_name=file_name,
        )
