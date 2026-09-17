"""判定ルール表（凡例）のテスト（test-design.md TC-SFV-D-040〜041）。

判定ルールダイアログの 4 行に 状況テンプレート・推奨アクション（T-207）・責任部署（R-201）を載せる。
判定軸（V-210）は廃止済みで、行にも文言にも現れない。
"""

from __future__ import annotations

import inspect
from dataclasses import fields

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    FLOW_QUADRANT_KEYS,
    FLOW_QUADRANTS,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_INCOMING,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
    responsible_departments,
)
from application.inventory_order_alert.domain.value_objects.flow_quadrant_rules import (
    FlowQuadrantRuleRow,
    build_flow_quadrant_rule_rows,
)
from application.inventory_order_alert.domain.value_objects.recommended_action import (
    DEFAULT_RECOMMENDED_ACTIONS,
)

PROHIBITED_TERMS = ("判定軸", "供給リスク品", "在庫過剰リスク品", "象限")


# --- TC-SFV-D-040: 判定ルール行に状況・推奨アクションが含まれる ---


def test_d040_rule_rows_are_four_in_rank_order():
    rows = build_flow_quadrant_rule_rows()

    assert [row.quadrant for row in rows] == [
        QUADRANT_LOW_FLOW_NO_INCOMING,
        QUADRANT_DORMANT_STOCK,
        QUADRANT_LOW_FLOW_NO_SHIPMENT,
        QUADRANT_NORMAL_FLOW,
    ]
    assert [row.quadrant for row in rows] == list(FLOW_QUADRANTS)


def test_d040_rule_rows_include_incoming_shipment_conditions():
    rows = build_flow_quadrant_rule_rows()

    assert [(row.has_incoming, row.has_shipment) for row in rows] == [
        ("なし", "あり"),
        ("なし", "なし"),
        ("あり", "なし"),
        ("あり", "あり"),
    ]


def test_d040_rule_rows_carry_status_template_and_action_from_recommended_actions():
    rows = build_flow_quadrant_rule_rows()

    for row in rows:
        expected = DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(row.quadrant)
        assert row.status_template == expected.status_template
        assert row.action == expected.action
        assert row.departments == expected.departments
        assert row.departments == responsible_departments(row.quadrant)
        assert row.quadrant_key == FLOW_QUADRANT_KEYS[row.quadrant]


def test_d040_low_flow_no_incoming_row_has_status_and_action_text():
    row = build_flow_quadrant_rule_rows()[0]

    assert row.quadrant == QUADRANT_LOW_FLOW_NO_INCOMING
    assert "{period}" in row.status_template
    assert "仕入先" in row.action


def test_d040_normal_flow_row_has_empty_status_and_action():
    row = build_flow_quadrant_rule_rows()[-1]

    assert row.quadrant == QUADRANT_NORMAL_FLOW
    assert row.status_template == ""
    assert row.action == ""


def test_d040_rule_rows_require_no_arguments():
    params = inspect.signature(build_flow_quadrant_rule_rows).parameters

    assert all(param.default is not inspect.Parameter.empty for param in params.values())
    assert not any("month" in name for name in params)


def test_d040_rule_rows_reflect_overridden_action_texts():
    overridden = DEFAULT_RECOMMENDED_ACTIONS.with_action_texts(
        {FLOW_QUADRANT_KEYS[QUADRANT_LOW_FLOW_NO_INCOMING]: "上書き文言"}
    )

    rows = build_flow_quadrant_rule_rows(overridden)

    assert rows[0].action == "上書き文言"
    assert rows[0].status_template == DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_LOW_FLOW_NO_INCOMING).status_template
    assert [row.action for row in rows[1:]] == [
        DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(row.quadrant).action for row in rows[1:]
    ]


# --- TC-SFV-D-041: 判定ルール行に判定軸の項目がない ---


def test_d041_rule_row_has_no_axis_field():
    names = {field.name for field in fields(FlowQuadrantRuleRow)}

    assert "axis" not in names
    assert not any("axis" in name for name in names)
    assert {"quadrant", "quadrant_key", "status_template", "action", "departments"} <= names


def test_d041_rule_rows_do_not_mention_prohibited_terms():
    for row in build_flow_quadrant_rule_rows():
        texts = (row.has_incoming, row.has_shipment, row.quadrant, row.status_template, row.action, *row.departments)
        for text in texts:
            for term in PROHIBITED_TERMS:
                assert term not in text
