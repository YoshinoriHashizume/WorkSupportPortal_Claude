"""発注残（V-224）の読み取りのテスト（TC-SOR-D-004〜006b）。

2026/09/23（spec/08_stockout-risk-rework）: 補充見込み（V-226）・補充期限（V-229）・
長期納期超過（V-230）を撤去したため、それらのテストも外した。納期での振り分け
（基準日より後は来る／納期遅れは来ない）は `test_stock_projection.py` が見る。
"""

from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.open_purchase_order import (
    OpenPurchaseOrder,
    open_purchase_orders_from_rows,
)


def _po(due: date | None, qty: int, item_cd: str = "X-9065", vend_cd: str = "9065") -> OpenPurchaseOrder:
    return OpenPurchaseOrder(item_cd=item_cd, vend_cd=vend_cd, due_date=due, remaining_qty=qty)


def test_d004_negative_remaining_is_zero():
    assert _po(date(2026, 10, 5), -5).remaining_qty == 0


def test_d006_duplicate_lines_from_multiple_rows_are_counted_once():
    """同じ発注明細（同じ order_cd）が照合単位の複数行に付いていても 1 回だけ数える。"""
    rows = [
        {"open_purchase_orders": [{"order_cd": "PO-1", "item_cd": "X-9065", "vend_cd": "9065", "due_date": "2026/10/05", "remaining_qty": 100}]},
        {"open_purchase_orders": [{"order_cd": "PO-1", "item_cd": "X-9065", "vend_cd": "9065", "due_date": "2026/10/05", "remaining_qty": 100}]},
        {"open_purchase_orders": [{"order_cd": "PO-2", "item_cd": "Y-9209", "vend_cd": "9209", "due_date": "2026/11/01", "remaining_qty": 7}]},
        {},
    ]

    orders = open_purchase_orders_from_rows(rows)

    assert sorted((o.order_cd, o.item_cd, o.remaining_qty) for o in orders) == [("PO-1", "X-9065", 100), ("PO-2", "Y-9209", 7)]


def test_d006a_distinct_orders_with_same_item_due_and_qty_are_all_counted():
    """同品番・同仕入先・同納期・同数量でも order_cd が違えば別明細（カンバン式の分割発注。2026/09/18 レビュー指摘）。"""
    line = {"item_cd": "X-9065", "vend_cd": "9065", "due_date": "2026/10/05", "remaining_qty": 20}
    rows = [
        {"open_purchase_orders": [{"order_cd": f"PO-{n}", **line} for n in range(1, 4)]},
        {"open_purchase_orders": [{"order_cd": f"PO-{n}", **line} for n in range(1, 4)]},
    ]

    orders = open_purchase_orders_from_rows(rows)

    assert len(orders) == 3
    assert sum(order.remaining_qty for order in orders) == 60


def test_d006b_rows_without_order_cd_fall_back_to_legacy_key():
    """旧スナップショット（order_cd なし）は従来の (品番, 仕入先, 納期, 数量) で重複を除く。"""
    legacy = {"item_cd": "X-9065", "vend_cd": "9065", "due_date": "2026/10/05", "remaining_qty": 100}
    rows = [{"open_purchase_orders": [legacy]}, {"open_purchase_orders": [dict(legacy)]}]

    orders = open_purchase_orders_from_rows(rows)

    assert len(orders) == 1
    assert orders[0].order_cd == ""


def test_open_purchase_orders_from_rows_tolerates_bad_values():
    rows = [{"open_purchase_orders": [{"item_cd": "X", "vend_cd": "V", "due_date": "", "remaining_qty": "abc"}, "garbage"]}]

    [order] = open_purchase_orders_from_rows(rows)

    assert order.due_date is None
    assert order.remaining_qty == 0


def test_replenishment_helpers_are_gone():
    """補充見込み系は撤去した（08 design §2.4）。"""
    from application.inventory_order_alert.domain.value_objects import open_purchase_order as module

    for name in ("ReplenishmentOutlook", "build_replenishment_outlook", "replenishment_deadline"):
        assert not hasattr(module, name)
