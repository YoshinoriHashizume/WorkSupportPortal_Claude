from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.stockout_risk import (
    STOCKOUT_RISK_KEYS,
    row_stockout_risk,
)
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    FLOW_QUADRANT_KEYS,
    QUADRANT_NORMAL_FLOW,
    normalize_flow_quadrant,
)

CONFIRMATION_CONFIRMED = "確認済み"
CONFIRMATION_IN_PROGRESS = "確認中"
ROW_CLASS_CONFIRMED = "確認済"
ROW_CLASS_IN_PROGRESS = "確認中"
#: 在庫切れリスクごとの行クラス（`stockout-danger` / `stockout-caution` / `stockout-watch` / `stockout-none`）。
ROW_CLASS_STOCKOUT_PREFIX = "stockout-"


def is_confirmed_row(row: dict[str, object]) -> bool:
    return str(row.get("confirmation_status") or "") == CONFIRMATION_CONFIRMED


def is_in_progress_row(row: dict[str, object]) -> bool:
    return str(row.get("confirmation_status") or "") == CONFIRMATION_IN_PROGRESS


def display_flow_quadrant(row: dict[str, object]) -> str:
    return normalize_flow_quadrant(str(row.get("flow_quadrant") or QUADRANT_NORMAL_FLOW))


def row_alert_class(row: dict[str, object]) -> str:
    """行の強調に使うクラス（06 design §6.4、2026/09/18 改訂）。

    確認状態（確認済 / 確認中）を最優先し、未確認の行は **在庫切れリスク（S-204）だけ** で色を決める
    （`stockout-danger` = 赤、`stockout-caution` = 黄、`stockout-watch` / `stockout-none` = 色なし）。
    流動区分は行の色に使わず、セル内の色見本で示す（色の意味を 1 つにするため）。
    """
    if is_confirmed_row(row):
        return ROW_CLASS_CONFIRMED
    if is_in_progress_row(row):
        return ROW_CLASS_IN_PROGRESS
    return ROW_CLASS_STOCKOUT_PREFIX + STOCKOUT_RISK_KEYS[row_stockout_risk(row)]
