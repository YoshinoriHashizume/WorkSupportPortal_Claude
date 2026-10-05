"""行から流動区分（S-203）の判定材料と理由を導く（07 design §2.2）。

判定そのものは `flow_quadrant.resolve_flow_quadrant` が行う。ここは
保存済みの行（スナップショット）の値を 在庫の有無・需要の有無・直近入荷の有無 に落とし、
判定根拠を利用者向けの文言（理由）にする役目を持つ。
"""

from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.dates import parse_optional_ymd
from application.inventory_order_alert.domain.value_objects.demand_forecast import (
    BASIS_UNCONFIRMED,
    FORECAST_MONTHS,
)
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    DEFAULT_FLOW_THRESHOLDS,
    QUADRANT_DISCONTINUATION_CANDIDATE,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_STOCKOUT,
    QUADRANT_STOCKOUT_NO_INCOMING,
    REFERENCE_FLOW_SELECTION,
    FlowFacts,
    FlowSelection,
    FlowThresholds,
    is_recent_incoming,
    is_within_evaluation_period,
)
from application.inventory_order_alert.domain.value_objects.stock_quantity import is_stock_fetched

#: 理由（REQ-FQR-F-005）。表示文言そのもの。
FLOW_REASON_NO_INCOMING_RECORD = "入荷の記録なし・経路要確認"
#: 期間にかかわる理由は判定期間（V-211）で判断する（用語集 V-211「期間判断の基準」）。`{period}` は表示中のラベル。
FLOW_REASON_NO_SHIPMENT_IN_PERIOD = "{period}以上出荷なし・経路要確認"
FLOW_REASON_INCOMING_BELOW_DEMAND = "入荷 < 需要"
FLOW_REASON_UNCONFIRMED_WITHOUT_SHIPMENT = "内示あり（立ち上がり／出荷経路要確認）"


def _row_date(row: dict[str, object], key: str) -> date | None:
    """行の日付文字列を date に直す。空・解析不能はいずれも None。"""
    text = str(row.get(key) or "").strip()
    if not text:
        return None
    try:
        return parse_optional_ymd(text)
    except ValueError:
        return None


def _trend_qtys(trend: object) -> list[int]:
    if not isinstance(trend, list):
        return []
    qtys: list[int] = []
    for point in trend:
        try:
            qtys.append(int((point or {}).get("qty") or 0))
        except (TypeError, ValueError, AttributeError):
            qtys.append(0)
    return qtys


def row_stock_missing(row: dict[str, object]) -> bool:
    """SLIMS 在庫なし（T-209/T-210）か。

    行の在庫数が「該当なし」（空文字）で、かつ照合単位（T-208）の在庫合計も 0 以下のときだけ真。
    在庫数のキーがない旧行は未取得（`－`）なので偽、`0` は SLIMS に行があり在庫ゼロなので偽（在庫あり扱い）。
    """
    if not is_stock_fetched(row, "stock_qty"):
        return False
    if str(row.get("stock_qty") or "").strip():
        return False
    total = row.get("demand_forecast_stock_total")
    if total is None or total == "":
        return True
    try:
        return float(total) <= 0
    except (TypeError, ValueError):
        return True


def row_has_demand(row: dict[str, object]) -> bool:
    """需要あり（内示推移 V-219 に数量がある）か。出荷実績は見ない（REQ-FQR-F-002）。

    需要予測（V-220）が付いた行はその算出根拠を、付く前の行は内示推移の翌月〜翌々々月を見る。
    """
    if "demand_forecast_basis" in row:
        return str(row.get("demand_forecast_basis") or "") == BASIS_UNCONFIRMED
    return any(qty > 0 for qty in _trend_qtys(row.get("unconfirmed_order_trend"))[1 : FORECAST_MONTHS + 1])


def row_recent_incoming(row: dict[str, object], *, as_of_date: date, days: int) -> bool:
    """直近入荷あり（T-209）か。"""
    return is_recent_incoming(_row_date(row, "last_incoming_date"), as_of_date=as_of_date, days=days)


def row_last_incoming_month_qty(row: dict[str, object], *, as_of_date: date) -> int:
    """最終入荷日（V-215）が属する月の入荷推移（V-217）の合計。

    入荷推移は月次の合計しか持たず「直近 30 日」を日単位で切り出せないため、
    直近に入荷があった月の実績で代表する（REQ-FQR-F-005、2026/09/21 確定）。
    """
    _ = as_of_date
    last_incoming = _row_date(row, "last_incoming_date")
    if last_incoming is None:
        return 0
    month_key = f"{last_incoming.year:04d}-{last_incoming.month:02d}"
    trend = row.get("incoming_trend")
    if not isinstance(trend, list):
        return 0
    total = 0
    for point in trend:
        if not isinstance(point, dict) or str(point.get("month") or "") != month_key:
            continue
        try:
            total += int(point.get("qty") or 0)
        except (TypeError, ValueError):
            continue
    return total


def row_next_month_demand(row: dict[str, object]) -> int:
    """翌月の内示（需要予測 V-220 の `monthly` の先頭）。算出根拠が内示でなければ 0。"""
    if str(row.get("demand_forecast_basis") or "") != BASIS_UNCONFIRMED:
        return 0
    monthly = _trend_monthly(row.get("demand_forecast_monthly"))
    return monthly[0] if monthly else 0


def _trend_monthly(monthly: object) -> list[int]:
    if not isinstance(monthly, list):
        return []
    values: list[int] = []
    for qty in monthly:
        try:
            values.append(int(qty or 0))
        except (TypeError, ValueError):
            values.append(0)
    return values


def build_flow_facts(
    row: dict[str, object],
    *,
    as_of_date: date,
    thresholds: FlowThresholds = DEFAULT_FLOW_THRESHOLDS,
) -> FlowFacts:
    """行から判定材料を組み立てる。"""
    return FlowFacts(
        last_incoming_date=_row_date(row, "last_incoming_date"),
        last_ship_date=_row_date(row, "last_ship_date"),
        stock_missing=row_stock_missing(row),
        has_demand=row_has_demand(row),
        recent_incoming=row_recent_incoming(row, as_of_date=as_of_date, days=thresholds.recent_incoming_days),
    )


def format_phase_out_reason(phase_out_date: date) -> str:
    """打ち切り候補の理由（適用終了日）。"""
    return f"適用終了日 {phase_out_date.strftime('%Y/%m/%d')}"


def flow_reasons(
    row: dict[str, object],
    quadrant: str,
    facts: FlowFacts,
    *,
    as_of_date: date,
    selection: FlowSelection = REFERENCE_FLOW_SELECTION,
) -> list[str]:
    """流動区分の判定根拠（REQ-FQR-F-005）。該当がなければ空。

    期間にかかわる判断は判定期間（`selection`）で行う（用語集 V-211「期間判断の基準」）。
    区分が判定期間で変わるため、理由も期間ごとに組み立てる（07 design §1-6）。
    """
    reasons: list[str] = []
    if quadrant == QUADRANT_STOCKOUT_NO_INCOMING and facts.last_incoming_date is None:
        reasons.append(FLOW_REASON_NO_INCOMING_RECORD)
    if quadrant in (QUADRANT_STOCKOUT, QUADRANT_STOCKOUT_NO_INCOMING) and not is_within_evaluation_period(
        facts.last_ship_date, as_of_date=as_of_date, months=selection.period.months
    ):
        # 入荷はあるのに期間内に出荷がない＝出荷が基幹に記録されない経路の疑い（最終出荷日が空も含む）
        reasons.append(FLOW_REASON_NO_SHIPMENT_IN_PERIOD.replace("{period}", selection.period.label))
    if quadrant == QUADRANT_STOCKOUT:
        next_month_demand = row_next_month_demand(row)
        if next_month_demand > 0 and row_last_incoming_month_qty(row, as_of_date=as_of_date) < next_month_demand:
            reasons.append(FLOW_REASON_INCOMING_BELOW_DEMAND)
    if quadrant == QUADRANT_LOW_FLOW_NO_SHIPMENT and row_has_demand(row):
        reasons.append(FLOW_REASON_UNCONFIRMED_WITHOUT_SHIPMENT)
    if quadrant == QUADRANT_DISCONTINUATION_CANDIDATE:
        phase_out = _row_date(row, "phase_out_date")
        if phase_out is not None and phase_out < as_of_date:
            reasons.append(format_phase_out_reason(phase_out))
    return reasons
