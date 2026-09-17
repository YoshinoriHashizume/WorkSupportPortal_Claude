from __future__ import annotations

from dataclasses import dataclass

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_INCOMING,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
    normalize_flow_quadrant,
)
from application.inventory_order_alert.domain.value_objects.row_display import (
    CONFIRMATION_CONFIRMED,
    CONFIRMATION_IN_PROGRESS,
)


@dataclass(frozen=True)
class RowCounts:
    """件数サマリ（02 design.md §6.6.3、05 で新区分名に追随）。

    流動区分4値は排他かつ網羅であるため、4件数の和は常に `total` に一致する。
    確認状態の3件数とも一致するので、画面左右の合計が揃う。
    """

    total: int = 0
    low_flow_no_incoming: int = 0
    dormant_stock: int = 0
    low_flow_no_shipment: int = 0
    normal_flow: int = 0
    unconfirmed: int = 0
    in_progress: int = 0
    confirmed: int = 0

    @property
    def attention(self) -> int:
        """通常流動品を除く、対応が要る3区分の合計。"""
        return self.low_flow_no_incoming + self.dormant_stock + self.low_flow_no_shipment

    @property
    def by_quadrant(self) -> dict[str, int]:
        """流動区分ラベル → 件数（ランク順）。TC-SFV-D-057。"""
        return {
            QUADRANT_LOW_FLOW_NO_INCOMING: self.low_flow_no_incoming,
            QUADRANT_DORMANT_STOCK: self.dormant_stock,
            QUADRANT_LOW_FLOW_NO_SHIPMENT: self.low_flow_no_shipment,
            QUADRANT_NORMAL_FLOW: self.normal_flow,
        }


def _row_flow_quadrant(row: dict[str, object]) -> str:
    return normalize_flow_quadrant(str(row.get("flow_quadrant") or ""))


def _count_status(rows: list[dict[str, object]], status: str) -> int:
    return sum(1 for row in rows if str(row.get("confirmation_status") or "") == status)


def count_rows(rows: list[dict[str, object]]) -> RowCounts:
    quadrants = [_row_flow_quadrant(row) for row in rows]
    return RowCounts(
        total=len(rows),
        low_flow_no_incoming=quadrants.count(QUADRANT_LOW_FLOW_NO_INCOMING),
        dormant_stock=quadrants.count(QUADRANT_DORMANT_STOCK),
        low_flow_no_shipment=quadrants.count(QUADRANT_LOW_FLOW_NO_SHIPMENT),
        normal_flow=quadrants.count(QUADRANT_NORMAL_FLOW),
        unconfirmed=_count_status(rows, "未確認"),
        in_progress=_count_status(rows, CONFIRMATION_IN_PROGRESS),
        confirmed=_count_status(rows, CONFIRMATION_CONFIRMED),
    )
