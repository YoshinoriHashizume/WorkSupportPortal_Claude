from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    FLOW_QUADRANT_KEYS,
    QUADRANT_NORMAL_FLOW,
    normalize_flow_quadrant,
)

CONFIRMATION_CONFIRMED = "確認済み"
CONFIRMATION_IN_PROGRESS = "確認中"
ROW_CLASS_CONFIRMED = "確認済"
ROW_CLASS_IN_PROGRESS = "確認中"


def is_confirmed_row(row: dict[str, object]) -> bool:
    return str(row.get("confirmation_status") or "") == CONFIRMATION_CONFIRMED


def is_in_progress_row(row: dict[str, object]) -> bool:
    return str(row.get("confirmation_status") or "") == CONFIRMATION_IN_PROGRESS


def display_flow_quadrant(row: dict[str, object]) -> str:
    return normalize_flow_quadrant(str(row.get("flow_quadrant") or QUADRANT_NORMAL_FLOW))


def row_alert_class(row: dict[str, object]) -> str:
    """行の強調に使うクラス（design.md §6.6.7）。

    確認状態は流動区分より優先する。未確認の行は流動区分の ASCII キーを返す。
    確認状態のクラスだけは既存の日本語のまま据え置く（本要件の対象外）。
    """
    if is_confirmed_row(row):
        return ROW_CLASS_CONFIRMED
    if is_in_progress_row(row):
        return ROW_CLASS_IN_PROGRESS
    return FLOW_QUADRANT_KEYS[display_flow_quadrant(row)]
