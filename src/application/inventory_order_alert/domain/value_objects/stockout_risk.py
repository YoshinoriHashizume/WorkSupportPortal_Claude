"""対応区分（S-204）の判定（08 design §2.2）。

目的は「お客さんの納期どおりに納める＝在庫切れを起こさない」。
日次の在庫見通し（V-232 在庫切れ日 / V-233 発注期限 / V-231 安全在庫割れ）と
納期遅れの発注残から、**次にすべき行動**を 5 区分で示す。判定は取込時に行い保存する。

2026/09/23 改訂（spec/08_stockout-risk-rework）: 「在庫切れリスク（危険/注意/監視/対象外）」から
全面改訂した。月平均需要による予測の延長、猶予日数・補充見込み・補充期限・長期納期超過・
安全日数・監視期間は撤去し、内示のある範囲だけを日次で追う形にした。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from application.inventory_order_alert.domain.value_objects.ordering_profile import LEAD_TIME_SOURCE_DEFAULT
from application.inventory_order_alert.domain.value_objects.reconciliation_unit import ReconciliationUnits
from application.inventory_order_alert.domain.value_objects.stock_projection import (
    DEFAULT_LEAD_TIME_DAYS,
    DailyStockProjection,
    build_stock_projection,
)

# --- 対応区分（S-204） ---

RESPONSE_ORDER_OVERDUE = "発注遅れ"
RESPONSE_DELIVERY_CHECK = "納期確認"
RESPONSE_ORDER_NEEDED = "要発注"
RESPONSE_WATCH = "要監視"
RESPONSE_NONE = "対象外"

#: ランク順（数値が小さいほど急ぐ）。
RESPONSE_CLASS_RANK = {
    RESPONSE_ORDER_OVERDUE: 0,
    RESPONSE_DELIVERY_CHECK: 1,
    RESPONSE_ORDER_NEEDED: 2,
    RESPONSE_WATCH: 3,
    RESPONSE_NONE: 4,
}
RESPONSE_CLASSES = tuple(sorted(RESPONSE_CLASS_RANK, key=RESPONSE_CLASS_RANK.__getitem__))

#: CSS キー・URL 値。
RESPONSE_CLASS_KEYS = {
    RESPONSE_ORDER_OVERDUE: "order-overdue",
    RESPONSE_DELIVERY_CHECK: "delivery-check",
    RESPONSE_ORDER_NEEDED: "order-needed",
    RESPONSE_WATCH: "watch",
    RESPONSE_NONE: "none",
}
RESPONSE_CLASS_LABELS = {key: label for label, key in RESPONSE_CLASS_KEYS.items()}

#: 2026-09-23 までの旧称「在庫切れリスク」からの写像（REQ-SRR-F-008）。確認記録・旧スナップショットの読込に使う。
LEGACY_RESPONSE_CLASS_ALIASES = {
    "危険": RESPONSE_ORDER_OVERDUE,
    "注意": RESPONSE_ORDER_NEEDED,
    "監視": RESPONSE_WATCH,
    "対象外": RESPONSE_NONE,
    "danger": RESPONSE_ORDER_OVERDUE,
    "caution": RESPONSE_ORDER_NEEDED,
    "watch": RESPONSE_WATCH,
    "none": RESPONSE_NONE,
}


@dataclass(frozen=True)
class ResponseAssessment:
    response_class: str
    reasons: tuple[str, ...]
    projection: DailyStockProjection

    @property
    def key(self) -> str:
        return RESPONSE_CLASS_KEYS[self.response_class]


def _format_date(value: date | None) -> str:
    return value.strftime("%Y/%m/%d") if value else ""


def _format_qty(value: float) -> str:
    return f"{int(value):,}" if float(value).is_integer() else f"{value:,.1f}"


def assess_response_class(projection: DailyStockProjection, *, as_of_date: date) -> ResponseAssessment:
    """対応区分と理由を決める（REQ-SRR-F-004/005）。

    2 軸（在庫の見通し × 納期遅れの発注残）の組み合わせで決まるため、分岐の順番に依存しない。
    """
    overdue = projection.overdue_order_qty > 0

    if projection.stockout_date is not None:
        deadline = projection.order_deadline
        if deadline is not None and deadline <= as_of_date:
            response_class = RESPONSE_ORDER_OVERDUE
        else:
            response_class = RESPONSE_DELIVERY_CHECK if overdue else RESPONSE_ORDER_NEEDED
    elif overdue:
        response_class = RESPONSE_DELIVERY_CHECK
    elif projection.below_safety_stock:
        response_class = RESPONSE_WATCH
    else:
        response_class = RESPONSE_NONE

    reasons: list[str] = []
    if projection.stockout_date is not None:
        reasons.append(f"在庫切れ {_format_date(projection.stockout_date)}")
        if projection.order_deadline is not None:
            reasons.append(f"発注期限 {_format_date(projection.order_deadline)}")
    if overdue:
        reasons.append(f"納期遅れの発注残 {projection.overdue_order_count} 件 {_format_qty(projection.overdue_order_qty)} 個")
    if projection.below_safety_stock:
        reasons.append(f"安全在庫 {_format_qty(projection.safety_stock)} を下回る")
    if projection.stockout_date is not None and projection.lead_time_source == LEAD_TIME_SOURCE_DEFAULT:
        reasons.append("リードタイム未設定")
    if not projection.has_demand:
        reasons.append("内示なし（在庫は動かない）")
    return ResponseAssessment(response_class, tuple(reasons), projection)


def normalize_response_class(value: object) -> str:
    """区分名・キー・旧称を対応区分に正規化する。未知の値は対象外（安全側）。"""
    text = str(value or "").strip()
    if text in RESPONSE_CLASS_RANK:
        return text
    if text in RESPONSE_CLASS_LABELS:
        return RESPONSE_CLASS_LABELS[text]
    return LEGACY_RESPONSE_CLASS_ALIASES.get(text, RESPONSE_NONE)


def row_response_class(row: dict[str, object]) -> str:
    """行の対応区分。旧スナップショット（`stockout_risk` しかない行）も読む。"""
    value = row.get("response_class")
    if value is None:
        value = row.get("stockout_risk")
    return normalize_response_class(value)


def response_class_sort_rank(row: dict[str, object]) -> int:
    return RESPONSE_CLASS_RANK[row_response_class(row)]


def _assessment_fields(assessment: ResponseAssessment) -> dict[str, object]:
    projection = assessment.projection
    return {
        "response_class": assessment.response_class,
        "response_class_key": assessment.key,
        "response_reasons": list(assessment.reasons),
        "stockout_date": _format_date(projection.stockout_date),
        "order_deadline": _format_date(projection.order_deadline),
        "below_safety_stock": projection.below_safety_stock,
        "safety_stock": projection.safety_stock,
        "overdue_order_qty": projection.overdue_order_qty,
        "overdue_order_count": projection.overdue_order_count,
        "lead_time_days": projection.lead_time_days,
        "lead_time_source": projection.lead_time_source,
    }


def _stock_total_of(row: dict[str, object]) -> float | None:
    value = row.get("demand_forecast_stock_total")
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def attach_response_class(
    rows: list[dict[str, object]],
    as_of_date: date,
    *,
    default_lead_time_days: int = DEFAULT_LEAD_TIME_DAYS,
) -> list[dict[str, object]]:
    """照合単位ごとに 1 回判定し、単位内の全行に複製する（入力は変更しない）。"""
    units = ReconciliationUnits.build(rows)
    cache: dict[str, dict[str, object]] = {}
    enriched: list[dict[str, object]] = []

    for row in rows:
        copied = dict(row)
        unit = units.unit_of(str(row.get("item_cd") or ""))
        if unit is None:
            # 得意先品番が空の行は照合単位に属さない。行単体で見る
            projection = build_stock_projection(
                [row], as_of_date=as_of_date, stock_total=_stock_total_of(row), default_lead_time_days=default_lead_time_days
            )
            copied.update(_assessment_fields(assess_response_class(projection, as_of_date=as_of_date)))
            enriched.append(copied)
            continue
        if unit.key not in cache:
            unit_rows = units.rows_of(unit, rows)
            projection = build_stock_projection(
                unit_rows,
                as_of_date=as_of_date,
                stock_total=_stock_total_of(row),
                default_lead_time_days=default_lead_time_days,
            )
            cache[unit.key] = _assessment_fields(assess_response_class(projection, as_of_date=as_of_date))
        copied.update(cache[unit.key])
        enriched.append(copied)
    return enriched
