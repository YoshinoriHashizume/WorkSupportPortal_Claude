from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.repositories.ports import LoadAppSettings, StockImporter
from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings
from application.inventory_order_alert.domain.value_objects.demand_forecast import attach_demand_forecast
from application.inventory_order_alert.domain.value_objects.flow_quadrant import REFERENCE_FLOW_SELECTION
from application.inventory_order_alert.domain.value_objects.list_query import ListQuery
from application.inventory_order_alert.domain.value_objects.list_rows import apply_flow_quadrants_to_rows
from application.inventory_order_alert.domain.value_objects.slims_stock import decode_slims_csv_bytes
from application.inventory_order_alert.domain.value_objects.stockout_risk import attach_stockout_risk
from application.inventory_order_alert.domain.value_objects.summary import StockImportInfo


class ImportStock:
    """SLIMS 在庫 CSV の取込。集計行の後処理（需要予測 → 在庫切れリスク）を取込ポートに渡す。"""

    def __init__(self, import_stock: StockImporter, load_app_settings: LoadAppSettings | None = None) -> None:
        self._import_stock = import_stock
        self._load_app_settings = load_app_settings

    def _enrich_rows(self, rows: list[dict[str, object]], as_of_date: date) -> list[dict[str, object]]:
        # 需要予測（05 design §6.7）→ 流動区分の引き直し（07 design §3.1）→ 在庫切れリスク（06 design §3）の順。
        # 流動区分を引き直すのは、在庫なしの行を 欠品／打ち切り候補 に振り分けるのに需要予測が要るため。
        # 設定値は取込時点の値を使う
        settings = self._load_app_settings() if self._load_app_settings is not None else AppSettings()
        thresholds = settings.to_flow_thresholds()
        with_forecast = attach_demand_forecast(rows, as_of_date)
        with_flow = apply_flow_quadrants_to_rows(
            with_forecast,
            as_of_date=as_of_date,
            query=ListQuery(as_of_date=as_of_date, flow_selection=REFERENCE_FLOW_SELECTION),
            thresholds=thresholds,
        )
        return attach_stockout_risk(
            with_flow,
            as_of_date,
            settings=settings.to_stockout_risk_settings(),
            thresholds=thresholds,
        )

    def execute(self, raw_bytes: bytes, *, user: object | None = None, file_name: str = "") -> StockImportInfo:
        return self._import_stock(
            decode_slims_csv_bytes(raw_bytes),
            user=user,
            file_name=file_name,
            enrich_rows=self._enrich_rows,
        )
