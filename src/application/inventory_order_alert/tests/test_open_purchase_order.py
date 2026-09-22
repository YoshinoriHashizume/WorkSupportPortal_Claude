"""発注残（V-224）と補充見込み（V-226）のテスト（TC-SOR-D-001〜009a）。"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from application.inventory_order_alert.domain.value_objects.open_purchase_order import (
    OpenPurchaseOrder,
    ReplenishmentOutlook,
    build_replenishment_outlook,
    open_purchase_orders_from_rows,
    replenishment_deadline,
)

AS_OF = date(2026, 9, 17)
#: 補充期限（V-229）: 予測月 2026-12 の 1 日 ＋ 安全日数 14
DEADLINE_DEC = date(2026, 12, 15)
#: 長期納期超過（V-230）の閾値: リードタイム 5 ＋ 安全日数 14
STALE_AFTER = 19


def _outlook(orders, *, stockout_month="2026-12", deadline=DEADLINE_DEC, stale_after_days=STALE_AFTER, level1_pairs=None):
    return build_replenishment_outlook(
        orders, as_of_date=AS_OF, stockout_month=stockout_month, deadline=deadline, stale_after_days=stale_after_days, level1_pairs=level1_pairs
    )


def _po(due: date | None, qty: int, item_cd: str = "X-9065", vend_cd: str = "9065") -> OpenPurchaseOrder:
    return OpenPurchaseOrder(item_cd=item_cd, vend_cd=vend_cd, due_date=due, remaining_qty=qty)


def test_d001_sums_remaining_qty_due_by_deadline():
    """補充期限（12/15）までの納期を数え、翌日以降は later（2026/09/21 改訂: 予測月の月末 → 補充期限）。"""
    outlook = _outlook([_po(date(2026, 10, 5), 100), _po(date(2026, 12, 15), 50), _po(date(2026, 12, 16), 30)])

    assert outlook.qty == 150
    assert outlook.later_qty == 30
    assert outlook.stale_qty == 0
    assert outlook.earliest_due == date(2026, 10, 5)
    assert outlook.has_overdue is False
    assert outlook.unknown is False


def test_d002_recently_overdue_orders_are_counted_and_flagged():
    """納期超過が LT＋安全日数 以内の発注残は納期遅れの入荷待ちとして補充に数える。"""
    outlook = _outlook([_po(date(2026, 9, 1), 20)])

    assert outlook.qty == 20
    assert outlook.stale_qty == 0
    assert outlook.has_overdue is True
    assert outlook.earliest_due == date(2026, 9, 1)


def test_d007_stale_overdue_orders_are_excluded_from_replenishment():
    """長期納期超過（V-230）は補充見込みに数えず、別枠で持つ。納期超過の印は付く。"""
    outlook = _outlook([_po(date(2026, 6, 1), 20)])

    assert outlook.qty == 0
    assert outlook.stale_qty == 20
    assert outlook.has_overdue is True
    assert outlook.earliest_due is None


def test_d008_stale_boundary_is_stale_after_days():
    exactly = _outlook([_po(AS_OF - timedelta(days=STALE_AFTER), 20)])
    one_more = _outlook([_po(AS_OF - timedelta(days=STALE_AFTER + 1), 20)])

    assert (exactly.qty, exactly.stale_qty) == (20, 0)
    assert (one_more.qty, one_more.stale_qty) == (0, 20)


@pytest.mark.parametrize(
    ("stockout_month", "expected"),
    [("2026-10", date(2026, 10, 15)), ("2026-09", date(2026, 10, 1)), ("2027-01", date(2027, 1, 15))],
)
def test_d009_replenishment_deadline_is_stockout_day_or_as_of_plus_safety(stockout_month, expected):
    """補充期限（V-229）= max(予測月の 1 日, 基準日) ＋ 安全日数。当月は基準日起点。"""
    assert replenishment_deadline(AS_OF, stockout_month, safety_days=14) == expected


def test_d009_replenishment_deadline_is_none_without_stockout_month():
    assert replenishment_deadline(AS_OF, None, safety_days=14) is None


def test_d003_no_stockout_month_gives_zero_outlook():
    outlook = _outlook([_po(date(2026, 10, 5), 100)], stockout_month=None, deadline=None)

    assert outlook == ReplenishmentOutlook(qty=0, later_qty=0, earliest_due=None, has_overdue=False, unknown=False)


def test_d004_negative_remaining_is_zero():
    assert _po(date(2026, 10, 5), -5).remaining_qty == 0


def test_d005_missing_due_date_is_not_counted_before_stockout():
    outlook = _outlook([_po(None, 40)])

    assert outlook.qty == 0
    assert outlook.later_qty == 40
    assert outlook.earliest_due is None


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
    assert _outlook(orders).qty == 107


def test_d006a_distinct_orders_with_same_item_due_and_qty_are_all_counted():
    """同品番・同仕入先・同納期・同数量でも order_cd が違えば別明細（カンバン式の分割発注。2026/09/18 レビュー指摘）。"""
    line = {"item_cd": "X-9065", "vend_cd": "9065", "due_date": "2026/10/05", "remaining_qty": 20}
    rows = [
        {"open_purchase_orders": [{"order_cd": f"PO-{n}", **line} for n in range(1, 4)]},
        {"open_purchase_orders": [{"order_cd": f"PO-{n}", **line} for n in range(1, 4)]},
    ]

    orders = open_purchase_orders_from_rows(rows)

    assert len(orders) == 3
    assert _outlook(orders, stockout_month="2026-10", deadline=date(2026, 10, 15)).qty == 60


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


def test_unknown_outlook_helper():
    outlook = ReplenishmentOutlook.unknown_outlook()

    assert outlook.unknown is True
    assert outlook.qty == 0


# --- 2026/09/18 追加: 工程の連鎖。上流工程の発注残は補充見込みに数えず、別に持つ ---


def test_upstream_orders_are_tracked_separately():
    level1_pairs = {("X-9133", "9133")}
    orders = [
        _po(date(2026, 10, 5), 100, item_cd="X-9133", vend_cd="9133"),  # 直下の工程
        _po(date(2026, 6, 15), 240, item_cd="X-9106", vend_cd="9106"),  # 上流・納期超過
        _po(date(2026, 11, 1), 50, item_cd="X-9213", vend_cd="9213"),  # 上流・納期内
    ]

    outlook = _outlook(orders, level1_pairs=level1_pairs)

    assert outlook.qty == 100
    assert outlook.has_overdue is False
    assert outlook.upstream_qty == 290
    assert outlook.upstream_overdue is True
    assert outlook.upstream_earliest_due == date(2026, 6, 15)
    # 納期超過でなく補充期限以前の上流の残数（混在時の判定・理由に使う。2026/09/18、2026/09/21 納期の窓）
    assert outlook.upstream_pending_qty == 50


def test_d009a_upstream_pending_requires_due_within_deadline():
    """上流工程の発注残が「流れている」とみなすのは 納期超過でなく 納期 ≤ 補充期限 のもののみ。納期なし・補充期限より後は数えない（2026/09/21）。"""
    level1_pairs = {("X-9133", "9133")}
    orders = [
        _po(date(2027, 3, 1), 100, item_cd="X-9106", vend_cd="9106"),  # 補充期限より後
        _po(None, 50, item_cd="X-9213", vend_cd="9213"),  # 納期なし
        _po(date(2026, 10, 1), 30, item_cd="X-9300", vend_cd="9300"),  # 補充期限以前
    ]

    outlook = _outlook(orders, level1_pairs=level1_pairs)

    assert outlook.upstream_qty == 180
    assert outlook.upstream_pending_qty == 30
    assert outlook.upstream_overdue is False


def test_upstream_pending_qty_is_zero_when_all_upstream_orders_are_overdue():
    level1_pairs = {("X-9133", "9133")}
    orders = [
        _po(date(2026, 6, 15), 240, item_cd="X-9106", vend_cd="9106"),
        _po(date(2026, 9, 10), 30, item_cd="X-9213", vend_cd="9213"),
    ]

    outlook = _outlook(orders, level1_pairs=level1_pairs)

    assert outlook.upstream_qty == 270
    assert outlook.upstream_pending_qty == 0
    assert outlook.upstream_overdue is True
    assert ReplenishmentOutlook.empty().upstream_pending_qty == 0


def test_without_level1_pairs_every_order_counts_as_direct():
    outlook = _outlook([_po(date(2026, 10, 5), 100, item_cd="X-9106", vend_cd="9106")])

    assert outlook.qty == 100
    assert outlook.upstream_qty == 0


def test_upstream_orders_are_counted_even_without_stockout_month():
    orders = [_po(date(2026, 6, 15), 240, item_cd="X-9106", vend_cd="9106")]

    outlook = _outlook(orders, stockout_month=None, deadline=None, level1_pairs={("X-9133", "9133")})

    assert outlook.qty == 0
    assert outlook.upstream_qty == 240
    assert outlook.upstream_overdue is True
    assert outlook.upstream_pending_qty == 0
