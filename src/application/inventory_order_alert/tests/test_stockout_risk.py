"""対応区分（S-204）の判定と理由のテスト（test-design.md TC-SRR-R-*, N-*）。

日次の在庫見通し（V-232 在庫切れ日 / V-233 発注期限 / V-231 安全在庫）と
納期遅れの発注残から、次にすべき行動を 5 区分で示す（08 design §2.2）。
"""

from __future__ import annotations

from datetime import date

import pytest

from application.inventory_order_alert.domain.value_objects.ordering_profile import (
    LEAD_TIME_SOURCE_DEFAULT,
    LEAD_TIME_SOURCE_MASTER,
)
from application.inventory_order_alert.domain.value_objects.stock_projection import DailyStockProjection
from application.inventory_order_alert.domain.value_objects.stockout_risk import (
    RESPONSE_CLASS_KEYS,
    RESPONSE_CLASS_RANK,
    RESPONSE_CLASSES,
    RESPONSE_DELIVERY_CHECK,
    RESPONSE_NONE,
    RESPONSE_ORDER_NEEDED,
    RESPONSE_ORDER_OVERDUE,
    RESPONSE_WATCH,
    assess_response_class,
    normalize_response_class,
    response_class_sort_rank,
    row_response_class,
)

AS_OF = date(2026, 9, 18)


def _projection(**overrides: object) -> DailyStockProjection:
    values: dict[str, object] = {
        "has_demand": True,
        "stockout_date": None,
        "order_deadline": None,
        "below_safety_stock": False,
        "safety_stock": 0.0,
        "overdue_order_qty": 0,
        "overdue_order_count": 0,
        "lead_time_days": 5,
        "lead_time_source": LEAD_TIME_SOURCE_MASTER,
    }
    values.update(overrides)
    return DailyStockProjection(**values)


def _assess(**overrides: object):
    return assess_response_class(_projection(**overrides), as_of_date=AS_OF)


# --- TC-SRR-R-001〜010: マトリクス ---


def test_r001_no_demand_without_overdue_is_none():
    result = _assess(has_demand=False)

    assert result.response_class == RESPONSE_NONE


def test_r002_no_demand_with_overdue_is_delivery_check():
    result = _assess(has_demand=False, overdue_order_qty=300, overdue_order_count=2)

    assert result.response_class == RESPONSE_DELIVERY_CHECK


def test_r003_no_stockout_without_overdue_is_none():
    assert _assess().response_class == RESPONSE_NONE


def test_r004_no_stockout_with_overdue_is_delivery_check():
    result = _assess(overdue_order_qty=100, overdue_order_count=1)

    assert result.response_class == RESPONSE_DELIVERY_CHECK


def test_r005_below_safety_stock_without_overdue_is_watch():
    result = _assess(below_safety_stock=True, safety_stock=50)

    assert result.response_class == RESPONSE_WATCH


def test_r006_below_safety_stock_with_overdue_is_delivery_check():
    result = _assess(below_safety_stock=True, safety_stock=50, overdue_order_qty=100, overdue_order_count=1)

    assert result.response_class == RESPONSE_DELIVERY_CHECK


def test_r007_stockout_with_future_deadline_is_order_needed():
    result = _assess(stockout_date=date(2026, 10, 10), order_deadline=date(2026, 10, 5))

    assert result.response_class == RESPONSE_ORDER_NEEDED


def test_r008_stockout_with_future_deadline_and_overdue_is_delivery_check():
    result = _assess(
        stockout_date=date(2026, 10, 10), order_deadline=date(2026, 10, 5), overdue_order_qty=100, overdue_order_count=1
    )

    assert result.response_class == RESPONSE_DELIVERY_CHECK


def test_r009_deadline_on_the_base_date_is_order_overdue():
    """発注期限が当日なら、もう間に合わないものとして扱う。"""
    result = _assess(stockout_date=date(2026, 9, 23), order_deadline=AS_OF)

    assert result.response_class == RESPONSE_ORDER_OVERDUE


def test_r010_passed_deadline_is_order_overdue_even_with_overdue_orders():
    result = _assess(
        stockout_date=date(2026, 9, 20), order_deadline=date(2026, 9, 15), overdue_order_qty=100, overdue_order_count=1
    )

    assert result.response_class == RESPONSE_ORDER_OVERDUE


# --- TC-SRR-R-011/012: ランクと正規化 ---


def test_r011_rank_order():
    assert RESPONSE_CLASSES == (
        RESPONSE_ORDER_OVERDUE,
        RESPONSE_DELIVERY_CHECK,
        RESPONSE_ORDER_NEEDED,
        RESPONSE_WATCH,
        RESPONSE_NONE,
    )
    assert [RESPONSE_CLASS_RANK[c] for c in RESPONSE_CLASSES] == [0, 1, 2, 3, 4]
    assert RESPONSE_CLASS_KEYS == {
        RESPONSE_ORDER_OVERDUE: "order-overdue",
        RESPONSE_DELIVERY_CHECK: "delivery-check",
        RESPONSE_ORDER_NEEDED: "order-needed",
        RESPONSE_WATCH: "watch",
        RESPONSE_NONE: "none",
    }


@pytest.mark.parametrize(
    ("legacy", "expected"),
    [
        ("危険", RESPONSE_ORDER_OVERDUE),
        ("注意", RESPONSE_ORDER_NEEDED),
        ("監視", RESPONSE_WATCH),
        ("対象外", RESPONSE_NONE),
        ("danger", RESPONSE_ORDER_OVERDUE),
        ("caution", RESPONSE_ORDER_NEEDED),
        ("order-needed", RESPONSE_ORDER_NEEDED),
        ("要発注", RESPONSE_ORDER_NEEDED),
        ("", RESPONSE_NONE),
        ("未知", RESPONSE_NONE),
    ],
)
def test_r012_normalize_legacy_values(legacy, expected):
    assert normalize_response_class(legacy) == expected


def test_row_response_class_reads_the_row():
    assert row_response_class({"response_class": "要発注"}) == RESPONSE_ORDER_NEEDED
    assert row_response_class({"stockout_risk": "危険"}) == RESPONSE_ORDER_OVERDUE  # 旧スナップショット
    assert row_response_class({}) == RESPONSE_NONE
    assert response_class_sort_rank({"response_class": "発注遅れ"}) == 0


# --- TC-SRR-N-001〜006: 理由 ---


def test_n001_stockout_and_deadline_reasons():
    result = _assess(stockout_date=date(2026, 10, 10), order_deadline=date(2026, 10, 2))

    assert result.reasons[0] == "在庫切れ 2026/10/10"
    assert result.reasons[1] == "発注期限 2026/10/02"


def test_n002_overdue_order_reason():
    result = _assess(overdue_order_qty=300, overdue_order_count=2)

    assert "納期遅れの発注残 2 件 300 個" in result.reasons


def test_n003_below_safety_stock_reason():
    result = _assess(below_safety_stock=True, safety_stock=50)

    assert "安全在庫 50 を下回る" in result.reasons


def test_n004_default_lead_time_reason():
    result = _assess(
        stockout_date=date(2026, 10, 10), order_deadline=date(2026, 10, 5), lead_time_source=LEAD_TIME_SOURCE_DEFAULT
    )

    assert "リードタイム未設定" in result.reasons


def test_n005_no_demand_reason():
    result = _assess(has_demand=False)

    assert result.reasons == ("内示なし（在庫は動かない）",)


def test_n006_nothing_to_say_has_no_reasons():
    assert _assess().reasons == ()


def test_removed_terms_are_gone():
    """撤去した概念が残っていないこと（08 design §2.4）。"""
    from application.inventory_order_alert.domain.value_objects import stockout_risk as module

    for name in (
        "RISK_DANGER",
        "RISK_CAUTION",
        "RISK_WATCH",
        "RISK_NONE",
        "STOCKOUT_RISKS",
        "days_until_stockout",
        "shortage_qty",
        "demand_until_month",
        "assess_stockout_risk",
    ):
        assert not hasattr(module, name)
