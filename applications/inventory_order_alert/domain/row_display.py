from __future__ import annotations

from applications.inventory_order_alert.domain.alert_level import ALERT_NONE, normalize_alert_level

CONFIRMATION_CONFIRMED = "確認済み"
CONFIRMATION_IN_PROGRESS = "確認中"
ROW_CLASS_CONFIRMED = "確認済"
ROW_CLASS_IN_PROGRESS = "確認中"


def is_confirmed_row(row: dict[str, object]) -> bool:
    return str(row.get("confirmation_status") or "") == CONFIRMATION_CONFIRMED


def is_in_progress_row(row: dict[str, object]) -> bool:
    return str(row.get("confirmation_status") or "") == CONFIRMATION_IN_PROGRESS


def counts_toward_alert_summary(row: dict[str, object]) -> bool:
    return not is_confirmed_row(row)


def display_alert_level(row: dict[str, object]) -> str:
    return normalize_alert_level(str(row.get("alert_level") or ALERT_NONE))


def row_alert_class(row: dict[str, object]) -> str:
    if is_confirmed_row(row):
        return ROW_CLASS_CONFIRMED
    if is_in_progress_row(row):
        return ROW_CLASS_IN_PROGRESS
    return normalize_alert_level(str(row.get("alert_level") or ALERT_NONE))
