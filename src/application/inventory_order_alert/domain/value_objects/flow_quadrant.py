"""流動区分（S-203）と判定条件（判定軸 V-210 × 判定期間 V-211）のドメイン定義。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from application.inventory_order_alert.domain.value_objects.dates import add_calendar_months

# --- 判定軸（V-210） ---

FLOW_AXIS_LOW_FLOW = "low_flow"
FLOW_AXIS_DORMANT = "dormant"

FLOW_AXIS_LABELS = {
    FLOW_AXIS_LOW_FLOW: "低流動判定軸",
    FLOW_AXIS_DORMANT: "死蔵判定軸",
}

#: 判定軸ごとの補助テキスト（design.md §6.6.6）
FLOW_AXIS_HELP_TEXTS = {
    FLOW_AXIS_LOW_FLOW: "判定期間内に入出荷のない品目（低流動品）を洗い出します",
    FLOW_AXIS_DORMANT: "長期にわたり動きのない品目（在庫死蔵品）を洗い出します",
}

DEFAULT_FLOW_AXIS = FLOW_AXIS_LOW_FLOW

DEFAULT_LOW_FLOW_VALUE = 3
DEFAULT_DORMANT_VALUE = 1


# --- 判定期間（V-211） ---


@dataclass(frozen=True)
class EvaluationPeriod:
    axis: str
    value: int

    @property
    def months(self) -> int:
        if self.axis == FLOW_AXIS_DORMANT:
            return self.value * 12
        return self.value

    @property
    def key(self) -> str:
        prefix = "D" if self.axis == FLOW_AXIS_DORMANT else "L"
        return f"{prefix}{self.value}"

    @property
    def label(self) -> str:
        if self.axis == FLOW_AXIS_DORMANT:
            return f"{self.value}年"
        return f"{self.value}か月"


class EvaluationPeriods:
    """選択可能な判定期間6値のファーストクラスコレクション。"""

    def __init__(self, periods: tuple[EvaluationPeriod, ...]) -> None:
        self._periods = tuple(periods)

    def for_axis(self, axis: str) -> tuple[EvaluationPeriod, ...]:
        return tuple(period for period in self._periods if period.axis == axis)

    def default_for_axis(self, axis: str) -> EvaluationPeriod:
        if axis == FLOW_AXIS_DORMANT:
            return EvaluationPeriod(FLOW_AXIS_DORMANT, DEFAULT_DORMANT_VALUE)
        return EvaluationPeriod(FLOW_AXIS_LOW_FLOW, DEFAULT_LOW_FLOW_VALUE)

    def find(self, key: str) -> EvaluationPeriod | None:
        for period in self._periods:
            if period.key == key:
                return period
        return None

    def __iter__(self):
        return iter(self._periods)

    def __len__(self) -> int:
        return len(self._periods)


EVALUATION_PERIODS = EvaluationPeriods(
    (
        EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 1),
        EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 3),
        EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 6),
        EvaluationPeriod(FLOW_AXIS_DORMANT, 1),
        EvaluationPeriod(FLOW_AXIS_DORMANT, 2),
        EvaluationPeriod(FLOW_AXIS_DORMANT, 5),
    )
)


@dataclass(frozen=True)
class FlowSelection:
    """利用者が選択した判定条件（判定軸 × 判定期間）。"""

    period: EvaluationPeriod

    @property
    def axis(self) -> str:
        return self.period.axis

    @property
    def key(self) -> str:
        return self.period.key

    @property
    def axis_label(self) -> str:
        return FLOW_AXIS_LABELS.get(self.period.axis, "")

    @property
    def period_label(self) -> str:
        return self.period.label


#: メニュー画面のアラート帯・確認記録の深刻化判定で使う固定基準（低流動判定軸・3か月）。
REFERENCE_FLOW_SELECTION = FlowSelection(EvaluationPeriod(FLOW_AXIS_LOW_FLOW, DEFAULT_LOW_FLOW_VALUE))


# --- 流動区分（S-203） ---

QUADRANT_SUPPLY_RISK = "供給リスク品"
QUADRANT_DORMANT_STOCK = "在庫死蔵品"
QUADRANT_EXCESS_STOCK_RISK = "在庫過剰リスク品"
QUADRANT_NORMAL_FLOW = "通常流動品"

FLOW_QUADRANT_KEYS = {
    QUADRANT_SUPPLY_RISK: "supply-risk",
    QUADRANT_DORMANT_STOCK: "dormant-stock",
    QUADRANT_EXCESS_STOCK_RISK: "excess-stock-risk",
    QUADRANT_NORMAL_FLOW: "normal-flow",
}

FLOW_QUADRANT_LABELS = {key: label for label, key in FLOW_QUADRANT_KEYS.items()}

FLOW_QUADRANT_SORT_RANK = {
    QUADRANT_SUPPLY_RISK: 0,
    QUADRANT_DORMANT_STOCK: 1,
    QUADRANT_EXCESS_STOCK_RISK: 2,
    QUADRANT_NORMAL_FLOW: 3,
}

#: 対応の緊急度順に並べた流動区分。
FLOW_QUADRANTS = (
    QUADRANT_SUPPLY_RISK,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_EXCESS_STOCK_RISK,
    QUADRANT_NORMAL_FLOW,
)

#: 流動区分ごとの責任部署（R-201）。
RESPONSIBLE_DEPARTMENTS = {
    QUADRANT_SUPPLY_RISK: ("調達G", "営業G", "生産管理"),
    QUADRANT_DORMANT_STOCK: ("調達G",),
    QUADRANT_EXCESS_STOCK_RISK: ("営業G",),
    QUADRANT_NORMAL_FLOW: ("生産管理",),
}

#: 旧アラートレベル（別名を含む）から流動区分への互換写像（design.md §5.2）。
LEGACY_QUADRANT_ALIASES = {
    "重点": QUADRANT_SUPPLY_RISK,
    "警告（出荷なし）": QUADRANT_EXCESS_STOCK_RISK,
    "警告（入荷）": QUADRANT_EXCESS_STOCK_RISK,
    "警告（出荷あり）": QUADRANT_NORMAL_FLOW,
    "警告（出荷）": QUADRANT_NORMAL_FLOW,
    "アラート無し": QUADRANT_NORMAL_FLOW,
    "アラートなし": QUADRANT_NORMAL_FLOW,
    "なし": QUADRANT_NORMAL_FLOW,
    "問題なし": QUADRANT_NORMAL_FLOW,
}


def is_no_incoming_record(last_incoming_date: date | None) -> bool:
    """入荷実績なし（V-214）かどうか。判定期間に依存しない。"""

    return last_incoming_date is None


def is_within_evaluation_period(target: date | None, *, as_of_date: date, months: int) -> bool:
    """target が基準日から遡る判定期間に含まれるか（境界日ちょうどは含む）。"""

    if target is None:
        return False
    return target >= add_calendar_months(as_of_date, -months)


def resolve_flow_quadrant(
    last_incoming_date: date | None,
    last_ship_date: date | None,
    *,
    as_of_date: date,
    selection: FlowSelection,
) -> str:
    """期間内入荷（V-212）／期間内出荷（V-213）の有無から流動区分を決める。"""

    months = selection.period.months
    has_incoming = is_within_evaluation_period(last_incoming_date, as_of_date=as_of_date, months=months)
    has_shipment = is_within_evaluation_period(last_ship_date, as_of_date=as_of_date, months=months)
    if not has_incoming:
        return QUADRANT_SUPPLY_RISK if has_shipment else QUADRANT_DORMANT_STOCK
    return QUADRANT_NORMAL_FLOW if has_shipment else QUADRANT_EXCESS_STOCK_RISK


def resolve_flow_quadrant_matrix(
    last_incoming_date: date | None,
    last_ship_date: date | None,
    *,
    as_of_date: date,
) -> dict[str, str]:
    """判定期間6値すべてで判定し、判定期間キー → 流動区分キーの辞書を返す。"""

    return {
        period.key: FLOW_QUADRANT_KEYS[
            resolve_flow_quadrant(
                last_incoming_date,
                last_ship_date,
                as_of_date=as_of_date,
                selection=FlowSelection(period),
            )
        ]
        for period in EVALUATION_PERIODS
    }


def normalize_flow_quadrant(value: str | None) -> str:
    """流動区分ラベルを正規化する。旧アラートレベル・未知の値は安全側の通常流動品に寄せる。"""

    text = str(value or "").strip()
    if text in FLOW_QUADRANT_KEYS:
        return text
    return LEGACY_QUADRANT_ALIASES.get(text, QUADRANT_NORMAL_FLOW)


def flow_quadrant_sort_rank(quadrant: str) -> int:
    """流動区分の並び順（0 が最優先）。"""

    return FLOW_QUADRANT_SORT_RANK[normalize_flow_quadrant(quadrant)]


def responsible_departments(quadrant: str) -> tuple[str, ...]:
    """流動区分に対応する責任部署（R-201）。未知の値は空タプル。"""

    return RESPONSIBLE_DEPARTMENTS.get(quadrant, ())


def is_flow_escalated(previous: str, current: str) -> bool:
    """流動区分が前回より深刻化したか。"""

    return flow_quadrant_sort_rank(current) < flow_quadrant_sort_rank(previous)
