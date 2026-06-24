from __future__ import annotations

from dataclasses import dataclass

from apps.inventory_order_alert.domain.alert_level import (
    ALERT_CRITICAL,
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
