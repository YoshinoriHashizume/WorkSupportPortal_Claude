"""納期が基準日当日の発注残の扱い（ISSUE-0009）。

納期遅れは **納期 < 基準日**。納期が基準日当日の発注残は予定入荷（V-236）として在庫に数え、
納期確認の根拠にしない。判定（在庫切れ日）・詳細ダイアログ（予定入荷）・グラフで同じ規則にする。
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from application.inventory_order_alert.domain.value_objects.stock_projection import build_stock_projection
from application.inventory_order_alert.domain.value_objects.stock_simulation import (
    OverdueBreakdown,
    build_stock_simulation_input,
    overdue_order_breakdown,
    overdue_orders,
    planned_incoming_by_due,
)
from application.inventory_order_alert.infrastructure.oracle.summary_queries import build_planned_incoming

AS_OF = date(2026, 11, 25)
LIST_JS = Path(__file__).resolve().parents[3] / "static" / "js" / "inventory-order-alert-list.js"


def _order(order_cd: str, due: str, qty: int) -> dict[str, object]:
    return {
        "order_cd": order_cd,
        "item_cd": "ITEM-A-CKD-9000",
        "vend_cd": "9000",
        "due_date": due,
        "remaining_qty": qty,
        "updated_at": "2026/11/24",
    }


def _row(orders: list[dict[str, object]], demand: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "cust_code": "100",
        "item_cd": "ITEM-A",
        "internal_item_cd": "ITEM-A-CKD",
        "level1_item_cd": "ITEM-A-CKD-9000",
        "level1_vend_cd": "9000",
        "lead_time_days": 5,
        "lead_time_source": "master",
        "safety_stock": 0,
        "unconfirmed_order_daily": demand or [],
        "open_purchase_orders": orders,
    }


# --- 納期遅れの境界 ---


def test_order_due_on_the_base_date_is_not_overdue():
    rows = [_row([_order("PO-1", "2026/11/25", 300)])]

    assert overdue_order_breakdown(rows, as_of_date=AS_OF, stale_after_days=30) == OverdueBreakdown()
    assert overdue_orders(rows, as_of_date=AS_OF) == (0, 0)


def test_order_due_the_day_before_the_base_date_is_overdue():
    rows = [_row([_order("PO-1", "2026/11/24", 300)])]

    assert overdue_orders(rows, as_of_date=AS_OF) == (300, 1)


# --- 予定入荷（判定側） ---


def test_order_due_on_the_base_date_is_planned_incoming():
    rows = [_row([_order("PO-1", "2026/11/25", 300), _order("PO-2", "2026/11/24", 50)])]

    assert planned_incoming_by_due(rows, as_of_date=AS_OF) == {AS_OF: 300}
    movements = {movement.date: movement for movement in build_stock_simulation_input(rows, as_of_date=AS_OF, past_days=0)}
    assert movements[AS_OF].planned == 300


def test_projection_adds_todays_planned_incoming_to_the_starting_stock():
    """在庫 100・当日納期 300・12/10 に内示 120 → 在庫は切れない。"""
    rows = [_row([_order("PO-1", "2026/11/25", 300)], demand=[{"date": "2026-12-10", "qty": 120}])]

    projection = build_stock_projection(rows, as_of_date=AS_OF, stock_total=100.0, default_lead_time_days=5)

    assert projection.overdue_order_qty == 0
    assert projection.overdue_order_count == 0
    assert projection.stockout_date is None


def test_projection_still_runs_out_when_todays_incoming_is_not_enough():
    """在庫 0・当日納期 50・12/10 に内示 120 → 12/10 に切れる。"""
    rows = [_row([_order("PO-1", "2026/11/25", 50)], demand=[{"date": "2026-12-10", "qty": 120}])]

    projection = build_stock_projection(rows, as_of_date=AS_OF, stock_total=None, default_lead_time_days=5)

    assert projection.stockout_date == date(2026, 12, 10)


# --- 予定入荷（詳細ダイアログ・グラフの配信データ） ---


def test_detail_planned_incoming_includes_the_base_date():
    orders = [_order("PO-1", "2026/11/25", 300), _order("PO-2", "2026/11/24", 50), _order("PO-3", "2026/12/01", 20)]

    planned = build_planned_incoming(orders, as_of_date=AS_OF, level1_item_cd="ITEM-A-CKD-9000", level1_vend_cd="9000")

    assert planned == [{"date": "2026-11-25", "qty": 300}, {"date": "2026-12-01", "qty": 20}]


def test_chart_starts_the_future_side_with_todays_planned_incoming():
    source = LIST_JS.read_text(encoding="utf-8")
    block = source.split("// 未来側（asOf の翌日 → last）へ進む。", 1)[1].split("return past.concat(future);", 1)[0]

    assert "qty = Number(anchorQty) + (planned[asOfKey] || 0);" in block
