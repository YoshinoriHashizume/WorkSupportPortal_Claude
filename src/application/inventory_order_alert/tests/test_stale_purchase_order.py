"""滞留発注残（V-238）の判定のテスト（11 test-design.md TC-JS-S-001〜011）。

基幹に「発注を止めた」フラグが存在しないため、最終更新日（`UPDATED_DATE`）による**推定**で
「生きている納期遅れ」と「滞留」を分ける（11 REQ-JS-F-002）。
"""

from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.stock_simulation import (
    OverdueBreakdown,
    overdue_order_breakdown,
    overdue_orders,
)

AS_OF = date(2026, 10, 27)
STALE_AFTER = 30  # 境界は更新日 2026/09/27


def _row(orders: list[dict[str, object]], **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "cust_code": "110",
        "item_cd": "094ME-41490",
        "internal_item_cd": "IN-1",
        "level1_item_cd": "094ME-41490-9110",
        "level1_vend_cd": "9110",
        "open_purchase_orders": orders,
    }
    row.update(overrides)
    return row


def _order(**overrides: object) -> dict[str, object]:
    order: dict[str, object] = {
        "order_cd": "PO-1",
        "item_cd": "094ME-41490-9110",
        "vend_cd": "9110",
        "due_date": "2026/10/01",
        "updated_at": "2026/10/20",
        "remaining_qty": 100,
    }
    order.update(overrides)
    return order


def _breakdown(orders: list[dict[str, object]], *, stale_after_days: int | None = STALE_AFTER) -> OverdueBreakdown:
    return overdue_order_breakdown([_row(orders)], as_of_date=AS_OF, stale_after_days=stale_after_days)


# --- TC-JS-S-001〜004: 更新日による振り分け ---


def test_js_s001_recently_updated_overdue_is_live():
    result = _breakdown([_order(updated_at="2026/10/20")])

    assert result == OverdueBreakdown(overdue_qty=100, overdue_count=1)


def test_js_s002_exactly_at_threshold_is_stale():
    """境界は 30 日。`>=` なので 30 日ちょうどは滞留。"""
    result = _breakdown([_order(updated_at="2026/09/27")])

    assert result == OverdueBreakdown(stale_qty=100, stale_count=1)


def test_js_s003_one_day_inside_threshold_is_live():
    result = _breakdown([_order(updated_at="2026/09/28")])

    assert result == OverdueBreakdown(overdue_qty=100, overdue_count=1)


def test_js_s004_very_old_update_is_stale():
    result = _breakdown([_order(updated_at="2024/05/01")])

    assert result == OverdueBreakdown(stale_qty=100, stale_count=1)


# --- TC-JS-S-005: 納期が未来なら滞留にしない ---


def test_js_s005_future_due_date_is_never_stale():
    """納期が未来の明細は予定入荷（V-236）であり、更新日に関わらず納期遅れにも滞留にもしない。"""
    result = _breakdown([_order(due_date="2026/11/30", updated_at="2024/05/01")])

    assert result == OverdueBreakdown()


# --- TC-JS-S-006/007: 更新日がない・壊れている（REQ-JS-F-007） ---


def test_js_s006_missing_updated_at_is_live():
    """旧スナップショットの明細は従来どおり納期遅れとして数える。"""
    result = _breakdown([_order(updated_at="")])

    assert result == OverdueBreakdown(overdue_qty=100, overdue_count=1)


def test_js_s007_unparsable_updated_at_is_live():
    result = _breakdown([_order(updated_at="not-a-date")])

    assert result == OverdueBreakdown(overdue_qty=100, overdue_count=1)


# --- TC-JS-S-008: しきい値を渡さなければ分けない ---


def test_js_s008_none_threshold_keeps_everything_live():
    result = _breakdown([_order(updated_at="2024/05/01")], stale_after_days=None)

    assert result == OverdueBreakdown(overdue_qty=100, overdue_count=1)


# --- TC-JS-S-009: 重複除去 ---


def test_js_s009_same_order_across_rows_counts_once():
    orders = [_order(order_cd="PO-1", updated_at="2024/05/01")]
    rows = [_row(orders), _row(orders, cust_code="137", item_cd="OTHER")]

    result = overdue_order_breakdown(rows, as_of_date=AS_OF, stale_after_days=STALE_AFTER)

    assert result == OverdueBreakdown(stale_qty=100, stale_count=1)


# --- TC-JS-S-010: 完成品直下以外は対象外 ---


def test_js_s010_orders_outside_level1_are_ignored():
    result = _breakdown([_order(item_cd="OTHER-ITEM", updated_at="2024/05/01")])

    assert result == OverdueBreakdown()


# --- TC-JS-S-011: 後方互換 ---


def test_js_s011_overdue_orders_still_includes_stale():
    """`overdue_orders()` は従来どおり納期を過ぎた全部を返す（既存の呼び出しを壊さない）。"""
    rows = [_row([_order(order_cd="PO-1", updated_at="2026/10/20"), _order(order_cd="PO-2", updated_at="2024/05/01", remaining_qty=40)])]

    assert overdue_orders(rows, as_of_date=AS_OF) == (140, 2)


# --- 混在 ---


def test_live_and_stale_are_counted_separately():
    rows = [
        _row(
            [
                _order(order_cd="PO-1", updated_at="2026/10/20", remaining_qty=120),
                _order(order_cd="PO-2", updated_at="2024/05/01", remaining_qty=87),
                _order(order_cd="PO-3", updated_at="2025/02/26", remaining_qty=9),
                # 納期が未来 → どちらにも入らない
                _order(order_cd="PO-4", due_date="2026/10/30", updated_at="2026/10/26", remaining_qty=1000),
            ]
        )
    ]

    result = overdue_order_breakdown(rows, as_of_date=AS_OF, stale_after_days=STALE_AFTER)

    assert result == OverdueBreakdown(overdue_qty=120, overdue_count=1, stale_qty=96, stale_count=2)
