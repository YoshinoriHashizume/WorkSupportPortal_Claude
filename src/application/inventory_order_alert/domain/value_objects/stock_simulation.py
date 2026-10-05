"""在庫シミュレーション（V-237）の材料となる日次の動き（09 design §2.1）。

照合単位（T-208）の行から、**クライアントが累積するだけで描ける形**に組み立てる。
重複除去と完成品直下の工程の絞り込みはここで済ませ、JS には累積和しか置かない
（判定ロジックを JS に持ち込まない。spec/05 NF-005）。

  過去側（基準日の past_days 前 〜 基準日）  … 日次出荷（V-234）・日次入荷（V-235）
  未来側（基準日の翌日 〜 内示・予定入荷の最終日）… 内示（V-219）・予定入荷（V-236）

在庫切れ日（V-232）は、この未来側を累積して初めて 0 未満になる日と一致する。
判定（stock_projection.py）と描画が同じ配列を読むことで、グラフの線と一覧の
在庫切れ日・発注期限が食い違わないようにする（09 design §1）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from application.inventory_order_alert.domain.value_objects.dates import parse_optional_ymd
from application.inventory_order_alert.domain.value_objects.unconfirmed_order_trend import unconfirmed_order_window_end

#: 在庫シミュレーションが遡る日数（REQ-SSC-F-002）。
PAST_DAYS_FOR_SIMULATION = 30


def simulation_range(as_of_date: date) -> tuple[date, date]:
    """在庫シミュレーション（V-237）の範囲: 基準日の 1 か月前 〜 翌々々月末（REQ-SSC-F-002）。

    **品目によって端が変わらないよう固定する**（軸を揃えて見比べられるようにするため。
    2026-09-29 ユーザー判断）。動きのない日も前日の値を引き継いだ水平線として描く。
    """
    return as_of_date - timedelta(days=PAST_DAYS_FOR_SIMULATION), unconfirmed_order_window_end(as_of_date) - timedelta(days=1)


@dataclass(frozen=True)
class DailyMovement:
    """1 日ぶんの在庫の動き。"""

    date: date
    #: 実績（過去側）
    ship: int = 0
    incoming: int = 0
    #: 見通し（未来側）
    demand: int = 0
    planned: int = 0


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


def _sparse_series(
    unit_rows: list[dict[str, object]],
    *,
    key: str,
    pair_keys: tuple[str, ...],
    keep: "callable[[date], bool]",
) -> dict[date, int]:
    """行が持つ疎な配列を、`pair_keys` の重複を除いて日ごとに合算する。"""
    totals: dict[date, int] = {}
    seen: set[tuple[str, ...]] = set()
    for row in unit_rows:
        pair = tuple(str(row.get(name) or "").strip() for name in pair_keys)
        if pair in seen:
            continue
        seen.add(pair)
        entries = row.get(key)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            day = _parse_date(entry.get("date"))
            qty = _as_int(entry.get("qty"))
            if day is not None and qty > 0 and keep(day):
                totals[day] = totals.get(day, 0) + qty
    return totals


def planned_incoming_by_due(unit_rows: list[dict[str, object]], *, as_of_date: date) -> dict[date, int]:
    """予定入荷（V-236）: 納期が基準日より後の発注残を、発注番号の重複を除いて納期ごとに合算する。

    対象は完成品直下の工程（`level1_item_cd` × `level1_vend_cd`）のみ。
    納期が基準日以前（納期遅れ）のものは**来ないもの**として含めない。
    """
    planned: dict[date, int] = {}
    seen: set[str] = set()
    for row in unit_rows:
        level1 = (str(row.get("level1_item_cd") or "").strip(), str(row.get("level1_vend_cd") or "").strip())
        orders = row.get("open_purchase_orders")
        if not isinstance(orders, list):
            continue
        for order in orders:
            if not isinstance(order, dict):
                continue
            if (str(order.get("item_cd") or "").strip(), str(order.get("vend_cd") or "").strip()) != level1:
                continue
            order_cd = str(order.get("order_cd") or "").strip()
            if not order_cd or order_cd in seen:
                continue
            seen.add(order_cd)
            due = _parse_date(order.get("due_date"))
            qty = _as_int(order.get("remaining_qty"))
            if due is not None and qty > 0 and due > as_of_date:
                planned[due] = planned.get(due, 0) + qty
    return planned


def overdue_orders(unit_rows: list[dict[str, object]], *, as_of_date: date) -> tuple[int, int]:
    """納期遅れの発注残の (数量合計, 件数)。在庫の計算には加算しない（REQ-SRR-F-002）。"""
    total = 0
    count = 0
    seen: set[str] = set()
    for row in unit_rows:
        level1 = (str(row.get("level1_item_cd") or "").strip(), str(row.get("level1_vend_cd") or "").strip())
        orders = row.get("open_purchase_orders")
        if not isinstance(orders, list):
            continue
        for order in orders:
            if not isinstance(order, dict):
                continue
            if (str(order.get("item_cd") or "").strip(), str(order.get("vend_cd") or "").strip()) != level1:
                continue
            order_cd = str(order.get("order_cd") or "").strip()
            if not order_cd or order_cd in seen:
                continue
            seen.add(order_cd)
            due = _parse_date(order.get("due_date"))
            qty = _as_int(order.get("remaining_qty"))
            if due is not None and qty > 0 and due <= as_of_date:
                total += qty
                count += 1
    return total, count


def build_stock_simulation_input(
    unit_rows: list[dict[str, object]],
    *,
    as_of_date: date,
    past_days: int = PAST_DAYS_FOR_SIMULATION,
) -> list[DailyMovement]:
    """照合単位の行から日次の動きを組み立てる。例外は投げない。

    `past_days=0` なら未来側だけを返す（`build_stock_projection` の呼び方）。
    """
    window_start = as_of_date - timedelta(days=past_days)

    ship = (
        _sparse_series(
            unit_rows,
            key="daily_shipment",
            pair_keys=("cust_code", "item_cd"),
            keep=lambda day: window_start <= day <= as_of_date,
        )
        if past_days > 0
        else {}
    )
    incoming = (
        _sparse_series(
            unit_rows,
            key="daily_incoming",
            pair_keys=("level1_item_cd", "level1_vend_cd"),
            keep=lambda day: window_start <= day <= as_of_date,
        )
        if past_days > 0
        else {}
    )
    demand = _sparse_series(
        unit_rows,
        key="unconfirmed_order_daily",
        pair_keys=("cust_code", "internal_item_cd"),
        keep=lambda day: day > as_of_date,
    )
    planned = planned_incoming_by_due(unit_rows, as_of_date=as_of_date)

    days = sorted(set(ship) | set(incoming) | set(demand) | set(planned))
    return [
        DailyMovement(
            date=day,
            ship=ship.get(day, 0),
            incoming=incoming.get(day, 0),
            demand=demand.get(day, 0),
            planned=planned.get(day, 0),
        )
        for day in days
    ]
