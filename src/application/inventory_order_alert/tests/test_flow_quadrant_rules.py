"""判定ルール表（凡例）のテスト（test-design.md TC-SFV-D-040〜041）。

判定ルールダイアログの 7 行（07_flow-quadrant-refinement design §2.9）に 判定材料（在庫 / 需要 / 直近入荷 /
期間内入荷 / 期間内出荷）・状況テンプレート・推奨アクション（T-207）・責任部署（R-201）を載せる。
判定軸（V-210）は廃止済みで、行にも文言にも現れない。
"""

from __future__ import annotations

import inspect
from dataclasses import fields

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    FLOW_QUADRANT_KEYS,
    FLOW_QUADRANTS,
    QUADRANT_DISCONTINUATION_CANDIDATE,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_INCOMING,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
    QUADRANT_STOCKOUT,
    QUADRANT_STOCKOUT_NO_INCOMING,
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


def _row_of(quadrant: str, **kwargs):
    return next(row for row in build_flow_quadrant_rule_rows(**kwargs) if row.quadrant == quadrant)


# --- TC-SFV-D-040: 判定ルール行に状況・推奨アクションが含まれる（07 で 7 行） ---


def test_d040_rule_rows_are_seven_in_rank_order():
    rows = build_flow_quadrant_rule_rows()

    assert [row.quadrant for row in rows] == [
        QUADRANT_STOCKOUT_NO_INCOMING,
        QUADRANT_STOCKOUT,
        QUADRANT_LOW_FLOW_NO_INCOMING,
        QUADRANT_DORMANT_STOCK,
        QUADRANT_LOW_FLOW_NO_SHIPMENT,
        QUADRANT_DISCONTINUATION_CANDIDATE,
        QUADRANT_NORMAL_FLOW,
    ]
    assert [row.quadrant for row in rows] == list(FLOW_QUADRANTS)


def test_d040_rule_rows_include_incoming_shipment_conditions():
    """在庫ありの 4 行は期間内入荷・出荷で分かれ、在庫なしの 3 行は判定期間によらない（—）。"""
    rows = build_flow_quadrant_rule_rows()

    assert [(row.has_incoming, row.has_shipment) for row in rows] == [
        ("—", "—"),
        ("—", "—"),
        ("なし", "あり"),
        ("なし", "なし"),
        ("あり", "なし"),
        ("—", "—"),
        ("あり", "あり"),
    ]


def test_fqr_a003_rule_rows_include_stock_demand_recent_incoming_conditions():
    """TC-FQR-A-003（07 design §2.9）: 在庫 / 需要 / 直近入荷 の列。在庫ありの行は需要・直近入荷を見ない（—）。"""
    rows = build_flow_quadrant_rule_rows()

    assert [(row.stock, row.demand, row.recent_incoming) for row in rows] == [
        ("なし", "あり", "なし"),
        ("なし", "あり", "あり"),
        ("あり", "—", "—"),
        ("あり", "—", "—"),
        ("あり", "—", "—"),
        ("なし", "なし", "—"),
        ("あり", "—", "—"),
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
    row = _row_of(QUADRANT_LOW_FLOW_NO_INCOMING)

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

    target = next(row for row in rows if row.quadrant == QUADRANT_LOW_FLOW_NO_INCOMING)
    others = [row for row in rows if row.quadrant != QUADRANT_LOW_FLOW_NO_INCOMING]
    assert target.action == "上書き文言"
    assert target.status_template == DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_LOW_FLOW_NO_INCOMING).status_template
    assert [row.action for row in others] == [DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(row.quadrant).action for row in others]


# --- TC-SFV-D-041: 判定ルール行に判定軸の項目がない ---


def test_d041_rule_row_has_no_axis_field():
    names = {field.name for field in fields(FlowQuadrantRuleRow)}

    assert "axis" not in names
    assert not any("axis" in name for name in names)
    assert {"quadrant", "quadrant_key", "status_template", "action", "departments"} <= names


def test_d041_rule_rows_do_not_mention_prohibited_terms():
    for row in build_flow_quadrant_rule_rows():
        texts = (row.stock, row.demand, row.recent_incoming, row.has_incoming, row.has_shipment, row.quadrant, row.status_template, row.action, *row.departments)
        for text in texts:
            for term in PROHIBITED_TERMS:
                assert term not in text


# --- 判定ルール表の状況文言（2026/09/17 画面指摘: プレースホルダがそのまま表示され、セルが折り返されない） ---


def test_rule_rows_carry_status_example_and_text_without_date_placeholders():
    rows = build_flow_quadrant_rule_rows(period_label="1年")

    no_incoming = _row_of(QUADRANT_LOW_FLOW_NO_INCOMING, period_label="1年")
    assert no_incoming.status_example == "出荷は継続、最終入荷 YYYY/MM/DD（{period}以上入荷なし）"
    assert no_incoming.status_text == "出荷は継続、最終入荷 YYYY/MM/DD（1年以上入荷なし）"
    # 07 の閾値プレースホルダ（{recent_days}）は凡例でも実値で埋まる
    assert _row_of(QUADRANT_STOCKOUT_NO_INCOMING).status_text == "在庫なし・需要あり、最終入荷 YYYY/MM/DD（直近 30 日入荷なし）"
    # 需要の窓（{demand_window}）は撤去済み（07 REQ-FQR-F-002）
    assert _row_of(QUADRANT_DISCONTINUATION_CANDIDATE).status_text == "在庫なし・内示なし（最終出荷 YYYY/MM/DD）"
    for row in rows:
        assert "{last_incoming}" not in row.status_text and "{last_ship}" not in row.status_text
        assert "{period}" not in row.status_text
        assert "{recent_days}" not in row.status_text and "{demand_window}" not in row.status_text
        assert "{last_incoming}" not in row.status_example and "{last_ship}" not in row.status_example
    assert rows[-1].status_text == ""
