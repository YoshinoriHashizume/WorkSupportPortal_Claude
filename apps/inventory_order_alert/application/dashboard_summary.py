from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from apps.inventory_order_alert.application.list_summary import ListQuery, build_list_rows
from apps.inventory_order_alert.application.settings_service import AppSettings, get_app_settings
from apps.inventory_order_alert.domain.alert_level import (
    ALERT_CRITICAL,
    ALERT_NONE,
    ALERT_WARNING_INCOMING,
    ALERT_WARNING_SHIP,
    is_alert_none_level,
    normalize_alert_level,
)
from apps.inventory_order_alert.domain.row_display import (
    CONFIRMATION_CONFIRMED,
    CONFIRMATION_IN_PROGRESS,
)


@dataclass(frozen=True)
class RowCounts:
    total: int = 0
    critical: int = 0
    warning_ship: int = 0
    warning_incoming: int = 0
    alert_none: int = 0
    warning: int = 0
    alert: int = 0
    unconfirmed: int = 0
    in_progress: int = 0
    confirmed: int = 0


def _row_alert_level(row: dict[str, object]) -> str:
    return normalize_alert_level(str(row.get("alert_level") or ""))


def count_rows(rows: list[dict[str, object]]) -> RowCounts:
    critical = sum(1 for row in rows if _row_alert_level(row) == ALERT_CRITICAL)
    warning_ship = sum(1 for row in rows if _row_alert_level(row) == ALERT_WARNING_SHIP)
    warning_incoming = sum(1 for row in rows if _row_alert_level(row) == ALERT_WARNING_INCOMING)
    alert_none = sum(1 for row in rows if is_alert_none_level(_row_alert_level(row)))
    warning = warning_ship + warning_incoming
    unconfirmed = sum(
        1
        for row in rows
        if str(row.get("confirmation_status") or "") == "未確認"
    )
    in_progress = sum(
        1
        for row in rows
        if str(row.get("confirmation_status") or "") == CONFIRMATION_IN_PROGRESS
    )
    confirmed = sum(
        1
        for row in rows
        if str(row.get("confirmation_status") or "") == CONFIRMATION_CONFIRMED
    )
    return RowCounts(
        total=len(rows),
        critical=critical,
        warning_ship=warning_ship,
        warning_incoming=warning_incoming,
        alert_none=alert_none,
        warning=warning,
        alert=critical + warning,
        unconfirmed=unconfirmed,
        in_progress=in_progress,
        confirmed=confirmed,
    )


def merge_query_with_settings(query: ListQuery, settings: AppSettings | None = None) -> ListQuery:
    app_settings = settings or get_app_settings()
    return ListQuery(
        as_of_date=query.as_of_date,
        cust_code=query.cust_code,
        vend_code=query.vend_code,
        alert_only=query.alert_only,
        hide_confirmed=query.hide_confirmed,
        warning_shipment_months=app_settings.warning_shipment_months,
        warning_incoming_months=app_settings.warning_incoming_months,
        critical_enabled=app_settings.critical_enabled,
    )


def build_dashboard_summary(
    connection: object,
    *,
    as_of_date: date | None = None,
    stock_info: object | None = None,
    settings: AppSettings | None = None,
) -> tuple[RowCounts, object | None]:
    from apps.inventory_order_alert.application.stock_storage import load_latest_stock_lines

    app_settings = settings or get_app_settings()
    today = as_of_date or date.today()
    stock_lines, loaded_info = load_latest_stock_lines()
    stock = stock_info or loaded_info

    query = ListQuery(
        as_of_date=today,
        alert_only=True,
        warning_shipment_months=app_settings.warning_shipment_months,
        warning_incoming_months=app_settings.warning_incoming_months,
        critical_enabled=app_settings.critical_enabled,
    )
    rows = build_list_rows(
        connection,
        query,
        stock_lines=stock_lines,
        stock_as_of_date=stock.stock_as_of_date if stock else None,
    )
    return count_rows(rows), stock
