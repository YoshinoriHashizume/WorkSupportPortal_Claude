"""要発注は手動発注（V-227）を含む照合単位だけ（ISSUE-0010）。

MRP は内示から発注を自動で起票するため、MRP 発注のみ・発注方式が不明の照合単位は
「在庫が切れる・発注期限が未来・納期遅れなし」でも対象外にする。発注遅れ・納期確認は変えない。
"""

from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.ordering_profile import LEAD_TIME_SOURCE_MASTER
from application.inventory_order_alert.domain.value_objects.stock_projection import DailyStockProjection
from application.inventory_order_alert.domain.value_objects.stockout_risk import (
    RESPONSE_DELIVERY_CHECK,
    RESPONSE_NONE,
    RESPONSE_ORDER_NEEDED,
    RESPONSE_ORDER_OVERDUE,
    assess_response_class,
)

AS_OF = date(2026, 11, 25)
MRP_NOTE = "MRP が発注を自動で起票するため対応区分に反映していません"


def _projection(**overrides: object) -> DailyStockProjection:
    values: dict[str, object] = {
        "has_demand": True,
        "stockout_date": date(2026, 12, 15),
        "order_deadline": date(2026, 12, 10),
        "below_safety_stock": False,
        "safety_stock": 0.0,
        "overdue_order_qty": 0,
        "overdue_order_count": 0,
        "lead_time_days": 5,
        "lead_time_source": LEAD_TIME_SOURCE_MASTER,
        "has_manual_ordering": False,
        "stale_order_qty": 0,
        "stale_order_count": 0,
    }
    values.update(overrides)
    return DailyStockProjection(**values)


def _assess(projection: DailyStockProjection):
    return assess_response_class(projection, as_of_date=AS_OF, judgement_horizon_days=30)


def test_manual_ordering_unit_is_order_needed():
    result = _assess(_projection(has_manual_ordering=True))

    assert result.response_class == RESPONSE_ORDER_NEEDED
    assert not any(MRP_NOTE in reason for reason in result.reasons)


def test_mrp_only_unit_is_not_order_needed():
    result = _assess(_projection(has_manual_ordering=False))

    assert result.response_class == RESPONSE_NONE


def test_mrp_unit_keeps_stockout_and_deadline_in_reasons_with_a_note():
    result = _assess(_projection(has_manual_ordering=False))

    assert "在庫切れ 2026/12/15" in result.reasons
    assert any(reason.startswith("発注期限 2026/12/10") and MRP_NOTE in reason for reason in result.reasons)


def test_mrp_unit_past_deadline_is_still_order_overdue():
    result = _assess(_projection(has_manual_ordering=False, order_deadline=date(2026, 11, 25)))

    assert result.response_class == RESPONSE_ORDER_OVERDUE
    assert not any(MRP_NOTE in reason for reason in result.reasons)


def test_mrp_unit_with_overdue_order_is_still_delivery_check():
    result = _assess(_projection(has_manual_ordering=False, overdue_order_qty=20, overdue_order_count=1))

    assert result.response_class == RESPONSE_DELIVERY_CHECK
