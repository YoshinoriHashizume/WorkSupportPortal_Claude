from __future__ import annotations

from application.inventory_order_alert.domain.repositories.ports import StockImporter
from application.inventory_order_alert.domain.value_objects.demand_forecast import attach_demand_forecast
from application.inventory_order_alert.domain.value_objects.slims_stock import decode_slims_csv_bytes
from application.inventory_order_alert.domain.value_objects.summary import StockImportInfo


class ImportStock:
    def __init__(self, import_stock: StockImporter) -> None:
        self._import_stock = import_stock

    def execute(self, raw_bytes: bytes, *, user: object | None = None, file_name: str = "") -> StockImportInfo:
        # 需要予測（V-220）は集計 → 付与 → 保存 の順で取込側が適用する（05 design §6.7）。
        return self._import_stock(
            decode_slims_csv_bytes(raw_bytes),
            user=user,
            file_name=file_name,
            enrich_rows=attach_demand_forecast,
        )
