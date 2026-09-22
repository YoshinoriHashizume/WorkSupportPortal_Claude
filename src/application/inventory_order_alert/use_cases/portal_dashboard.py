from __future__ import annotations

from dataclasses import dataclass

from application.inventory_order_alert.domain.repositories.ports import LoadAppSettings, LoadSummary
from application.inventory_order_alert.domain.value_objects.dates import is_stock_stale
from application.inventory_order_alert.domain.value_objects.flow_quadrant import REFERENCE_FLOW_SELECTION
from application.inventory_order_alert.domain.value_objects.list_query import ListQuery
from application.inventory_order_alert.domain.value_objects.list_rows import apply_flow_quadrants_to_rows
from application.inventory_order_alert.domain.value_objects.row_counts import count_rows

_BANNER_ERROR_MESSAGE = "アラート件数を取得できませんでした。在庫発注アラート画面で再確認してください。"

#: 帯の件数は既定の判定期間（1 年）で固定する。利用者が一覧で選んだ判定期間には従わない（05 design §6.5）。
BANNER_FLOW_SELECTION = REFERENCE_FLOW_SELECTION
BANNER_FLOW_CONDITION_LABEL = f"判定期間 {BANNER_FLOW_SELECTION.period_label}"
#: 在庫切れリスク（S-204）の件数はスナップショット保存値（取込時の設定）を数える。監視期間は表示上の既定値
BANNER_WATCH_MONTHS_LABEL = "監視期間 6か月"


@dataclass(frozen=True)
class DashboardBannerContext:
    low_flow_no_incoming: int
    dormant_stock: int
    low_flow_no_shipment: int
    unconfirmed: int
    stock_as_of_label: str
    has_stock_data: bool
    stock_stale: bool
    error_message: str = ""
    #: 在庫切れリスク（06）。危険 > 0 で赤系、注意のみで黄系
    danger: int = 0
    caution: int = 0
    watch: int = 0
    #: 07 在庫なしの 3 区分（design §3.2）
    stockout_no_incoming: int = 0
    stockout: int = 0
    discontinuation_candidate: int = 0

    @property
    def attention(self) -> int:
        """通常流動品以外の合計（07 design §2.7）。"""
        return (
            self.stockout_no_incoming
            + self.stockout
            + self.low_flow_no_incoming
            + self.dormant_stock
            + self.low_flow_no_shipment
            + self.discontinuation_candidate
        )

    @property
    def has_alerts(self) -> bool:
        return self.attention > 0 or self.danger > 0 or self.caution > 0

    @property
    def stockout_condition_label(self) -> str:
        return f"{BANNER_FLOW_CONDITION_LABEL}・{BANNER_WATCH_MONTHS_LABEL}"

    @property
    def flow_condition_label(self) -> str:
        return BANNER_FLOW_CONDITION_LABEL

    @property
    def tone(self) -> str:
        if self.error_message:
            return "neutral"
        # 在庫切れリスクを優先（06 design §6.5）。危険 > 0 で赤系、注意のみで黄系
        if self.danger > 0:
            return "critical"
        if self.caution > 0:
            return "warning"
        # 欠品（在庫なし・需要あり）は在庫切れリスクと同じ重さで赤系（07 design §3.2）
        if self.stockout_no_incoming > 0 or self.stockout > 0:
            return "critical"
        if self.low_flow_no_incoming > 0:
            return "critical"
        if self.dormant_stock > 0 or self.low_flow_no_shipment > 0:
            return "warning"
        return "ok"


def _empty_context(*, stock_as_of_label: str, has_stock_data: bool, error_message: str = "") -> DashboardBannerContext:
    return DashboardBannerContext(
        low_flow_no_incoming=0,
        dormant_stock=0,
        low_flow_no_shipment=0,
        unconfirmed=0,
        stock_as_of_label=stock_as_of_label,
        has_stock_data=has_stock_data,
        stock_stale=False,
        error_message=error_message,
    )


class PortalDashboard:
    def __init__(self, load_summary: LoadSummary, load_app_settings: LoadAppSettings) -> None:
        self._load_summary = load_summary
        self._load_app_settings = load_app_settings

    def execute(self) -> DashboardBannerContext:
        summary = self._load_summary()
        if summary is None or summary.stock_info is None or not summary.stock_info.has_data:
            return _empty_context(stock_as_of_label="", has_stock_data=False)

        stock_info = summary.stock_info
        if summary.aggregation_error:
            return _empty_context(
                stock_as_of_label=stock_info.stock_as_of_label,
                has_stock_data=True,
                error_message=_BANNER_ERROR_MESSAGE,
            )

        app_settings = self._load_app_settings()
        as_of_date = summary.as_of_date or stock_info.stock_as_of_date
        rows = summary.rows
        if rows and as_of_date is not None:
            rows = apply_flow_quadrants_to_rows(
                rows,
                as_of_date=as_of_date,
                query=ListQuery(as_of_date=as_of_date, flow_selection=BANNER_FLOW_SELECTION),
                thresholds=app_settings.to_flow_thresholds(),
            )
        counts = count_rows(rows)
        stock_stale = is_stock_stale(stock_info.stock_as_of_date, app_settings.stock_stale_days)

        return DashboardBannerContext(
            stockout_no_incoming=counts.stockout_no_incoming,
            stockout=counts.stockout,
            discontinuation_candidate=counts.discontinuation_candidate,
            low_flow_no_incoming=counts.low_flow_no_incoming,
            dormant_stock=counts.dormant_stock,
            low_flow_no_shipment=counts.low_flow_no_shipment,
            unconfirmed=counts.unconfirmed,
            stock_as_of_label=stock_info.stock_as_of_label,
            has_stock_data=True,
            stock_stale=stock_stale,
            danger=counts.danger,
            caution=counts.caution,
            watch=counts.watch,
        )
