from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.inventory_order_alert.domain.row_counts import count_rows
from apps.inventory_order_alert.domain.ports import LoadAppSettings, LoadSummary

_BANNER_ERROR_MESSAGE = "アラート件数を取得できませんでした。在庫発注アラート画面で再確認してください。"


@dataclass(frozen=True)
class DashboardBannerContext:
    critical: int
    warning_ship: int
    warning_incoming: int
    unconfirmed: int
    stock_as_of_label: str
    has_stock_data: bool
    stock_stale: bool
    error_message: str = ""

    @property
    def warning(self) -> int:
        return self.warning_ship + self.warning_incoming

    @property
    def has_alerts(self) -> bool:
        return self.critical > 0 or self.warning > 0

    @property
    def tone(self) -> str:
        if self.error_message:
            return "neutral"
        if self.critical > 0:
            return "critical"
        if self.warning > 0:
            return "warning"
        return "ok"


class PortalDashboardUsecase:
    def __init__(self, load_summary: LoadSummary, load_app_settings: LoadAppSettings) -> None:
        self._load_summary = load_summary
        self._load_app_settings = load_app_settings

    def execute(self) -> DashboardBannerContext:
        summary = self._load_summary()
        if summary is None or summary.stock_info is None or not summary.stock_info.has_data:
            return DashboardBannerContext(
                critical=0,
                warning_ship=0,
                warning_incoming=0,
                unconfirmed=0,
                stock_as_of_label="",
                has_stock_data=False,
                stock_stale=False,
            )

        stock_info = summary.stock_info
        if summary.aggregation_error:
            return DashboardBannerContext(
                critical=0,
                warning_ship=0,
                warning_incoming=0,
                unconfirmed=0,
                stock_as_of_label=stock_info.stock_as_of_label,
                has_stock_data=True,
                stock_stale=False,
                error_message=_BANNER_ERROR_MESSAGE,
            )

        counts = count_rows(summary.rows)
        app_settings = self._load_app_settings()
        stock_stale = (timezone.localdate() - stock_info.stock_as_of_date).days > app_settings.stock_stale_days

        return DashboardBannerContext(
            critical=counts.critical,
            warning_ship=counts.warning_ship,
            warning_incoming=counts.warning_incoming,
            unconfirmed=counts.unconfirmed,
            stock_as_of_label=stock_info.stock_as_of_label,
            has_stock_data=True,
            stock_stale=stock_stale,
        )
