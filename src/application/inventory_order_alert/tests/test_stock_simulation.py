"""日次の在庫の動き（V-237 在庫シミュレーションの材料）のテスト（test-design.md TC-SSC-D-*）。

照合単位の行から、クライアントが累積するだけで描ける形に組み立てる。
重複除去・完成品直下の工程の絞り込みはここで済ませる（09 design §2.1）。
"""

from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.stock_simulation import (
    DailyMovement,
    build_stock_simulation_input,
)

AS_OF = date(2026, 9, 18)


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "cust_code": "100",
        "item_cd": "ITEM-A",
        "internal_item_cd": "IN-1",
        "level1_item_cd": "X-9065",
        "level1_vend_cd": "9065",
        "daily_shipment": [],
        "daily_incoming": [],
        "unconfirmed_order_daily": [],
        "open_purchase_orders": [],
    }
    row.update(overrides)
    return row


def _by_date(movements: list[DailyMovement]) -> dict[date, DailyMovement]:
    return {movement.date: movement for movement in movements}


# --- TC-SSC-D-001〜003: 過去側（日次出荷・日次入荷） ---


def test_d001_past_shipment_and_incoming_are_taken_per_day():
    rows = [
        _row(
            daily_shipment=[{"date": "2026-09-10", "qty": 20}, {"date": "2026-09-12", "qty": 5}],
            daily_incoming=[{"date": "2026-09-12", "qty": 50}],
        )
    ]

    movements = _by_date(build_stock_simulation_input(rows, as_of_date=AS_OF))

    assert movements[date(2026, 9, 10)].ship == 20
    assert movements[date(2026, 9, 12)].ship == 5
    assert movements[date(2026, 9, 12)].incoming == 50


def test_d002_shipment_older_than_the_window_is_dropped():
    rows = [_row(daily_shipment=[{"date": "2026-08-18", "qty": 20}, {"date": "2026-08-19", "qty": 7}])]

    movements = _by_date(build_stock_simulation_input(rows, as_of_date=AS_OF, past_days=30))

    assert date(2026, 8, 18) not in movements  # 31 日前は範囲外
    assert movements[date(2026, 8, 19)].ship == 7  # 30 日前は範囲内


def test_d003_movements_on_the_base_date_are_kept():
    rows = [_row(daily_shipment=[{"date": "2026-09-18", "qty": 3}], daily_incoming=[{"date": "2026-09-18", "qty": 9}])]

    movements = _by_date(build_stock_simulation_input(rows, as_of_date=AS_OF))

    assert movements[date(2026, 9, 18)].ship == 3
    assert movements[date(2026, 9, 18)].incoming == 9


# --- TC-SSC-D-004/005/008: 未来側（内示・予定入荷） ---


def test_d004_future_demand_and_planned_incoming():
    rows = [
        _row(
            unconfirmed_order_daily=[{"date": "2026-10-01", "qty": 60}, {"date": "2026-10-10", "qty": 60}],
            open_purchase_orders=[
                {"order_cd": "PO-1", "item_cd": "X-9065", "vend_cd": "9065", "due_date": "2026/10/05", "remaining_qty": 50}
            ],
        )
    ]

    movements = _by_date(build_stock_simulation_input(rows, as_of_date=AS_OF))

    assert movements[date(2026, 10, 1)].demand == 60
    assert movements[date(2026, 10, 10)].demand == 60
    assert movements[date(2026, 10, 5)].planned == 50


def test_d005_overdue_orders_are_not_planned_incoming():
    rows = [
        _row(
            open_purchase_orders=[
                {"order_cd": "PO-1", "item_cd": "X-9065", "vend_cd": "9065", "due_date": "2026/09/10", "remaining_qty": 50},
                {"order_cd": "PO-2", "item_cd": "X-9065", "vend_cd": "9065", "due_date": "2026/09/18", "remaining_qty": 30},
            ]
        )
    ]

    movements = build_stock_simulation_input(rows, as_of_date=AS_OF)

    assert all(movement.planned == 0 for movement in movements)


def test_d008_orders_of_upstream_processes_are_not_planned_incoming():
    rows = [
        _row(
            open_purchase_orders=[
                {"order_cd": "PO-1", "item_cd": "UPSTREAM", "vend_cd": "9106", "due_date": "2026/10/05", "remaining_qty": 50}
            ]
        )
    ]

    movements = build_stock_simulation_input(rows, as_of_date=AS_OF)

    assert all(movement.planned == 0 for movement in movements)


# --- TC-SSC-D-006/007/009/010: 重複除去 ---


def test_d006_demand_is_not_counted_twice():
    daily = [{"date": "2026-10-01", "qty": 60}]
    rows = [_row(item_cd="ITEM-A", unconfirmed_order_daily=daily), _row(item_cd="ITEM-B", unconfirmed_order_daily=daily)]

    movements = _by_date(build_stock_simulation_input(rows, as_of_date=AS_OF))

    assert movements[date(2026, 10, 1)].demand == 60


def test_d007_planned_incoming_is_not_counted_twice():
    order = {"order_cd": "PO-1", "item_cd": "X-9065", "vend_cd": "9065", "due_date": "2026/10/05", "remaining_qty": 50}
    rows = [_row(item_cd="ITEM-A", open_purchase_orders=[order]), _row(item_cd="ITEM-B", open_purchase_orders=[order])]

    movements = _by_date(build_stock_simulation_input(rows, as_of_date=AS_OF))

    assert movements[date(2026, 10, 5)].planned == 50


def test_d009_daily_shipment_is_not_counted_twice():
    """出荷は (得意先, 得意先品番) で重複を除く。別品番なら合算する。"""
    shipment = [{"date": "2026-09-10", "qty": 20}]
    same = [_row(item_cd="ITEM-A", daily_shipment=shipment), _row(item_cd="ITEM-A", daily_shipment=shipment)]
    other = [_row(item_cd="ITEM-A", daily_shipment=shipment), _row(item_cd="ITEM-B", daily_shipment=shipment)]

    assert _by_date(build_stock_simulation_input(same, as_of_date=AS_OF))[date(2026, 9, 10)].ship == 20
    assert _by_date(build_stock_simulation_input(other, as_of_date=AS_OF))[date(2026, 9, 10)].ship == 40


def test_d010_daily_incoming_is_not_counted_twice():
    """入荷は (仕入先品番, 仕入先) で重複を除く。得意先品番が違っても同じ組なら 1 回。"""
    incoming = [{"date": "2026-09-12", "qty": 50}]
    rows = [_row(item_cd="ITEM-A", daily_incoming=incoming), _row(item_cd="ITEM-B", daily_incoming=incoming)]

    movements = _by_date(build_stock_simulation_input(rows, as_of_date=AS_OF))

    assert movements[date(2026, 9, 12)].incoming == 50


# --- TC-SSC-D-011〜013 ---


def test_d011_past_days_zero_builds_only_the_future_side():
    """`build_stock_projection` は未来側だけを使う。"""
    rows = [
        _row(
            daily_shipment=[{"date": "2026-09-10", "qty": 20}],
            unconfirmed_order_daily=[{"date": "2026-10-01", "qty": 60}],
        )
    ]

    movements = build_stock_simulation_input(rows, as_of_date=AS_OF, past_days=0)

    assert [movement.date for movement in movements] == [date(2026, 10, 1)]


def test_d012_unparsable_entries_are_dropped():
    rows = [
        _row(
            daily_shipment=[{"date": "", "qty": 5}, {"date": "おかしな日付", "qty": 5}, "garbage"],
            unconfirmed_order_daily=[{"date": None, "qty": 5}],
            open_purchase_orders=[{"order_cd": "PO-1", "item_cd": "X-9065", "vend_cd": "9065", "due_date": "", "remaining_qty": 50}],
        )
    ]

    assert build_stock_simulation_input(rows, as_of_date=AS_OF) == []


def test_d013_movements_are_sorted_by_date():
    rows = [
        _row(
            daily_shipment=[{"date": "2026-09-15", "qty": 1}, {"date": "2026-09-01", "qty": 1}],
            unconfirmed_order_daily=[{"date": "2026-10-10", "qty": 1}, {"date": "2026-10-01", "qty": 1}],
        )
    ]

    movements = build_stock_simulation_input(rows, as_of_date=AS_OF)

    assert [movement.date for movement in movements] == [
        date(2026, 9, 1),
        date(2026, 9, 15),
        date(2026, 10, 1),
        date(2026, 10, 10),
    ]


def test_zero_quantities_are_dropped():
    rows = [_row(daily_shipment=[{"date": "2026-09-10", "qty": 0}], unconfirmed_order_daily=[{"date": "2026-10-01", "qty": 0}])]

    assert build_stock_simulation_input(rows, as_of_date=AS_OF) == []


# --- 描画範囲は品目によらず固定（REQ-SSC-F-002） ---


def test_simulation_range_is_fixed_regardless_of_the_item():
    from application.inventory_order_alert.domain.value_objects.stock_simulation import simulation_range

    start, end = simulation_range(AS_OF)

    assert start == date(2026, 8, 19)   # 基準日の 30 日前
    assert end == date(2026, 12, 31)    # 翌々々月末
