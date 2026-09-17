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

    @property
    def attention(self) -> int:
        return self.low_flow_no_incoming + self.dormant_stock + self.low_flow_no_shipment

    @property
    def has_alerts(self) -> bool:
        return self.attention > 0

    @property
    def flow_condition_label(self) -> str:
        return BANNER_FLOW_CONDITION_LABEL

    @property
    def tone(self) -> str:
        if self.error_message:
            return "neutral"
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
            )
        counts = count_rows(rows)
        stock_stale = is_stock_stale(stock_info.stock_as_of_date, app_settings.stock_stale_days)

        return DashboardBannerContext(
            low_flow_no_incoming=counts.low_flow_no_incoming,
            dormant_stock=counts.dormant_stock,
            low_flow_no_shipment=counts.low_flow_no_shipment,
            unconfirmed=counts.unconfirmed,
            stock_as_of_label=stock_info.stock_as_of_label,
            has_stock_data=True,
            stock_stale=stock_stale,
        )
