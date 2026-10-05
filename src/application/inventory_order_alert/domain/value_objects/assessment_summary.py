"""判定サマリ（T-211。10 design §2.1）。

詳細ダイアログの先頭で「この品番の在庫は切れるのか、切れないのか」に**一文で答える**。
対応区分（S-204）・在庫切れ日（V-232）・発注期限（V-233）・理由を読み替えるだけで、
**新しい判定は行わない**（REQ-DDC-NF-001）。

文言を domain に置くのは、判定と言い回しを 1 か所に保つため。JS では文言を組み立てない
（REQ-DDC-NF-003。spec/05 NF-005 と同じ方針）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from application.inventory_order_alert.domain.value_objects.dates import parse_optional_ymd
from application.inventory_order_alert.domain.value_objects.stockout_risk import (
    RESPONSE_DELIVERY_CHECK,
    RESPONSE_NONE,
    RESPONSE_ORDER_NEEDED,
    RESPONSE_ORDER_OVERDUE,
    RESPONSE_WATCH,
    row_response_class,
)

#: 対応区分ごとの「次にすること」。流動区分由来の推奨アクション（T-207）とは別のもの。
NEXT_ACTIONS: dict[str, str] = {
    RESPONSE_ORDER_OVERDUE: "生産管理: 至急手配し、客先へ納期を調整する",
    RESPONSE_DELIVERY_CHECK: "購買: 仕入先へ納期を確認する",
    RESPONSE_ORDER_NEEDED: "生産管理: 発注期限までに発注する",
    RESPONSE_WATCH: "生産管理: 様子を見る",
    RESPONSE_NONE: "対応不要",
}

HEADLINE_NO_STOCKOUT = "在庫は切れません"


@dataclass(frozen=True)
class AssessmentSummary:
    """詳細ダイアログ先頭の結論。"""

    headline: str
    response_class: str
    next_action: str
    #: 「2026/10/05（あと 5 日）」。在庫切れ日がなければ空
    deadline_text: str
    reasons: tuple[str, ...] = ()


def _parse(value: object) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return parse_optional_ymd(text)
    except (ValueError, TypeError):
        return None


def _qty(value: object) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return "0"
    return f"{int(number):,}" if number.is_integer() else f"{number:,.1f}"


def _as_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _deadline_text(row: dict[str, object], *, as_of_date: date) -> str:
    """発注期限と、基準日からの残り日数。在庫切れ日がなければ空。"""
    deadline_raw = str(row.get("order_deadline") or "").strip()
    if not deadline_raw:
        return ""
    deadline = _parse(deadline_raw)
    if deadline is None:
        return deadline_raw
    days = (deadline - as_of_date).days
    if days > 0:
        return f"{deadline_raw}（あと {days} 日）"
    if days == 0:
        return f"{deadline_raw}（本日）"
    return f"{deadline_raw}（{-days} 日超過）"


def build_assessment_summary(row: dict[str, object], *, as_of_date: date) -> AssessmentSummary:
    """行の判定値から判定サマリを組み立てる。例外は投げない。"""
    response_class = row_response_class(row)
    stockout_raw = str(row.get("stockout_date") or "").strip()
    deadline_raw = str(row.get("order_deadline") or "").strip()
    reasons = tuple(str(reason) for reason in (row.get("response_reasons") or []))

    overdue_text = f"納期遅れの発注残 {_as_int(row.get('overdue_order_count'))} 件 {_qty(row.get('overdue_order_qty'))} 個"

    if response_class in (RESPONSE_ORDER_OVERDUE, RESPONSE_ORDER_NEEDED) and stockout_raw:
        if response_class == RESPONSE_ORDER_OVERDUE:
            headline = f"この品番は {stockout_raw} に在庫が切れます。発注期限 {deadline_raw} は過ぎています"
        else:
            headline = f"この品番は {stockout_raw} に在庫が切れます。{deadline_raw} までに発注が必要です"
    elif response_class == RESPONSE_DELIVERY_CHECK:
        # 納期確認は「切れる かつ 納期遅れあり」でも起きる（S-204 のマトリクス）。
        # 一律に「在庫は足ります」とすると事実と逆になるため、在庫切れ日の有無で分ける（2026-09-30 修正）
        if stockout_raw:
            headline = (
                f"この品番は {stockout_raw} に在庫が切れます。{deadline_raw} までに発注が必要です。"
                f"あわせて{overdue_text}の納期を確認してください"
            )
        else:
            headline = f"在庫は足ります。ただし{overdue_text}があります"
    elif response_class == RESPONSE_WATCH:
        headline = f"在庫は切れませんが、安全在庫 {_qty(row.get('safety_stock'))} を下回ります"
    else:
        # 対象外、および「在庫切れ日が無いのに 発注遅れ / 要発注」という起こらないはずの組み合わせ（安全側）
        headline = HEADLINE_NO_STOCKOUT

    return AssessmentSummary(
        headline=headline,
        response_class=response_class,
        next_action=NEXT_ACTIONS.get(response_class, NEXT_ACTIONS[RESPONSE_NONE]),
        deadline_text=_deadline_text(row, as_of_date=as_of_date) if stockout_raw else "",
        reasons=reasons,
    )
