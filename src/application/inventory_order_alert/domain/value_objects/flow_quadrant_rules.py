"""判定ルールダイアログに表示する流動区分の凡例（design.md §6.6.5）。"""

from __future__ import annotations

from dataclasses import dataclass

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    FLOW_QUADRANT_KEYS,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_EXCESS_STOCK_RISK,
    QUADRANT_NORMAL_FLOW,
    QUADRANT_SUPPLY_RISK,
    responsible_departments,
)

#: 凡例1行あたりの (期間内入荷, 期間内出荷, 流動区分)。緊急度順に並べる。
_RULE_CONDITIONS = (
    ("なし", "あり", QUADRANT_SUPPLY_RISK),
    ("なし", "なし", QUADRANT_DORMANT_STOCK),
    ("あり", "なし", QUADRANT_EXCESS_STOCK_RISK),
    ("あり", "あり", QUADRANT_NORMAL_FLOW),
)


@dataclass(frozen=True)
class FlowQuadrantRuleRow:
    has_incoming: str
    has_shipment: str
    quadrant: str
    quadrant_key: str
    departments: tuple[str, ...]


def build_flow_quadrant_rule_rows() -> list[FlowQuadrantRuleRow]:
    """判定期間に依存しない固定の凡例4行を返す。"""

    return [
        FlowQuadrantRuleRow(
            has_incoming=has_incoming,
            has_shipment=has_shipment,
            quadrant=quadrant,
            quadrant_key=FLOW_QUADRANT_KEYS[quadrant],
            departments=responsible_departments(quadrant),
        )
        for has_incoming, has_shipment, quadrant in _RULE_CONDITIONS
    ]
