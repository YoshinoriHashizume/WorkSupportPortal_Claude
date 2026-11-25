from __future__ import annotations

import logging
from datetime import date

from application.inventory_order_alert.domain.repositories.ports import LoadAppSettings, StockImporter
from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings
from application.inventory_order_alert.domain.value_objects.demand_forecast import attach_demand_forecast
from application.inventory_order_alert.domain.value_objects.direct_shipment import exclude_direct_shipment_items
from application.inventory_order_alert.domain.value_objects.flow_quadrant import REFERENCE_FLOW_SELECTION
from application.inventory_order_alert.domain.value_objects.list_query import ListQuery
from application.inventory_order_alert.domain.value_objects.list_rows import apply_flow_quadrants_to_rows
from application.inventory_order_alert.domain.value_objects.slims_stock import decode_slims_csv_bytes
from application.inventory_order_alert.domain.value_objects.stockout_risk import attach_response_class
from application.inventory_order_alert.domain.value_objects.summary import StockImportInfo

logger = logging.getLogger(__name__)


class ImportStock:
    """SLIMS 在庫 CSV の取込。集計行の後処理（直送品の除外 → 需要予測 → 対応区分）を取込ポートに渡す。"""

    def __init__(self, import_stock: StockImporter, load_app_settings: LoadAppSettings | None = None) -> None:
        self._import_stock = import_stock
        self._load_app_settings = load_app_settings

    def _load_settings(self) -> AppSettings:
        return self._load_app_settings() if self._load_app_settings is not None else AppSettings()

    def _enrich_rows(
        self,
        rows: list[dict[str, object]],
        as_of_date: date,
        settings: AppSettings | None = None,
    ) -> list[dict[str, object]]:
        # 直送品の除外（12 design §6.4）→ 需要予測（05 design §6.7）→ 流動区分の引き直し（07 design §3.1）
        # → 対応区分（08 design §3）の順。
        # 直送品は照合単位ごと除くので、残る照合単位の計算は除く前と変わらない（12 REQ-DSE-NF-003）。
        # 流動区分を引き直すのは、在庫なしの行を 欠品／打ち切り候補 に振り分けるのに需要予測が要るため。
        settings = settings if settings is not None else self._load_settings()
        exclusion = exclude_direct_shipment_items(rows, settings.direct_shipment_suppliers)
        if exclusion.excluded_row_count:
            logger.info(
                "直送品を集計から除外しました: %d 照合単位・%d 行",
                exclusion.excluded_unit_count,
                exclusion.excluded_row_count,
            )
        thresholds = settings.to_flow_thresholds()
        with_forecast = attach_demand_forecast(exclusion.kept_rows, as_of_date)
        with_flow = apply_flow_quadrants_to_rows(
            with_forecast,
            as_of_date=as_of_date,
            query=ListQuery(as_of_date=as_of_date, flow_selection=REFERENCE_FLOW_SELECTION),
            thresholds=thresholds,
        )
        return attach_response_class(
            with_flow,
            as_of_date,
            default_lead_time_days=settings.default_lead_time_days,
            # 判定ホライズン（V-239）・滞留発注残（V-238）の閾値も取込時点の設定を使う（11 REQ-JS-F-008）
            judgement_horizon_days=settings.judgement_horizon_days,
            stale_order_days=settings.stale_order_days,
        )

    def execute(self, raw_bytes: bytes, *, user: object | None = None, file_name: str = "") -> StockImportInfo:
        # 設定は取込の開始時点の値を 1 回だけ読む。取込中に設定が変わっても同じ取込の中で混ざらない（12 REQ-DSE-F-002）
        settings = self._load_settings()
        return self._import_stock(
            decode_slims_csv_bytes(raw_bytes),
            user=user,
            file_name=file_name,
            enrich_rows=lambda rows, as_of_date: self._enrich_rows(rows, as_of_date, settings),
        )
