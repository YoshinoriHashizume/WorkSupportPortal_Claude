"""判定ルールダイアログに表示する流動区分の凡例（05 design §6.3、REQ-SFV-F-012）。

期間内入荷・期間内出荷の有無 → 流動区分（S-203）の対応に、
状況テンプレート・推奨アクション（T-207）・責任部署（R-201）を添えてランク順に並べる。
判定期間（V-211）には依存しない。
"""

from __future__ import annotations

from dataclasses import dataclass

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    FLOW_QUADRANT_KEYS,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_INCOMING,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
)
from application.inventory_order_alert.domain.value_objects.recommended_action import (
    DEFAULT_RECOMMENDED_ACTIONS,
    RecommendedActions,
)

#: 凡例1行あたりの (期間内入荷, 期間内出荷, 流動区分)。ランク順（S-203）に並べる。
_RULE_CONDITIONS = (
    ("なし", "あり", QUADRANT_LOW_FLOW_NO_INCOMING),
    ("なし", "なし", QUADRANT_DORMANT_STOCK),
    ("あり", "なし", QUADRANT_LOW_FLOW_NO_SHIPMENT),
    ("あり", "あり", QUADRANT_NORMAL_FLOW),
)


@dataclass(frozen=True)
class FlowQuadrantRuleRow:
    has_incoming: str
    has_shipment: str
    quadrant: str
    quadrant_key: str
    status_template: str
    action: str
    departments: tuple[str, ...]


def build_flow_quadrant_rule_rows(
    recommended_actions: RecommendedActions = DEFAULT_RECOMMENDED_ACTIONS,
) -> list[FlowQuadrantRuleRow]:
    """固定の凡例 4 行を返す。推奨アクションの文言は定義表（上書き済みなら上書き後）から引く。"""

    rows: list[FlowQuadrantRuleRow] = []
    for has_incoming, has_shipment, quadrant in _RULE_CONDITIONS:
        recommended = recommended_actions.for_quadrant(quadrant)
        rows.append(
            FlowQuadrantRuleRow(
                has_incoming=has_incoming,
                has_shipment=has_shipment,
                quadrant=quadrant,
                quadrant_key=FLOW_QUADRANT_KEYS[quadrant],
                status_template=recommended.status_template,
                action=recommended.action,
                departments=recommended.departments,
            )
        )
    return rows
