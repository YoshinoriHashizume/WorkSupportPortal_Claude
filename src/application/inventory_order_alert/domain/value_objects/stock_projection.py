"""日次の在庫見通し（08 design §2.1）。

照合単位（T-208）の在庫合計を起点に、内示（V-219）を所要日ごとに引き、
納期が基準日より後の発注残（V-224）を納期の日に足して、在庫の動きを 1 日ずつ追う。

  その日の在庫 ＝ 前日の在庫 − その日の内示 ＋ その日に届く予定入荷

ここから 在庫切れ日（V-232）・発注期限（V-233）・安全在庫割れ を求める。
月平均需要による予測の延長は行わない（内示のある範囲だけで判断する。REQ-SRR-F-001）。
納期遅れの発注残は**来ないものとして加算しない**が、件数と数量は持つ（REQ-SRR-F-002）。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta

from application.inventory_order_alert.domain.value_objects.ordering_profile import (
    LEAD_TIME_SOURCE_DEFAULT,
    LEAD_TIME_SOURCE_MASTER,
)
from application.inventory_order_alert.domain.value_objects.stock_simulation import (
    DailyMovement,
    build_stock_simulation_input,
    overdue_orders,
)

#: リードタイムの既定値（設定から渡す。ここは引数の既定値のみ）
DEFAULT_LEAD_TIME_DAYS = 5


@dataclass(frozen=True)
class DailyStockProjection:
    """照合単位 1 つぶんの日次の見通し。"""

    has_demand: bool = False
    stockout_date: date | None = None
    order_deadline: date | None = None
    below_safety_stock: bool = False
    safety_stock: float = 0.0
    overdue_order_qty: int = 0
    overdue_order_count: int = 0
    lead_time_days: int = DEFAULT_LEAD_TIME_DAYS
    lead_time_source: str = LEAD_TIME_SOURCE_DEFAULT


def _parse_date(value: object) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return parse_optional_ymd(text)
    except (ValueError, TypeError):
        return None


def _as_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _as_float(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _daily_demand(unit_rows: list[dict[str, object]], *, as_of_date: date) -> Counter:
    """内示を日ごとに合算する（在庫シミュレーション V-237 と同じ材料。09 design §2.2）。"""
    return Counter(
        {movement.date: movement.demand for movement in _future_movements(unit_rows, as_of_date) if movement.demand}
    )


def _planned_and_overdue(unit_rows: list[dict[str, object]], *, as_of_date: date) -> tuple[Counter, int, int]:
    """納期が基準日より後の予定入荷と、納期遅れの合計（在庫シミュレーションと同じ材料）。"""
    planned = Counter(
        {movement.date: movement.planned for movement in _future_movements(unit_rows, as_of_date) if movement.planned}
    )
    overdue_qty, overdue_count = overdue_orders(unit_rows, as_of_date=as_of_date)
    return planned, overdue_qty, overdue_count


def _future_movements(unit_rows: list[dict[str, object]], as_of_date: date) -> list[DailyMovement]:
    """未来側（基準日より後）の動きだけを組み立てる。判定と描画で材料を共有する（09 design §1）。"""
    return build_stock_simulation_input(unit_rows, as_of_date=as_of_date, past_days=0)


def _safety_stock_of(unit_rows: list[dict[str, object]]) -> float:
    """内作品番の重複を除いて安全在庫（V-231）を合算する。"""
    total = 0.0
    seen: set[str] = set()
    for row in unit_rows:
        internal = str(row.get("internal_item_cd") or "").strip()
        if not internal or internal in seen:
            continue
        seen.add(internal)
        total += _as_float(row.get("safety_stock"))
    return total


def _lead_time_of(unit_rows: list[dict[str, object]], *, default_days: int) -> tuple[int, str]:
    """照合単位のリードタイム。単位内で最も長いものを採り、未設定があれば既定値で補う。"""
    longest = 0
    source = LEAD_TIME_SOURCE_MASTER
    for row in unit_rows:
        days = _as_int(row.get("lead_time_days"))
        if days <= 0 or str(row.get("lead_time_source") or "") == LEAD_TIME_SOURCE_DEFAULT:
            source = LEAD_TIME_SOURCE_DEFAULT
            days = max(days, default_days)
        longest = max(longest, days)
    if longest <= 0:
        return default_days, LEAD_TIME_SOURCE_DEFAULT
    return longest, source


def build_stock_projection(
    unit_rows: list[dict[str, object]],
    *,
    as_of_date: date,
    stock_total: float | None,
    default_lead_time_days: int = DEFAULT_LEAD_TIME_DAYS,
) -> DailyStockProjection:
    """照合単位の行から日次の見通しを組み立てる。例外は投げない（REQ-SRR-NF-003）。"""
    lead_time_days, lead_time_source = _lead_time_of(unit_rows, default_days=default_lead_time_days)
    safety_stock = _safety_stock_of(unit_rows)
    planned, overdue_qty, overdue_count = _planned_and_overdue(unit_rows, as_of_date=as_of_date)
    demand = _daily_demand(unit_rows, as_of_date=as_of_date)

    base = DailyStockProjection(
        has_demand=bool(demand),
        safety_stock=safety_stock,
        overdue_order_qty=overdue_qty,
        overdue_order_count=overdue_count,
        lead_time_days=lead_time_days,
        lead_time_source=lead_time_source,
    )
    if not demand:
        # 内示がなければ在庫は動かない（REQ-SRR-F-001）
        return base

    # 在庫が未取得の行は 0 として計算する（REQ-SRR-F-002）
    stock = 0.0 if stock_total is None else float(stock_total)
    last_day = max(max(demand), max(planned) if planned else as_of_date)
    stockout_date: date | None = None
    below_safety = False

    day = as_of_date + timedelta(days=1)
    while day <= last_day:
        stock = stock - demand.get(day, 0) + planned.get(day, 0)
        if stockout_date is None and stock < 0:
            stockout_date = day
        if safety_stock > 0 and stock < safety_stock:
            below_safety = True
        day += timedelta(days=1)

    order_deadline = stockout_date - timedelta(days=lead_time_days) if stockout_date else None
    return DailyStockProjection(
        has_demand=True,
        stockout_date=stockout_date,
        order_deadline=order_deadline,
        below_safety_stock=below_safety,
        safety_stock=safety_stock,
        overdue_order_qty=overdue_qty,
        overdue_order_count=overdue_count,
        lead_time_days=lead_time_days,
        lead_time_source=lead_time_source,
    )
