"""流動区分（S-203）と判定期間（V-211）のドメイン定義。

05_single-flow-view（2026-09）で判定軸（V-210）を廃止し、判定期間を 1/3/5 年に一本化した。
流動区分は 低流動品（入荷なし）/ 在庫死蔵品 / 低流動品（出荷なし）/ 通常流動品 の 4 値。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from application.inventory_order_alert.domain.value_objects.dates import add_calendar_months

# --- 判定期間（V-211） ---

#: 選択できる判定期間（年）。固定 3 値。
EVALUATION_PERIOD_YEARS = (1, 3, 5)


@dataclass(frozen=True)
class EvaluationPeriod:
    """判定期間（V-211）。入荷または出荷が止まってから「対応が必要」と判断するまでの年数。"""

    years: int

    def __post_init__(self) -> None:
        if self.years not in EVALUATION_PERIOD_YEARS:
            raise ValueError(f"判定期間は {EVALUATION_PERIOD_YEARS} 年のいずれか: {self.years}")

    @property
    def months(self) -> int:
        return self.years * 12

    @property
    def key(self) -> str:
        """事前判定行列のキー・URL 値（例: `Y3`）。"""

        return f"Y{self.years}"

    @property
    def label(self) -> str:
        return f"{self.years}年"


class EvaluationPeriods:
    """選択可能な判定期間 3 値のファーストクラスコレクション。"""

    def __init__(self, periods: tuple[EvaluationPeriod, ...]) -> None:
        self._periods = tuple(periods)

    @property
    def default(self) -> EvaluationPeriod:
        return DEFAULT_EVALUATION_PERIOD

    def find(self, key: str) -> EvaluationPeriod | None:
        for period in self._periods:
            if period.key == key:
                return period
        return None

    def find_by_years(self, years: int) -> EvaluationPeriod | None:
        for period in self._periods:
            if period.years == years:
                return period
        return None

    def __iter__(self):
        return iter(self._periods)

    def __len__(self) -> int:
        return len(self._periods)


DEFAULT_EVALUATION_PERIOD = EvaluationPeriod(1)

EVALUATION_PERIODS = EvaluationPeriods(tuple(EvaluationPeriod(years) for years in EVALUATION_PERIOD_YEARS))


@dataclass(frozen=True)
class FlowSelection:
    """利用者が選択した判定期間。"""

    period: EvaluationPeriod

    @property
    def key(self) -> str:
        return self.period.key

    @property
    def period_label(self) -> str:
        return self.period.label


#: メニュー画面のアラート帯・深刻化による未確認化（A-201）で使う固定基準（既定の判定期間 1 年）。
REFERENCE_FLOW_SELECTION = FlowSelection(DEFAULT_EVALUATION_PERIOD)


# --- 流動区分（S-203） ---

QUADRANT_LOW_FLOW_NO_INCOMING = "低流動品（入荷なし）"
QUADRANT_DORMANT_STOCK = "在庫死蔵品"
QUADRANT_LOW_FLOW_NO_SHIPMENT = "低流動品（出荷なし）"
QUADRANT_NORMAL_FLOW = "通常流動品"

#: CSS キー・URL 値・事前判定行列の値。
FLOW_QUADRANT_KEYS = {
    QUADRANT_LOW_FLOW_NO_INCOMING: "low-flow-no-incoming",
    QUADRANT_DORMANT_STOCK: "dormant-stock",
    QUADRANT_LOW_FLOW_NO_SHIPMENT: "low-flow-no-shipment",
    QUADRANT_NORMAL_FLOW: "normal-flow",
}

FLOW_QUADRANT_LABELS = {key: label for label, key in FLOW_QUADRANT_KEYS.items()}

#: ランク（深刻度・並び順）。数値が小さいほど深刻（S-203）。
FLOW_QUADRANT_SORT_RANK = {
    QUADRANT_LOW_FLOW_NO_INCOMING: 0,
    QUADRANT_DORMANT_STOCK: 1,
    QUADRANT_LOW_FLOW_NO_SHIPMENT: 2,
    QUADRANT_NORMAL_FLOW: 3,
}

#: ランク順に並べた流動区分。
FLOW_QUADRANTS = (
    QUADRANT_LOW_FLOW_NO_INCOMING,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
)

#: 責任部署（R-201）を1セルに収めるときの区切り。
RESPONSIBLE_DEPARTMENT_SEPARATOR = "・"

#: 旧称・旧キー・旧アラートレベルから流動区分への互換写像。
#: 確認記録（confirmed_flow_quadrant）・URL（flow_quadrant）・旧スナップショットの読込に用いる。
LEGACY_QUADRANT_ALIASES = {
    # 2026-09-15 までの旧称（S-203）
    "供給リスク品": QUADRANT_LOW_FLOW_NO_INCOMING,
    "在庫過剰リスク品": QUADRANT_LOW_FLOW_NO_SHIPMENT,
    # 旧 CSS キー・URL 値
    "supply-risk": QUADRANT_LOW_FLOW_NO_INCOMING,
    "excess-stock-risk": QUADRANT_LOW_FLOW_NO_SHIPMENT,
    # 旧アラートレベル（S-202）
    "重点": QUADRANT_LOW_FLOW_NO_INCOMING,
    "警告（出荷なし）": QUADRANT_LOW_FLOW_NO_SHIPMENT,
    "警告（入荷）": QUADRANT_LOW_FLOW_NO_SHIPMENT,
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
    """期間内入荷（V-212）／期間内出荷（V-213）の有無から流動区分を決める。在庫数は用いない。"""

    months = selection.period.months
    has_incoming = is_within_evaluation_period(last_incoming_date, as_of_date=as_of_date, months=months)
    has_shipment = is_within_evaluation_period(last_ship_date, as_of_date=as_of_date, months=months)
    if not has_incoming:
        return QUADRANT_LOW_FLOW_NO_INCOMING if has_shipment else QUADRANT_DORMANT_STOCK
    return QUADRANT_NORMAL_FLOW if has_shipment else QUADRANT_LOW_FLOW_NO_SHIPMENT


def resolve_flow_quadrant_matrix(
    last_incoming_date: date | None,
    last_ship_date: date | None,
    *,
    as_of_date: date,
) -> dict[str, str]:
    """判定期間 3 値すべてで判定し、判定期間キー（Y1/Y3/Y5）→ 流動区分キーの辞書を返す。"""

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
    """流動区分の値（ラベル・キー・旧称・旧アラートレベル）をラベルに正規化する。

    未知の値は安全側の通常流動品に寄せる。
    """

    text = str(value or "").strip()
    if text in FLOW_QUADRANT_KEYS:
        return text
    if text in FLOW_QUADRANT_LABELS:
        return FLOW_QUADRANT_LABELS[text]
    return LEGACY_QUADRANT_ALIASES.get(text, QUADRANT_NORMAL_FLOW)


def flow_quadrant_sort_rank(quadrant: str) -> int:
    """流動区分のランク（0 が最も深刻）。"""

    return FLOW_QUADRANT_SORT_RANK[normalize_flow_quadrant(quadrant)]


def responsible_departments(quadrant: str) -> tuple[str, ...]:
    """流動区分に対応する責任部署（R-201）。定義表は推奨アクション（T-207）に置く。未知の値は空タプル。"""

    # recommended_action は本モジュールの定数を import するため、循環を避けて関数内で読み込む。
    from application.inventory_order_alert.domain.value_objects.recommended_action import (
        DEFAULT_RECOMMENDED_ACTIONS,
    )

    if quadrant not in FLOW_QUADRANT_KEYS:
        return ()
    return DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(quadrant).departments


def format_responsible_departments(quadrant: str) -> str:
    """責任部署（R-201）を1セル・1列に収める文字列にする。"""

    return RESPONSIBLE_DEPARTMENT_SEPARATOR.join(responsible_departments(quadrant))


def is_flow_escalated(previous: str, current: str) -> bool:
    """流動区分が前回より深刻化したか（ランクが小さくなる方向）。A-201 の判定に用いる。"""

    return flow_quadrant_sort_rank(current) < flow_quadrant_sort_rank(previous)
