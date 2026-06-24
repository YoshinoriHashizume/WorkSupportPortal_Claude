from __future__ import annotations

from datetime import date

from apps.inventory_order_alert.domain.dates import has_passed_calendar_months, is_within_calendar_months

ALERT_NONE = "アラート無し"
LEGACY_ALERT_NONE_LABELS = frozenset({"なし", "アラートなし", "問題なし", ""})
LEGACY_ALERT_WARNING_SHIP = "警告（出荷）"
LEGACY_ALERT_WARNING_INCOMING = "警告（入荷）"
ALERT_CRITICAL = "重点"
ALERT_WARNING_SHIP = "警告（出荷あり）"
ALERT_WARNING_INCOMING = "警告（出荷なし）"

ALERT_LEVELS = (
    ALERT_CRITICAL,
    ALERT_WARNING_SHIP,
    ALERT_WARNING_INCOMING,
)


def has_balanced_incoming_shipment(
    last_incoming_date: date | None,
    last_ship_date: date | None,
    *,
    warning_shipment_months: int,
) -> bool:
    """入出荷バランス良好 = 最終入荷後 warning_shipment_months か月以内に最終出荷がある。"""
    if last_incoming_date is None or last_ship_date is None:
        return False
    return is_within_calendar_months(
        start=last_incoming_date,
        end=last_ship_date,
        months=warning_shipment_months,
    )


def normalize_alert_level(level: str) -> str:
    text = str(level or "").strip()
    if text in LEGACY_ALERT_NONE_LABELS:
        return ALERT_NONE
    if text == LEGACY_ALERT_WARNING_SHIP:
        return ALERT_WARNING_SHIP
    if text == LEGACY_ALERT_WARNING_INCOMING:
        return ALERT_WARNING_INCOMING
    return text


def is_alert_none_level(level: str) -> bool:
    return normalize_alert_level(level) == ALERT_NONE


def resolve_alert_level(
    last_incoming_date: date | None,
    last_ship_date: date | None,
    post_shipment_count: int,
    *,
    as_of_date: date,
    warning_shipment_months: int = 12,
    warning_incoming_months: int = 12,
    critical_enabled: bool = True,
) -> str:
    balanced = has_balanced_incoming_shipment(
        last_incoming_date,
        last_ship_date,
        warning_shipment_months=warning_shipment_months,
    )

    if critical_enabled and last_incoming_date is None and post_shipment_count > 0:
        return ALERT_CRITICAL

    if last_incoming_date is not None and post_shipment_count > 0 and not balanced:
        return ALERT_WARNING_SHIP

    if (
        last_incoming_date is not None
        and post_shipment_count == 0
        and has_passed_calendar_months(
            start=last_incoming_date,
            end=as_of_date,
            months=warning_incoming_months,
        )
    ):
        return ALERT_WARNING_INCOMING

    return ALERT_NONE


def is_alert_level(level: str) -> bool:
    return normalize_alert_level(level) in ALERT_LEVELS


def alert_sort_rank(level: str) -> int:
    normalized = normalize_alert_level(level)
    return {
        ALERT_CRITICAL: 0,
        ALERT_WARNING_SHIP: 1,
        ALERT_WARNING_INCOMING: 2,
        ALERT_NONE: 3,
    }.get(normalized, 99)


def is_alert_escalated(previous_level: str, current_level: str) -> bool:
    """確認時よりアラートが深刻化したか（重点化を含む）。"""
    previous_rank = alert_sort_rank(previous_level)
    current_rank = alert_sort_rank(current_level)
    return current_rank < previous_rank


def lookup_alert_level_for_row(
    rows: list[dict[str, object]],
    *,
    cust_code: str,
    item_cd: str,
) -> str:
    for row in rows:
        if str(row.get("cust_code") or "") == cust_code and str(row.get("item_cd") or "") == item_cd:
            return normalize_alert_level(str(row.get("alert_level") or ""))
    return ALERT_NONE
