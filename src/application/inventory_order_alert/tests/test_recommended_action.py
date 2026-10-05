"""推奨アクション（T-207）と状況テンプレートのテスト（test-design.md TC-SFV-D-030〜038、TC-FQR-A-001〜004）。

流動区分（S-203）ごとの 状況テンプレート / 推奨アクション / 責任部署（R-201）を
`RecommendedAction` に束ね、**7 区分ぶん**を `RecommendedActions` で保持する（design §4.3、07 design §2.4）。
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from application.inventory_order_alert.domain.value_objects import recommended_action as module
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    DEFAULT_RECENT_INCOMING_DAYS,
    FLOW_QUADRANT_KEYS,
    FLOW_QUADRANTS,
    QUADRANT_DISCONTINUATION_CANDIDATE,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_INCOMING,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
    QUADRANT_STOCKOUT,
    QUADRANT_STOCKOUT_NO_INCOMING,
    EvaluationPeriod,
)
from application.inventory_order_alert.domain.value_objects.recommended_action import (
    DEFAULT_RECOMMENDED_ACTIONS,
    RecommendedAction,
    RecommendedActions,
    describe_status_template,
    render_status,
)

#: 96160-00500（得意先 100）の実データ: 最終入荷 2025/04/02、最終出荷 2023/07/27。
LAST_INCOMING = "2025/04/02"
LAST_SHIP = "2023/07/27"

PERIOD_Y1 = EvaluationPeriod(1)

KEY_LOW_FLOW_NO_INCOMING = FLOW_QUADRANT_KEYS[QUADRANT_LOW_FLOW_NO_INCOMING]

PROHIBITED_TERMS = ("供給リスク品", "在庫過剰リスク品", "未流動品", "デッドストック", "象限", "判定軸")


def _render(quadrant: str, *, last_incoming: str = LAST_INCOMING, last_ship: str = LAST_SHIP, no_incoming_record: bool = False) -> str:
    return render_status(
        DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(quadrant),
        period=PERIOD_Y1,
        last_incoming=last_incoming,
        last_ship=last_ship,
        no_incoming_record=no_incoming_record,
    )


# --- TC-SFV-D-030 / TC-FQR-A-001: 既定の 7 区分がすべて定義されている ---


def test_d030_default_actions_cover_all_seven_quadrants():
    assert len(DEFAULT_RECOMMENDED_ACTIONS) == 7
    assert tuple(action.quadrant for action in DEFAULT_RECOMMENDED_ACTIONS) == FLOW_QUADRANTS
    for quadrant in FLOW_QUADRANTS:
        assert DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(quadrant).quadrant == quadrant


def test_d030_low_flow_no_incoming_action_mentions_supplier_and_production_continuation():
    action = DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_LOW_FLOW_NO_INCOMING)
    assert "仕入先" in action.action
    assert "生産継続" in action.action


def test_d030_default_departments_follow_r201():
    expected = {
        QUADRANT_STOCKOUT_NO_INCOMING: ("調達G", "生産管理"),
        QUADRANT_STOCKOUT: ("生産管理", "調達G"),
        QUADRANT_LOW_FLOW_NO_INCOMING: ("調達G", "営業G", "生産管理"),
        QUADRANT_DORMANT_STOCK: ("調達G",),
        QUADRANT_LOW_FLOW_NO_SHIPMENT: ("営業G",),
        QUADRANT_DISCONTINUATION_CANDIDATE: ("営業G",),
        QUADRANT_NORMAL_FLOW: ("生産管理",),
    }
    for quadrant, departments in expected.items():
        assert DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(quadrant).departments == departments


def test_d030_default_texts_do_not_use_prohibited_terms():
    for action in DEFAULT_RECOMMENDED_ACTIONS:
        for term in PROHIBITED_TERMS:
            assert term not in action.status_template
            assert term not in action.action


# --- TC-SFV-D-031: 通常流動品は状況・アクションが空 ---


def test_d031_normal_flow_has_empty_status_and_action():
    action = DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_NORMAL_FLOW)
    assert action.status_template == ""
    assert action.action == ""
    assert _render(QUADRANT_NORMAL_FLOW) == ""


# --- TC-SFV-D-032: 未知の区分で生成を拒否 ---


@pytest.mark.parametrize("quadrant", ["供給リスク品", "在庫過剰リスク品", "low-flow-no-incoming", "", "象限1"])
def test_d032_unknown_quadrant_is_rejected(quadrant):
    with pytest.raises(ValueError):
        RecommendedAction(quadrant=quadrant, status_template="", action="", departments=())


def test_d032_recommended_action_is_immutable():
    action = DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_DORMANT_STOCK)
    with pytest.raises(FrozenInstanceError):
        action.action = "X"  # type: ignore[misc]


# --- TC-SFV-D-033 / TC-FQR-A-001: 7 区分に欠けがあるコレクションは拒否 ---


def test_d033_collection_missing_a_quadrant_is_rejected():
    six = tuple(action for action in DEFAULT_RECOMMENDED_ACTIONS if action.quadrant != QUADRANT_NORMAL_FLOW)
    assert len(six) == 6
    with pytest.raises(ValueError):
        RecommendedActions(six)


def test_fqr_a001_collection_missing_a_new_quadrant_is_rejected():
    """07: 旧 4 区分だけのコレクションは 7 区分に満たないため拒否される。"""

    legacy_four = tuple(
        action
        for action in DEFAULT_RECOMMENDED_ACTIONS
        if action.quadrant
        in (
            QUADRANT_LOW_FLOW_NO_INCOMING,
            QUADRANT_DORMANT_STOCK,
            QUADRANT_LOW_FLOW_NO_SHIPMENT,
            QUADRANT_NORMAL_FLOW,
        )
    )
    assert len(legacy_four) == 4
    with pytest.raises(ValueError):
        RecommendedActions(legacy_four)


def test_d033_collection_with_duplicate_quadrant_is_rejected():
    dormant = DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_DORMANT_STOCK)
    duplicated = tuple(
        dormant if action.quadrant == QUADRANT_NORMAL_FLOW else action for action in DEFAULT_RECOMMENDED_ACTIONS
    )
    with pytest.raises(ValueError):
        RecommendedActions(duplicated)


# --- TC-SFV-D-034: 文言の上書きは action のみ差し替わる ---


def test_d034_with_action_texts_replaces_only_action_of_target_quadrant():
    overridden = DEFAULT_RECOMMENDED_ACTIONS.with_action_texts({KEY_LOW_FLOW_NO_INCOMING: "X"})

    before = DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_LOW_FLOW_NO_INCOMING)
    after = overridden.for_quadrant(QUADRANT_LOW_FLOW_NO_INCOMING)
    assert after.action == "X"
    assert after.status_template == before.status_template
    assert after.departments == before.departments

    for quadrant in (QUADRANT_DORMANT_STOCK, QUADRANT_LOW_FLOW_NO_SHIPMENT, QUADRANT_NORMAL_FLOW):
        assert overridden.for_quadrant(quadrant) == DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(quadrant)


def test_d034_with_action_texts_does_not_mutate_default():
    DEFAULT_RECOMMENDED_ACTIONS.with_action_texts({KEY_LOW_FLOW_NO_INCOMING: "X"})
    assert DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_LOW_FLOW_NO_INCOMING).action != "X"


# --- TC-SFV-D-035: 上書きの未知キーは無視 ---


def test_d035_unknown_override_key_is_ignored():
    overridden = DEFAULT_RECOMMENDED_ACTIONS.with_action_texts({"foo": "X", "supply-risk": "Y"})
    assert overridden == DEFAULT_RECOMMENDED_ACTIONS


def test_d035_empty_overrides_keep_default():
    assert DEFAULT_RECOMMENDED_ACTIONS.with_action_texts({}) == DEFAULT_RECOMMENDED_ACTIONS


# --- TC-SFV-D-036: 状況の描画（入荷なし） ---


def test_d036_render_status_low_flow_no_incoming_includes_last_incoming_and_period():
    text = _render(QUADRANT_LOW_FLOW_NO_INCOMING)
    assert f"最終入荷 {LAST_INCOMING}" in text
    assert PERIOD_Y1.label in text
    assert "{" not in text and "}" not in text


def test_d036_render_status_uses_selected_period_label():
    action = DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_LOW_FLOW_NO_INCOMING)
    text = render_status(
        action,
        period=EvaluationPeriod(5),
        last_incoming=LAST_INCOMING,
        last_ship=LAST_SHIP,
        no_incoming_record=False,
    )
    assert "5年" in text
    assert "1年" not in text


# --- TC-SFV-D-037: 入荷実績なしは日付の代わりに文言 ---


def test_d037_no_incoming_record_replaces_last_incoming_with_wording():
    text = _render(QUADRANT_LOW_FLOW_NO_INCOMING, last_incoming="", no_incoming_record=True)
    assert "入荷実績なし" in text
    assert "{last_incoming}" not in text
    assert "最終入荷 （" not in text


def test_d037_no_incoming_record_also_applies_to_dormant_stock():
    text = _render(QUADRANT_DORMANT_STOCK, last_incoming="", no_incoming_record=True)
    assert "入荷実績なし" in text
    assert "{" not in text and "}" not in text


# --- TC-SFV-D-038: 状況の描画（出荷なし・死蔵） ---


def test_d038_render_status_low_flow_no_shipment_includes_last_ship():
    text = _render(QUADRANT_LOW_FLOW_NO_SHIPMENT)
    assert LAST_SHIP in text
    assert PERIOD_Y1.label in text
    assert "{" not in text and "}" not in text


def test_d038_render_status_dormant_stock_includes_both_dates():
    text = _render(QUADRANT_DORMANT_STOCK)
    assert LAST_INCOMING in text
    assert LAST_SHIP in text
    assert PERIOD_Y1.label in text
    assert "{" not in text and "}" not in text


# --- TC-FQR-A-002: 新 3 区分の状況テンプレートと新プレースホルダ ---


def test_fqr_a002_stockout_no_incoming_status_fills_recent_days_with_default():
    text = _render(QUADRANT_STOCKOUT_NO_INCOMING)

    assert f"最終入荷 {LAST_INCOMING}" in text
    assert f"直近 {DEFAULT_RECENT_INCOMING_DAYS} 日入荷なし" in text
    assert "{" not in text and "}" not in text


def test_fqr_a002_discontinuation_candidate_status_has_no_demand_window():
    """需要の判定は内示のみになったため、状況から「{demand_window}か月以上出荷なし」を外す（07 REQ-FQR-F-002）。"""
    template = DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_DISCONTINUATION_CANDIDATE).status_template
    assert template == "在庫なし・内示なし（最終出荷 {last_ship}）"

    text = _render(QUADRANT_DISCONTINUATION_CANDIDATE)
    assert text == f"在庫なし・内示なし（最終出荷 {LAST_SHIP}）"
    assert "{" not in text and "}" not in text
    assert not hasattr(module, "PLACEHOLDER_DEMAND_WINDOW")


def test_fqr_a002_stockout_status_includes_both_dates():
    text = _render(QUADRANT_STOCKOUT)

    assert text == f"在庫なし・入荷はあるが在庫が残らない（最終入荷 {LAST_INCOMING}・最終出荷 {LAST_SHIP}）"
    assert "{" not in text and "}" not in text


def test_fqr_a002_render_status_accepts_non_default_thresholds():
    text = render_status(
        DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_STOCKOUT_NO_INCOMING),
        period=PERIOD_Y1,
        last_incoming=LAST_INCOMING,
        last_ship=LAST_SHIP,
        no_incoming_record=False,
        recent_days=45,
    )
    assert "直近 45 日入荷なし" in text
    assert "30" not in text

    with pytest.raises(TypeError):
        render_status(
            DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_DISCONTINUATION_CANDIDATE),
            period=PERIOD_Y1,
            last_incoming=LAST_INCOMING,
            last_ship=LAST_SHIP,
            no_incoming_record=False,
            demand_window_months=6,
        )


def test_fqr_a002_stockout_quadrants_do_not_use_the_period_placeholder():
    """欠品 2 区分と打ち切り候補は判定期間によらない（S-203 補足）ため `{period}` を持たない。"""

    for quadrant in (
        QUADRANT_STOCKOUT_NO_INCOMING,
        QUADRANT_STOCKOUT,
        QUADRANT_DISCONTINUATION_CANDIDATE,
    ):
        assert "{period}" not in DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(quadrant).status_template


def test_fqr_a002_describe_status_template_fills_new_placeholders_for_the_legend():
    template = DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_STOCKOUT_NO_INCOMING).status_template
    text = describe_status_template(template)

    assert "YYYY/MM/DD" in text
    assert f"直近 {DEFAULT_RECENT_INCOMING_DAYS} 日入荷なし" in text
    assert "{" not in text and "}" not in text

    template = DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_DISCONTINUATION_CANDIDATE).status_template
    assert describe_status_template(template) == "在庫なし・内示なし（最終出荷 YYYY/MM/DD）"


# --- TC-FQR-A-004: 定義ファイルの上書きが新キーで効く ---


@pytest.mark.parametrize(
    "quadrant",
    [QUADRANT_STOCKOUT_NO_INCOMING, QUADRANT_STOCKOUT, QUADRANT_DISCONTINUATION_CANDIDATE],
)
def test_fqr_a004_with_action_texts_accepts_new_quadrant_keys(quadrant):
    key = FLOW_QUADRANT_KEYS[quadrant]
    overridden = DEFAULT_RECOMMENDED_ACTIONS.with_action_texts({key: "上書き文言"})

    after = overridden.for_quadrant(quadrant)
    before = DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(quadrant)
    assert after.action == "上書き文言"
    assert after.status_template == before.status_template
    assert after.departments == before.departments
    for other in FLOW_QUADRANTS:
        if other != quadrant:
            assert overridden.for_quadrant(other) == DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(other)
