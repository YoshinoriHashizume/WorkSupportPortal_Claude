from __future__ import annotations

import inspect

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    FLOW_QUADRANT_KEYS,
    FLOW_QUADRANTS,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_EXCESS_STOCK_RISK,
    QUADRANT_NORMAL_FLOW,
    QUADRANT_SUPPLY_RISK,
    responsible_departments,
)
from application.inventory_order_alert.domain.value_objects.flow_quadrant_rules import (
    build_flow_quadrant_rule_rows,
)


def test_build_flow_quadrant_rule_rows_returns_four_rows_in_urgency_order():
    rows = build_flow_quadrant_rule_rows()

    assert [row.quadrant for row in rows] == [
        QUADRANT_SUPPLY_RISK,
        QUADRANT_DORMANT_STOCK,
        QUADRANT_EXCESS_STOCK_RISK,
        QUADRANT_NORMAL_FLOW,
    ]
    assert [row.quadrant for row in rows] == list(FLOW_QUADRANTS)


def test_build_flow_quadrant_rule_rows_includes_incoming_shipment_conditions():
    rows = build_flow_quadrant_rule_rows()

    conditions = [(row.has_incoming, row.has_shipment) for row in rows]

    assert conditions == [
        ("なし", "あり"),
        ("なし", "なし"),
        ("あり", "なし"),
        ("あり", "あり"),
    ]


def test_build_flow_quadrant_rule_rows_includes_responsible_departments():
    rows = build_flow_quadrant_rule_rows()

    for row in rows:
        assert row.departments == responsible_departments(row.quadrant)
        assert row.quadrant_key == FLOW_QUADRANT_KEYS[row.quadrant]


def test_build_flow_quadrant_rule_rows_takes_no_month_arguments():
    assert list(inspect.signature(build_flow_quadrant_rule_rows).parameters) == []
