"""判定ルールダイアログに表示する流動区分の凡例（05 design §6.3、REQ-SFV-F-012、07 design §2.9）。

判定材料（在庫 / 需要 / 直近入荷 / 期間内入荷 / 期間内出荷）→ 流動区分（S-203）の対応に、
状況テンプレート・推奨アクション（T-207）・責任部署（R-201）を添えてランク順に並べる。
在庫なし（T-209/T-210）の 3 行は判定期間（V-211）によらず、需要と直近入荷で分かれる。
在庫ありの 4 行は期間内入荷・期間内出荷で分かれ、需要・直近入荷は見ない。該当しない材料は「—」。
"""

from __future__ import annotations

from dataclasses import dataclass

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    FLOW_QUADRANT_KEYS,
    QUADRANT_DISCONTINUATION_CANDIDATE,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_INCOMING,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
    QUADRANT_STOCKOUT,
    QUADRANT_STOCKOUT_NO_INCOMING,
)
from application.inventory_order_alert.domain.value_objects.recommended_action import (
    DEFAULT_RECOMMENDED_ACTIONS,
    RecommendedActions,
    describe_status_template,
)

#: 判定材料が区分の決定に関与しないことを示す表記。
NOT_APPLICABLE = "—"

#: 凡例1行あたりの (在庫, 需要, 直近入荷, 期間内入荷, 期間内出荷, 流動区分)。ランク順（S-203）に並べる。
_RULE_CONDITIONS = (
    ("なし", "あり", "なし", NOT_APPLICABLE, NOT_APPLICABLE, QUADRANT_STOCKOUT_NO_INCOMING),
    ("なし", "あり", "あり", NOT_APPLICABLE, NOT_APPLICABLE, QUADRANT_STOCKOUT),
    ("あり", NOT_APPLICABLE, NOT_APPLICABLE, "なし", "あり", QUADRANT_LOW_FLOW_NO_INCOMING),
    ("あり", NOT_APPLICABLE, NOT_APPLICABLE, "なし", "なし", QUADRANT_DORMANT_STOCK),
    ("あり", NOT_APPLICABLE, NOT_APPLICABLE, "あり", "なし", QUADRANT_LOW_FLOW_NO_SHIPMENT),
    ("なし", "なし", NOT_APPLICABLE, NOT_APPLICABLE, NOT_APPLICABLE, QUADRANT_DISCONTINUATION_CANDIDATE),
    ("あり", NOT_APPLICABLE, NOT_APPLICABLE, "あり", "あり", QUADRANT_NORMAL_FLOW),
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
    #: 凡例向け: 日付を `YYYY/MM/DD` にした状況（`{period}` は残す。JS が判定期間で置換する）
    status_example: str = ""
    #: 凡例向け: `{period}` も埋めた状況（サーバ描画の初期表示）
    status_text: str = ""
    #: 07 の判定材料: SLIMS 在庫（あり/なし）、需要（あり/なし/—）、直近入荷（あり/なし/—）
    stock: str = NOT_APPLICABLE
    demand: str = NOT_APPLICABLE
    recent_incoming: str = NOT_APPLICABLE


def build_flow_quadrant_rule_rows(
    recommended_actions: RecommendedActions = DEFAULT_RECOMMENDED_ACTIONS,
    *,
    period_label: str = "判定期間",
) -> list[FlowQuadrantRuleRow]:
    """固定の凡例 7 行を返す。推奨アクションの文言は定義表（上書き済みなら上書き後）から引く。

    `period_label` は凡例の状況文言に埋める判定期間ラベル（例: `1年`）。
    """

    rows: list[FlowQuadrantRuleRow] = []
    for stock, demand, recent_incoming, has_incoming, has_shipment, quadrant in _RULE_CONDITIONS:
        recommended = recommended_actions.for_quadrant(quadrant)
        rows.append(
            FlowQuadrantRuleRow(
                stock=stock,
                demand=demand,
                recent_incoming=recent_incoming,
                has_incoming=has_incoming,
                has_shipment=has_shipment,
                quadrant=quadrant,
                quadrant_key=FLOW_QUADRANT_KEYS[quadrant],
                status_template=recommended.status_template,
                action=recommended.action,
                departments=recommended.departments,
                status_example=describe_status_template(recommended.status_template),
                status_text=describe_status_template(recommended.status_template, period_label=period_label),
            )
        )
    return rows
