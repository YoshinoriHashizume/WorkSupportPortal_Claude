"""日次の在庫見通しのテスト（test-design.md TC-SRR-P-001〜012）。

在庫から内示を日ごとに引き、納期が基準日より後の発注残を足して、
在庫切れ日・発注期限・安全在庫割れを求める（08 design §2.1）。
"""

from __future__ import annotations

from datetime import date

import pytest

from application.inventory_order_alert.domain.value_objects.stock_projection import (
    DailyStockProjection,
    build_stock_projection,
)

AS_OF = date(2026, 9, 18)


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "cust_code": "100",
        "item_cd": "ITEM-A",
        "internal_item_cd": "ITEM-A-CKD",
        "level1_item_cd": "ITEM-A-CKD-9000",
        "level1_vend_cd": "9000",
        "lead_time_days": 5,
        "lead_time_source": "master",
        "safety_stock": 0,
        "unconfirmed_order_daily": [],
        "open_purchase_orders": [],
    }
    row.update(overrides)
    return row


def _demand(*pairs: tuple[str, int]) -> list[dict[str, object]]:
    return [{"date": day, "qty": qty} for day, qty in pairs]


def _order(order_cd: str, due: str, qty: int, *, item: str = "ITEM-A-CKD-9000", vend: str = "9000") -> dict[str, object]:
    return {"order_cd": order_cd, "item_cd": item, "vend_cd": vend, "due_date": due, "remaining_qty": qty}


def _build(rows: list[dict[str, object]], stock_total: float | None, *, default_lead_time: int = 5) -> DailyStockProjection:
    return build_stock_projection(rows, as_of_date=AS_OF, stock_total=stock_total, default_lead_time_days=default_lead_time)


# --- TC-SRR-P-001/002: 内示の有無と在庫切れ日 ---


def test_p001_no_demand_means_stock_does_not_move():
    projection = _build([_row()], 100.0)

    assert projection.has_demand is False
    assert projection.stockout_date is None
    assert projection.order_deadline is None
    assert projection.below_safety_stock is False


def test_p002_stockout_date_is_the_first_day_below_zero():
    rows = [_row(unconfirmed_order_daily=_demand(("2026-10-01", 60), ("2026-10-10", 60)))]

    projection = _build(rows, 100.0)

    assert projection.has_demand is True
    assert projection.stockout_date == date(2026, 10, 10)


# --- TC-SRR-P-003〜005: 発注残の扱い ---


def test_p003_planned_receipt_before_the_stockout_prevents_it():
    rows = [
        _row(
            unconfirmed_order_daily=_demand(("2026-10-01", 60), ("2026-10-10", 60)),
            open_purchase_orders=[_order("PO-1", "2026/10/05", 50)],
        )
    ]

    projection = _build(rows, 100.0)

    assert projection.stockout_date is None
    assert projection.overdue_order_qty == 0


def test_p004_planned_receipt_after_the_stockout_does_not_prevent_it():
    """一時的にでも在庫が切れるなら在庫切れ日を出す（あとで発注残が届いても同じ）。"""
    rows = [
        _row(
            unconfirmed_order_daily=_demand(("2026-10-01", 60), ("2026-10-10", 60)),
            open_purchase_orders=[_order("PO-1", "2026/10/20", 500)],
        )
    ]

    projection = _build(rows, 100.0)

    assert projection.stockout_date == date(2026, 10, 10)


def test_p005_overdue_orders_are_not_added_to_stock():
    """納期遅れの発注残は来ないものとして計算し、件数・数量だけ持つ（REQ-SRR-F-002）。"""
    rows = [
        _row(
            unconfirmed_order_daily=_demand(("2026-10-10", 120)),
            open_purchase_orders=[_order("PO-1", "2026/09/01", 300), _order("PO-2", "2026/08/20", 200)],
        )
    ]

    projection = _build(rows, 100.0)

    assert projection.stockout_date == date(2026, 10, 10)
    assert projection.overdue_order_qty == 500
    assert projection.overdue_order_count == 2


def test_p005_order_due_on_the_base_date_counts_as_overdue():
    rows = [_row(unconfirmed_order_daily=_demand(("2026-10-10", 120)), open_purchase_orders=[_order("PO-1", "2026/09/18", 300)])]

    projection = _build(rows, 100.0)

    assert projection.overdue_order_qty == 300
    assert projection.stockout_date == date(2026, 10, 10)


# --- TC-SRR-P-006/012: 発注期限とリードタイム ---


def test_p006_order_deadline_is_the_stockout_date_minus_lead_time():
    rows = [_row(lead_time_days=8, unconfirmed_order_daily=_demand(("2026-12-11", 200)))]

    projection = _build(rows, 100.0)

    assert projection.stockout_date == date(2026, 12, 11)
    assert projection.order_deadline == date(2026, 12, 3)
    assert projection.lead_time_days == 8


def test_p012_missing_lead_time_falls_back_to_the_default():
    rows = [_row(lead_time_days=0, lead_time_source="default", unconfirmed_order_daily=_demand(("2026-10-10", 200)))]

    projection = _build(rows, 100.0, default_lead_time=5)

    assert projection.lead_time_days == 5
    assert projection.lead_time_source == "default"
    assert projection.order_deadline == date(2026, 10, 5)


# --- TC-SRR-P-007: 在庫が未取得 ---


def test_p007_missing_stock_is_treated_as_zero():
    rows = [_row(unconfirmed_order_daily=_demand(("2026-10-01", 10)))]

    projection = _build(rows, None)

    assert projection.stockout_date == date(2026, 10, 1)


# --- TC-SRR-P-008/009: 安全在庫 ---


def test_p008_below_safety_stock_without_running_out():
    rows = [_row(safety_stock=50, unconfirmed_order_daily=_demand(("2026-10-01", 70)))]

    projection = _build(rows, 100.0)

    assert projection.stockout_date is None
    assert projection.below_safety_stock is True
    assert projection.safety_stock == 50


def test_p009_safety_stock_zero_means_not_configured():
    rows = [_row(safety_stock=0, unconfirmed_order_daily=_demand(("2026-10-01", 70)))]

    projection = _build(rows, 100.0)

    assert projection.below_safety_stock is False


# --- TC-SRR-P-010/011: 照合単位の重複除去 ---


def test_p010_demand_is_not_counted_twice_for_the_same_customer_and_internal_item():
    """同じ (得意先, 内作品番) の行が複数あっても内示は 1 回だけ数える（需要予測と同じ規則）。"""
    shared = _demand(("2026-10-01", 60), ("2026-10-10", 60))
    rows = [_row(item_cd="ITEM-A", unconfirmed_order_daily=shared), _row(item_cd="ITEM-B", unconfirmed_order_daily=shared)]

    projection = _build(rows, 100.0)

    assert projection.stockout_date == date(2026, 10, 10)


def test_p011_planned_receipts_are_not_counted_twice_for_the_same_order():
    same_order = [_order("PO-1", "2026/10/05", 50)]
    rows = [
        _row(item_cd="ITEM-A", unconfirmed_order_daily=_demand(("2026-10-10", 140)), open_purchase_orders=same_order),
        _row(item_cd="ITEM-B", unconfirmed_order_daily=[], open_purchase_orders=same_order),
    ]

    projection = _build(rows, 100.0)

    # 在庫 100 + 発注残 50 = 150 に対し内示 140 なので切れない（発注残を 2 回数えると 200 になる）
    assert projection.stockout_date is None


def test_p011_safety_stock_is_summed_once_per_internal_item():
    rows = [
        _row(item_cd="ITEM-A", internal_item_cd="X", safety_stock=30),
        _row(item_cd="ITEM-B", internal_item_cd="X", safety_stock=30),
        _row(item_cd="ITEM-C", internal_item_cd="Y", safety_stock=20),
    ]

    projection = _build(rows, 100.0)

    assert projection.safety_stock == 50


# --- 異常系 ---


@pytest.mark.parametrize(
    "daily",
    [
        [{"date": "", "qty": 10}],
        [{"date": "2026-99-99", "qty": 10}],
        [{"qty": 10}],
        "文字列",
        None,
    ],
)
def test_broken_demand_data_does_not_raise(daily):
    projection = _build([_row(unconfirmed_order_daily=daily)], 100.0)

    assert projection.has_demand is False
    assert projection.stockout_date is None


def test_broken_order_data_does_not_raise():
    rows = [
        _row(
            unconfirmed_order_daily=_demand(("2026-10-10", 200)),
            open_purchase_orders=[{"order_cd": "", "due_date": "", "remaining_qty": "x"}, "壊れた行"],
        )
    ]

    projection = _build(rows, 100.0)

    assert projection.stockout_date == date(2026, 10, 10)
    assert projection.overdue_order_qty == 0


def test_demand_before_the_base_date_is_ignored():
    rows = [_row(unconfirmed_order_daily=_demand(("2026-09-01", 500), ("2026-10-10", 50)))]

    projection = _build(rows, 100.0)

    assert projection.stockout_date is None

# --- TC-SSC-C-001/004: 在庫シミュレーションの線と在庫切れ日が一致する（09 design §1） ---


def _first_negative_day(rows, *, stock_total, as_of=AS_OF):
    """在庫シミュレーションと同じ累積を行い、初めて 0 未満になる日を返す。"""
    from application.inventory_order_alert.domain.value_objects.stock_simulation import build_stock_simulation_input

    stock = 0.0 if stock_total is None else float(stock_total)
    for movement in build_stock_simulation_input(rows, as_of_date=as_of, past_days=0):
        stock = stock - movement.demand + movement.planned
        if stock < 0:
            return movement.date
    return None


@pytest.mark.parametrize(
    ("stock", "demand", "orders"),
    [
        (100, _demand(("2026-10-01", 60), ("2026-10-10", 60)), []),
        (100, _demand(("2026-10-01", 60), ("2026-10-10", 60)), [_order("PO-1", "2026/10/05", 50)]),
        (100, _demand(("2026-10-01", 60), ("2026-10-10", 60)), [_order("PO-1", "2026/10/20", 50)]),
        (100, _demand(("2026-10-01", 60)), [_order("PO-1", "2026/09/10", 500)]),
        (0, _demand(("2026-10-01", 1)), []),
        (100, [], [_order("PO-1", "2026/10/05", 50)]),
        (1000, _demand(("2026-10-01", 60), ("2026-12-31", 60)), []),
    ],
)
def test_ssc_c001_stockout_date_is_the_first_negative_day_of_the_simulation(stock, demand, orders):
    rows = [_row(unconfirmed_order_daily=demand, open_purchase_orders=orders)]

    projection = build_stock_projection(rows, as_of_date=AS_OF, stock_total=stock)

    assert projection.stockout_date == _first_negative_day(rows, stock_total=stock)


def test_ssc_c004_order_deadline_is_stockout_date_minus_lead_time():
    from datetime import timedelta

    rows = [_row(lead_time_days=8, unconfirmed_order_daily=_demand(("2026-10-01", 500)))]

    projection = build_stock_projection(rows, as_of_date=AS_OF, stock_total=100)

    assert projection.stockout_date == date(2026, 10, 1)
    assert projection.order_deadline == projection.stockout_date - timedelta(days=8)
