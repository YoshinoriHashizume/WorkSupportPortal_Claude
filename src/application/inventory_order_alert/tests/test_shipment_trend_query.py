"""all_shipments のグループ化（infrastructure）のテスト（test-design.md TC-SHC-I-001〜003）。"""

from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.shipment_trend import build_monthly_shipment_trend
from application.inventory_order_alert.infrastructure.oracle.summary_queries import group_shipments_by_pair


def test_TC_SHC_I_001_groups_by_cust_code_and_cust_item_cd():
    shipments = [
        ("112", "ITEM-A", date(2026, 6, 1), 10),
        ("112", "ITEM-A", date(2026, 5, 1), 5),
        ("201", "ITEM-B", date(2026, 6, 1), 20),
    ]

    grouped = group_shipments_by_pair(shipments)

    assert len(grouped) == 2
    assert len(grouped[("112", "ITEM-A")]) == 2
    assert len(grouped[("201", "ITEM-B")]) == 1
    assert grouped[("112", "ITEM-A")][0] == (date(2026, 6, 1), 10)


def test_TC_SHC_I_002_empty_list_returns_empty_dict():
    assert group_shipments_by_pair([]) == {}


def test_TC_SHC_I_003_missing_key_falls_back_to_all_zero_trend():
    grouped = group_shipments_by_pair([])

    trend = build_monthly_shipment_trend(
        grouped.get(("999", "NOT-SHIPPED"), []),
        as_of_date=date(2026, 6, 17),
    )

    assert len(trend) == 24
    assert all(point["qty"] == 0 for point in trend)
