from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.stockout_risk import (
    RESPONSE_CLASS_KEYS,
    row_response_class,
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
#: 対応区分ごとの行クラス（`response-order-overdue` / `response-delivery-check` / `response-order-needed`
#: / `response-watch` / `response-none`）。
ROW_CLASS_RESPONSE_PREFIX = "response-"


def is_confirmed_row(row: dict[str, object]) -> bool:
    return str(row.get("confirmation_status") or "") == CONFIRMATION_CONFIRMED


def is_in_progress_row(row: dict[str, object]) -> bool:
    return str(row.get("confirmation_status") or "") == CONFIRMATION_IN_PROGRESS


def display_flow_quadrant(row: dict[str, object]) -> str:
    return normalize_flow_quadrant(str(row.get("flow_quadrant") or QUADRANT_NORMAL_FLOW))


def row_alert_class(row: dict[str, object]) -> str:
    """行の強調に使うクラス（08 design §5、2026/09/23 改訂）。

    確認状態（確認済 / 確認中）を最優先し、未確認の行は **対応区分（S-204）だけ** で色を決める
    （`response-order-overdue` = 赤、`response-delivery-check` / `response-order-needed` = 黄、
    `response-watch` / `response-none` = 色なし）。
    流動区分は行の色に使わず、セル内のバッジで示す（色の意味を 1 つにするため）。
    """
    if is_confirmed_row(row):
        return ROW_CLASS_CONFIRMED
    if is_in_progress_row(row):
        return ROW_CLASS_IN_PROGRESS
    return ROW_CLASS_RESPONSE_PREFIX + RESPONSE_CLASS_KEYS[row_response_class(row)]
