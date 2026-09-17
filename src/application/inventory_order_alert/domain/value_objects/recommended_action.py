"""推奨アクション（T-207）と状況テンプレートのドメイン定義（design §4.3）。

流動区分（S-203）ごとに 状況テンプレート / 推奨アクション / 責任部署（R-201）を
`RecommendedAction` に束ね、4 区分ぶんを `RecommendedActions` で保持する。
文言の定義表はここ 1 か所に置き、`flow_quadrant.responsible_departments()` もここを引く。
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, replace

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    FLOW_QUADRANT_KEYS,
    FLOW_QUADRANT_LABELS,
    FLOW_QUADRANT_SORT_RANK,
    FLOW_QUADRANTS,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_INCOMING,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
    EvaluationPeriod,
)

#: 状況テンプレートのプレースホルダ。
PLACEHOLDER_PERIOD = "{period}"
PLACEHOLDER_LAST_INCOMING = "{last_incoming}"
PLACEHOLDER_LAST_SHIP = "{last_ship}"

#: 入荷実績なし（V-214）の行で最終入荷日の代わりに示す文言（REQ-SFV-F-005）。
NO_INCOMING_RECORD_TEXT = "入荷実績なし"


@dataclass(frozen=True)
class RecommendedAction:
    """流動区分 1 つぶんの 状況テンプレート・推奨アクション・責任部署。"""

    quadrant: str
    status_template: str
    action: str
    departments: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.quadrant not in FLOW_QUADRANT_KEYS:
            raise ValueError(f"流動区分のラベルではありません: {self.quadrant!r}")
        object.__setattr__(self, "departments", tuple(self.departments))

    @property
    def key(self) -> str:
        """CSS キー・URL 値・定義ファイルのキー（例: `low-flow-no-incoming`）。"""

        return FLOW_QUADRANT_KEYS[self.quadrant]


@dataclass(frozen=True)
class RecommendedActions:
    """4 区分ぶんの推奨アクションのファーストクラスコレクション。欠け・重複を許さない。"""

    actions: tuple[RecommendedAction, ...]

    def __post_init__(self) -> None:
        quadrants = [action.quadrant for action in self.actions]
        if sorted(quadrants) != sorted(FLOW_QUADRANTS):
            raise ValueError(f"推奨アクションは流動区分 4 値すべてを 1 件ずつ含む必要があります: {quadrants}")
        ordered = tuple(sorted(self.actions, key=lambda action: FLOW_QUADRANT_SORT_RANK[action.quadrant]))
        object.__setattr__(self, "actions", ordered)

    def __iter__(self) -> Iterator[RecommendedAction]:
        return iter(self.actions)

    def __len__(self) -> int:
        return len(self.actions)

    def for_quadrant(self, quadrant: str) -> RecommendedAction:
        for action in self.actions:
            if action.quadrant == quadrant:
                return action
        raise KeyError(quadrant)

    def with_action_texts(self, overrides: Mapping[str, str]) -> RecommendedActions:
        """定義ファイル等の上書き（流動区分キー → 文言）を推奨アクションにのみ適用する。未知のキーは無視。"""

        texts = {FLOW_QUADRANT_LABELS[key]: text for key, text in overrides.items() if key in FLOW_QUADRANT_LABELS}
        return RecommendedActions(
            tuple(
                replace(action, action=str(texts[action.quadrant])) if action.quadrant in texts else action
                for action in self.actions
            )
        )


#: 既定の定義表（用語集 S-203 の構成要素）。推奨アクションの文言は暫定（T-207）。
DEFAULT_RECOMMENDED_ACTIONS = RecommendedActions(
    (
        RecommendedAction(
            quadrant=QUADRANT_LOW_FLOW_NO_INCOMING,
            status_template="出荷は継続、最終入荷 {last_incoming}（{period}以上入荷なし）",
            action="仕入先へ生産継続可否・設備/金型の有無を確認。在庫切れ予測月が近いものから",
            departments=("調達G", "営業G", "生産管理"),
        ),
        RecommendedAction(
            quadrant=QUADRANT_DORMANT_STOCK,
            status_template="{period}以上、入荷も出荷もなし（最終入荷 {last_incoming}・最終出荷 {last_ship}）",
            action="処分・廃却の検討、得意先へ補給要否を確認",
            departments=("調達G",),
        ),
        RecommendedAction(
            quadrant=QUADRANT_LOW_FLOW_NO_SHIPMENT,
            status_template="入荷はあるが{period}以上出荷なし（最終出荷 {last_ship}）",
            action="発注を抑制、営業へ需要を確認",
            departments=("営業G",),
        ),
        RecommendedAction(
            quadrant=QUADRANT_NORMAL_FLOW,
            status_template="",
            action="",
            departments=("生産管理",),
        ),
    )
)


def render_status(
    action: RecommendedAction,
    *,
    period: EvaluationPeriod,
    last_incoming: str,
    last_ship: str,
    no_incoming_record: bool,
) -> str:
    """状況テンプレートのプレースホルダを埋めて S-203 の「状況」文字列にする。"""

    incoming_text = NO_INCOMING_RECORD_TEXT if no_incoming_record else str(last_incoming or "")
    return (
        action.status_template.replace(PLACEHOLDER_PERIOD, period.label)
        .replace(PLACEHOLDER_LAST_INCOMING, incoming_text)
        .replace(PLACEHOLDER_LAST_SHIP, str(last_ship or ""))
    )
