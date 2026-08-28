from __future__ import annotations

from dataclasses import dataclass

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    QUADRANT_DORMANT_STOCK,
    QUADRANT_EXCESS_STOCK_RISK,
    QUADRANT_NORMAL_FLOW,
    QUADRANT_SUPPLY_RISK,
    normalize_flow_quadrant,
)
from application.inventory_order_alert.domain.value_objects.row_display import (
    CONFIRMATION_CONFIRMED,
    CONFIRMATION_IN_PROGRESS,
)


@dataclass(frozen=True)
class RowCounts:
    """件数サマリ（design.md §6.6.3）。

    流動区分4値は排他かつ網羅であるため、4件数の和は常に `total` に一致する。
    確認状態の3件数とも一致するので、画面左右の合計が揃う。
    """

    total: int = 0
    supply_risk: int = 0
    dormant_stock: int = 0
    excess_stock_risk: int = 0
    normal_flow: int = 0
    unconfirmed: int = 0
    in_progress: int = 0
    confirmed: int = 0

    @property
    def attention(self) -> int:
        """通常流動品を除く、対応が要る3区分の合計。"""
        return self.supply_risk + self.dormant_stock + self.excess_stock_risk


def _row_flow_quadrant(row: dict[str, object]) -> str:
    return normalize_flow_quadrant(str(row.get("flow_quadrant") or ""))


def _count_status(rows: list[dict[str, object]], status: str) -> int:
    return sum(1 for row in rows if str(row.get("confirmation_status") or "") == status)


def count_rows(rows: list[dict[str, object]]) -> RowCounts:
    quadrants = [_row_flow_quadrant(row) for row in rows]
    return RowCounts(
        total=len(rows),
        supply_risk=quadrants.count(QUADRANT_SUPPLY_RISK),
        dormant_stock=quadrants.count(QUADRANT_DORMANT_STOCK),
        excess_stock_risk=quadrants.count(QUADRANT_EXCESS_STOCK_RISK),
        normal_flow=quadrants.count(QUADRANT_NORMAL_FLOW),
        unconfirmed=_count_status(rows, "未確認"),
        in_progress=_count_status(rows, CONFIRMATION_IN_PROGRESS),
        confirmed=_count_status(rows, CONFIRMATION_CONFIRMED),
    )
