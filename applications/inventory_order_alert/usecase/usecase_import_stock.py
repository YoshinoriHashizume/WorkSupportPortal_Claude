from __future__ import annotations

from collections.abc import Callable
from typing import Any

from applications.inventory_order_alert.domain.slims_stock import decode_slims_csv_bytes

StockImporter = Callable[..., Any]


class ImportStockUsecase:
    def __init__(self, import_stock: StockImporter) -> None:
        self._import_stock = import_stock

    def execute(self, raw_bytes: bytes, *, user: object | None = None, file_name: str = "") -> Any:
        return self._import_stock(
            decode_slims_csv_bytes(raw_bytes),
            user=user,
            file_name=file_name,
        )
