from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    DEFAULT_DORMANT_VALUE,
    DEFAULT_FLOW_AXIS,
    DEFAULT_LOW_FLOW_VALUE,
    EVALUATION_PERIODS,
    FLOW_AXIS_DORMANT,
    FLOW_AXIS_HELP_TEXTS,
    FLOW_AXIS_LABELS,
    FLOW_AXIS_LOW_FLOW,
    FLOW_QUADRANT_KEYS,
    FLOW_QUADRANT_LABELS,
    FLOW_QUADRANT_SORT_RANK,
    FLOW_QUADRANTS,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_EXCESS_STOCK_RISK,
    QUADRANT_NORMAL_FLOW,
    QUADRANT_SUPPLY_RISK,
    REFERENCE_FLOW_SELECTION,
    EvaluationPeriod,
    FlowSelection,
    flow_quadrant_sort_rank,
    is_flow_escalated,
    is_no_incoming_record,
    is_within_evaluation_period,
    normalize_flow_quadrant,
    resolve_flow_quadrant,
    resolve_flow_quadrant_matrix,
    responsible_departments,
)

#: BOM 基準日（V-209）。低流動判定軸・3か月の境界日は 2026/5/27。
AS_OF = date(2026, 8, 27)

SELECTION_L1 = FlowSelection(EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 1))
SELECTION_L3 = FlowSelection(EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 3))
SELECTION_L6 = FlowSelection(EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 6))
SELECTION_D1 = FlowSelection(EvaluationPeriod(FLOW_AXIS_DORMANT, 1))
SELECTION_D2 = FlowSelection(EvaluationPeriod(FLOW_AXIS_DORMANT, 2))
SELECTION_D5 = FlowSelection(EvaluationPeriod(FLOW_AXIS_DORMANT, 5))
ALL_SELECTIONS = (
    SELECTION_L1,
    SELECTION_L3,
    SELECTION_L6,
    SELECTION_D1,
    SELECTION_D2,
    SELECTION_D5,
)

#: (最終入荷日, 最終出荷日, 在庫数)
ROW_SUPPLY_RISK = (date(2026, 1, 10), date(2026, 8, 1), 500)
ROW_SUPPLY_RISK_NO_INCOMING = (None, date(2026, 8, 1), 120)
ROW_DORMANT_STOCK = (date(2026, 1, 10), date(2026, 1, 20), 3000)
ROW_EXCESS_STOCK_RISK = (date(2026, 8, 1), date(2026, 1, 20), 8000)
ROW_NORMAL_FLOW = (date(2026, 8, 1), date(2026, 8, 10), 400)
ROW_BOUNDARY = (date(2026, 5, 27), date(2026, 5, 27), 100)
ALL_ROWS = (
    ROW_SUPPLY_RISK,
    ROW_SUPPLY_RISK_NO_INCOMING,
    ROW_DORMANT_STOCK,
    ROW_EXCESS_STOCK_RISK,
    ROW_NORMAL_FLOW,
    ROW_BOUNDARY,
)

PROHIBITED_TERMS = ("未流動品", "デッドストック", "不良在庫", "象限")


def _resolve(row, selection):
    last_incoming_date, last_ship_date, _stock_qty = row
    return resolve_flow_quadrant(
        last_incoming_date,
        last_ship_date,
        as_of_date=AS_OF,
        selection=selection,
    )


# --- D-001〜D-017: EvaluationPeriod / EvaluationPeriods（V-211 判定期間） ---


def test_evaluation_period_months_for_low_flow_axis_equals_value():
    period = EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 3)

    assert period.months == 3


def test_evaluation_period_months_for_dormant_axis_multiplies_by_twelve():
    period = EvaluationPeriod(FLOW_AXIS_DORMANT, 5)

    assert period.months == 60


def test_evaluation_period_key_prefixes_axis_initial():
    low_flow = EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 3)
    dormant = EvaluationPeriod(FLOW_AXIS_DORMANT, 1)

    assert low_flow.key == "L3"
    assert dormant.key == "D1"


def test_evaluation_period_label_uses_month_unit_for_low_flow_axis():
    period = EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 6)

    assert period.label == "6か月"


def test_evaluation_period_label_uses_year_unit_for_dormant_axis():
    period = EvaluationPeriod(FLOW_AXIS_DORMANT, 2)

    assert period.label == "2年"


def test_evaluation_periods_for_low_flow_axis_returns_one_three_six_in_order():
    periods = EVALUATION_PERIODS.for_axis(FLOW_AXIS_LOW_FLOW)

    assert tuple(period.value for period in periods) == (1, 3, 6)


def test_evaluation_periods_for_dormant_axis_returns_one_two_five_in_order():
    periods = EVALUATION_PERIODS.for_axis(FLOW_AXIS_DORMANT)

    assert tuple(period.value for period in periods) == (1, 2, 5)


def test_evaluation_periods_for_unknown_axis_returns_empty():
    periods = EVALUATION_PERIODS.for_axis("foo")

    assert periods == ()


def test_evaluation_periods_default_for_low_flow_axis_is_three_months():
    period = EVALUATION_PERIODS.default_for_axis(FLOW_AXIS_LOW_FLOW)

    assert period == EvaluationPeriod(FLOW_AXIS_LOW_FLOW, DEFAULT_LOW_FLOW_VALUE)
    assert period.value == 3


def test_evaluation_periods_default_for_dormant_axis_is_one_year():
    period = EVALUATION_PERIODS.default_for_axis(FLOW_AXIS_DORMANT)

    assert period == EvaluationPeriod(FLOW_AXIS_DORMANT, DEFAULT_DORMANT_VALUE)
    assert period.value == 1


def test_evaluation_periods_default_for_unknown_axis_falls_back_to_low_flow_three_months():
    period = EVALUATION_PERIODS.default_for_axis("foo")

    assert period == EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 3)


def test_evaluation_periods_find_returns_period_for_known_key():
    period = EVALUATION_PERIODS.find("D5")

    assert period == EvaluationPeriod(FLOW_AXIS_DORMANT, 5)


def test_evaluation_periods_find_returns_none_for_undefined_key():
    assert EVALUATION_PERIODS.find("L2") is None


def test_evaluation_periods_find_returns_none_for_empty_key():
    assert EVALUATION_PERIODS.find("") is None


def test_evaluation_periods_contains_exactly_six_fixed_values():
    keys = [period.key for period in EVALUATION_PERIODS]

    assert len(EVALUATION_PERIODS) == 6
    assert keys == ["L1", "L3", "L6", "D1", "D2", "D5"]


def test_evaluation_period_with_same_axis_and_value_are_equal():
    one = EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 3)
    other = EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 3)

    assert one == other
    assert len({one, other}) == 1


def test_evaluation_period_is_immutable():
    period = EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 3)

    with pytest.raises(FrozenInstanceError):
        period.value = 6


# --- D-018〜D-019: FlowAxis（V-210 判定軸） ---


def test_flow_axis_labels_map_to_ubiquitous_language_terms():
    assert FLOW_AXIS_LABELS == {
        FLOW_AXIS_LOW_FLOW: "低流動判定軸",
        FLOW_AXIS_DORMANT: "死蔵判定軸",
    }


def test_default_flow_axis_is_low_flow():
    assert DEFAULT_FLOW_AXIS == FLOW_AXIS_LOW_FLOW
    assert DEFAULT_FLOW_AXIS == "low_flow"


# --- D-020〜D-022: FlowSelection（判定条件の組） ---


def test_flow_selection_exposes_axis_key_and_labels():
    selection = FlowSelection(EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 3))

    assert selection.axis == FLOW_AXIS_LOW_FLOW
    assert selection.key == "L3"
    assert selection.axis_label == "低流動判定軸"
    assert selection.period_label == "3か月"


def test_reference_flow_selection_is_low_flow_axis_three_months():
    assert REFERENCE_FLOW_SELECTION.axis == FLOW_AXIS_LOW_FLOW
    assert REFERENCE_FLOW_SELECTION.period.value == 3
    assert REFERENCE_FLOW_SELECTION.key == "L3"


def test_flow_selection_with_same_period_are_equal():
    one = FlowSelection(EvaluationPeriod(FLOW_AXIS_DORMANT, 1))
    other = FlowSelection(EvaluationPeriod(FLOW_AXIS_DORMANT, 1))

    assert one == other


# --- D-023〜D-028: FlowQuadrant（S-203 流動区分） ---


def test_flow_quadrant_keys_map_label_to_ascii_key():
    assert FLOW_QUADRANT_KEYS == {
        QUADRANT_SUPPLY_RISK: "supply-risk",
        QUADRANT_DORMANT_STOCK: "dormant-stock",
        QUADRANT_EXCESS_STOCK_RISK: "excess-stock-risk",
        QUADRANT_NORMAL_FLOW: "normal-flow",
    }


def test_flow_quadrant_labels_are_inverse_of_keys():
    assert len(FLOW_QUADRANT_KEYS) == 4
    assert len(FLOW_QUADRANT_LABELS) == 4
    assert FLOW_QUADRANT_LABELS == {key: label for label, key in FLOW_QUADRANT_KEYS.items()}


def test_flow_quadrants_are_ordered_by_urgency():
    assert FLOW_QUADRANTS == (
        QUADRANT_SUPPLY_RISK,
        QUADRANT_DORMANT_STOCK,
        QUADRANT_EXCESS_STOCK_RISK,
        QUADRANT_NORMAL_FLOW,
    )


def test_flow_quadrant_sort_rank_assigns_zero_to_supply_risk():
    ranks = [FLOW_QUADRANT_SORT_RANK[quadrant] for quadrant in FLOW_QUADRANTS]

    assert ranks == [0, 1, 2, 3]
    assert flow_quadrant_sort_rank(QUADRANT_SUPPLY_RISK) == 0
    assert flow_quadrant_sort_rank(QUADRANT_NORMAL_FLOW) == 3


def test_flow_quadrant_labels_do_not_contain_prohibited_terms():
    texts = list(FLOW_QUADRANTS) + list(FLOW_AXIS_LABELS.values()) + list(FLOW_AXIS_HELP_TEXTS.values())

    for text in texts:
        for term in PROHIBITED_TERMS:
            assert term not in text


def test_longest_flow_quadrant_label_fits_confirmation_field_length():
    assert max(len(quadrant) for quadrant in FLOW_QUADRANTS) <= 40


# --- D-029〜D-040: is_within_evaluation_period（V-212 期間内入荷 / V-213 期間内出荷） ---


def test_is_within_evaluation_period_returns_false_for_missing_date():
    assert is_within_evaluation_period(None, as_of_date=AS_OF, months=3) is False


def test_is_within_evaluation_period_returns_true_on_exact_boundary_date():
    assert is_within_evaluation_period(date(2026, 5, 27), as_of_date=AS_OF, months=3) is True


def test_is_within_evaluation_period_returns_false_one_day_before_boundary():
    assert is_within_evaluation_period(date(2026, 5, 26), as_of_date=AS_OF, months=3) is False


def test_is_within_evaluation_period_returns_true_for_bom_reference_date_itself():
    assert is_within_evaluation_period(AS_OF, as_of_date=AS_OF, months=3) is True


def test_is_within_evaluation_period_returns_true_for_future_date():
    assert is_within_evaluation_period(date(2026, 12, 1), as_of_date=AS_OF, months=3) is True


def test_is_within_evaluation_period_rounds_month_end_to_shorter_month():
    as_of = date(2026, 8, 31)

    assert is_within_evaluation_period(date(2026, 2, 28), as_of_date=as_of, months=6) is True


def test_is_within_evaluation_period_excludes_day_before_rounded_month_end():
    as_of = date(2026, 8, 31)

    assert is_within_evaluation_period(date(2026, 2, 27), as_of_date=as_of, months=6) is False


def test_is_within_evaluation_period_rounds_month_end_to_leap_day():
    as_of = date(2024, 8, 31)

    assert is_within_evaluation_period(date(2024, 2, 29), as_of_date=as_of, months=6) is True


def test_is_within_evaluation_period_handles_one_month_minimum():
    assert is_within_evaluation_period(date(2026, 7, 27), as_of_date=AS_OF, months=1) is True


def test_is_within_evaluation_period_handles_sixty_months_for_five_years():
    assert is_within_evaluation_period(date(2021, 8, 27), as_of_date=AS_OF, months=60) is True


def test_is_within_evaluation_period_excludes_day_before_five_year_boundary():
    assert is_within_evaluation_period(date(2021, 8, 26), as_of_date=AS_OF, months=60) is False


def test_is_within_evaluation_period_crosses_year_boundary():
    as_of = date(2026, 1, 15)

    assert is_within_evaluation_period(date(2025, 10, 15), as_of_date=as_of, months=3) is True


# --- D-041〜D-053: resolve_flow_quadrant（REQ-LFV-F-001） ---


def test_resolve_flow_quadrant_returns_supply_risk_when_incoming_absent_and_shipment_present():
    assert _resolve(ROW_SUPPLY_RISK, SELECTION_L3) == QUADRANT_SUPPLY_RISK


def test_resolve_flow_quadrant_returns_dormant_stock_when_both_absent():
    assert _resolve(ROW_DORMANT_STOCK, SELECTION_L3) == QUADRANT_DORMANT_STOCK


def test_resolve_flow_quadrant_returns_excess_stock_risk_when_incoming_present_and_shipment_absent():
    assert _resolve(ROW_EXCESS_STOCK_RISK, SELECTION_L3) == QUADRANT_EXCESS_STOCK_RISK


def test_resolve_flow_quadrant_returns_normal_flow_when_both_present():
    assert _resolve(ROW_NORMAL_FLOW, SELECTION_L3) == QUADRANT_NORMAL_FLOW


def test_resolve_flow_quadrant_returns_dormant_stock_when_both_dates_are_none():
    quadrant = resolve_flow_quadrant(None, None, as_of_date=AS_OF, selection=SELECTION_L3)

    assert quadrant == QUADRANT_DORMANT_STOCK


def test_resolve_flow_quadrant_returns_supply_risk_when_incoming_date_is_none_and_shipment_recent():
    assert _resolve(ROW_SUPPLY_RISK_NO_INCOMING, SELECTION_L3) == QUADRANT_SUPPLY_RISK


def test_resolve_flow_quadrant_returns_dormant_stock_when_shipment_date_is_none_and_incoming_old():
    quadrant = resolve_flow_quadrant(
        date(2026, 1, 10), None, as_of_date=AS_OF, selection=SELECTION_L3
    )

    assert quadrant == QUADRANT_DORMANT_STOCK


def test_resolve_flow_quadrant_returns_excess_stock_risk_when_shipment_date_is_none_and_incoming_recent():
    quadrant = resolve_flow_quadrant(
        date(2026, 8, 1), None, as_of_date=AS_OF, selection=SELECTION_L3
    )

    assert quadrant == QUADRANT_EXCESS_STOCK_RISK


def test_resolve_flow_quadrant_classifies_boundary_dates_as_within_period():
    assert _resolve(ROW_BOUNDARY, SELECTION_L3) == QUADRANT_NORMAL_FLOW


def test_resolve_flow_quadrant_widening_period_changes_dormant_stock_to_normal_flow():
    row = (date(2026, 4, 1), date(2026, 4, 1), 10)

    assert _resolve(row, SELECTION_L1) == QUADRANT_DORMANT_STOCK
    assert _resolve(row, SELECTION_L6) == QUADRANT_NORMAL_FLOW


def test_resolve_flow_quadrant_differs_between_low_flow_and_dormant_axis():
    row = (date(2025, 1, 10), date(2025, 1, 10), 10)

    assert _resolve(row, SELECTION_L3) == QUADRANT_DORMANT_STOCK
    assert _resolve(row, SELECTION_D5) == QUADRANT_NORMAL_FLOW


def test_resolve_flow_quadrant_ignores_stock_quantity():
    low_stock = (date(2026, 8, 1), date(2026, 1, 20), 1)
    high_stock = (date(2026, 8, 1), date(2026, 1, 20), 99999)

    assert _resolve(low_stock, SELECTION_L3) == _resolve(high_stock, SELECTION_L3)
    assert not any("stock" in name for name in inspect.signature(resolve_flow_quadrant).parameters)


def test_resolve_flow_quadrant_returns_one_of_four_labels_for_all_input_combinations():
    for row in ALL_ROWS:
        for selection in ALL_SELECTIONS:
            assert _resolve(row, selection) in FLOW_QUADRANTS


# --- D-054〜D-057: resolve_flow_quadrant_matrix（§3.2 案B） ---


def test_resolve_flow_quadrant_matrix_contains_all_six_period_keys():
    matrix = resolve_flow_quadrant_matrix(date(2026, 1, 10), date(2026, 8, 1), as_of_date=AS_OF)

    assert sorted(matrix) == sorted(["L1", "L3", "L6", "D1", "D2", "D5"])


def test_resolve_flow_quadrant_matrix_values_are_ascii_keys():
    matrix = resolve_flow_quadrant_matrix(date(2026, 1, 10), date(2026, 8, 1), as_of_date=AS_OF)

    for value in matrix.values():
        assert value.isascii()
        assert value in FLOW_QUADRANT_LABELS


def test_resolve_flow_quadrant_matrix_matches_resolve_flow_quadrant_for_every_period():
    for row in ALL_ROWS:
        last_incoming_date, last_ship_date, _stock_qty = row
        matrix = resolve_flow_quadrant_matrix(
            last_incoming_date, last_ship_date, as_of_date=AS_OF
        )
        for selection in ALL_SELECTIONS:
            assert matrix[selection.key] == FLOW_QUADRANT_KEYS[_resolve(row, selection)]


def test_resolve_flow_quadrant_matrix_returns_dormant_stock_for_all_periods_when_dates_are_none():
    matrix = resolve_flow_quadrant_matrix(None, None, as_of_date=AS_OF)

    assert set(matrix.values()) == {"dormant-stock"}


# --- D-058〜D-061: is_no_incoming_record（V-214 入荷実績なし） ---


def test_is_no_incoming_record_returns_true_when_last_incoming_date_is_none():
    assert is_no_incoming_record(None) is True


def test_is_no_incoming_record_returns_false_when_last_incoming_date_exists():
    assert is_no_incoming_record(date(2010, 1, 1)) is False


def test_is_no_incoming_record_does_not_depend_on_evaluation_period():
    assert list(inspect.signature(is_no_incoming_record).parameters) == ["last_incoming_date"]
    assert {is_no_incoming_record(None) for _ in ALL_SELECTIONS} == {True}


def test_no_incoming_record_can_coexist_with_non_supply_risk_quadrant():
    quadrant = resolve_flow_quadrant(None, None, as_of_date=AS_OF, selection=SELECTION_L3)

    assert quadrant == QUADRANT_DORMANT_STOCK
    assert is_no_incoming_record(None) is True


# --- D-062〜D-066: responsible_departments（R-201 責任部署） ---


def test_responsible_departments_for_supply_risk_includes_three_groups():
    assert responsible_departments(QUADRANT_SUPPLY_RISK) == ("調達G", "営業G", "生産管理")


def test_responsible_departments_for_dormant_stock_is_procurement_group():
    assert responsible_departments(QUADRANT_DORMANT_STOCK) == ("調達G",)


def test_responsible_departments_for_excess_stock_risk_is_sales_group():
    assert responsible_departments(QUADRANT_EXCESS_STOCK_RISK) == ("営業G",)


def test_responsible_departments_for_normal_flow_is_production_control():
    assert responsible_departments(QUADRANT_NORMAL_FLOW) == ("生産管理",)


def test_responsible_departments_returns_empty_for_unknown_quadrant():
    assert responsible_departments("謎") == ()


# --- D-067〜D-076: normalize_flow_quadrant（§5.2 旧ラベル互換写像） ---


def test_normalize_flow_quadrant_maps_legacy_critical_to_supply_risk():
    assert normalize_flow_quadrant("重点") == QUADRANT_SUPPLY_RISK


def test_normalize_flow_quadrant_maps_legacy_warning_no_shipment_to_excess_stock_risk():
    assert normalize_flow_quadrant("警告（出荷なし）") == QUADRANT_EXCESS_STOCK_RISK


def test_normalize_flow_quadrant_maps_legacy_warning_with_shipment_to_normal_flow():
    assert normalize_flow_quadrant("警告（出荷あり）") == QUADRANT_NORMAL_FLOW


def test_normalize_flow_quadrant_maps_legacy_no_alert_to_normal_flow():
    assert normalize_flow_quadrant("アラート無し") == QUADRANT_NORMAL_FLOW


@pytest.mark.parametrize(
    ("legacy_label", "expected"),
    [
        ("なし", QUADRANT_NORMAL_FLOW),
        ("アラートなし", QUADRANT_NORMAL_FLOW),
        ("問題なし", QUADRANT_NORMAL_FLOW),
        ("警告（出荷）", QUADRANT_NORMAL_FLOW),
        ("警告（入荷）", QUADRANT_EXCESS_STOCK_RISK),
    ],
)
def test_normalize_flow_quadrant_maps_legacy_aliases_from_alert_level_module(legacy_label, expected):
    assert normalize_flow_quadrant(legacy_label) == expected


def test_normalize_flow_quadrant_maps_empty_string_to_normal_flow():
    assert normalize_flow_quadrant("") == QUADRANT_NORMAL_FLOW


def test_normalize_flow_quadrant_maps_unknown_label_to_normal_flow():
    assert normalize_flow_quadrant("謎のラベル") == QUADRANT_NORMAL_FLOW


def test_normalize_flow_quadrant_keeps_current_quadrant_labels_unchanged():
    for quadrant in FLOW_QUADRANTS:
        assert normalize_flow_quadrant(quadrant) == quadrant


def test_normalize_flow_quadrant_trims_surrounding_whitespace():
    assert normalize_flow_quadrant("  重点  ") == QUADRANT_SUPPLY_RISK


def test_normalize_flow_quadrant_accepts_none():
    assert normalize_flow_quadrant(None) == QUADRANT_NORMAL_FLOW


# --- D-077〜D-083: is_flow_escalated（REQ-LFV-F-014 深刻化判定） ---


def test_is_flow_escalated_returns_true_when_rank_rises_from_normal_flow_to_supply_risk():
    assert is_flow_escalated(QUADRANT_NORMAL_FLOW, QUADRANT_SUPPLY_RISK) is True


def test_is_flow_escalated_returns_true_when_rank_rises_from_dormant_stock_to_supply_risk():
    assert is_flow_escalated(QUADRANT_DORMANT_STOCK, QUADRANT_SUPPLY_RISK) is True


def test_is_flow_escalated_returns_true_when_rank_rises_from_excess_stock_risk_to_dormant_stock():
    assert is_flow_escalated(QUADRANT_EXCESS_STOCK_RISK, QUADRANT_DORMANT_STOCK) is True


def test_is_flow_escalated_returns_false_when_rank_falls():
    assert is_flow_escalated(QUADRANT_SUPPLY_RISK, QUADRANT_NORMAL_FLOW) is False


def test_is_flow_escalated_returns_false_for_same_quadrant():
    assert is_flow_escalated(QUADRANT_SUPPLY_RISK, QUADRANT_SUPPLY_RISK) is False


def test_is_flow_escalated_normalizes_legacy_previous_label_before_comparing():
    assert is_flow_escalated("重点", QUADRANT_NORMAL_FLOW) is False


def test_is_flow_escalated_treats_unknown_previous_label_as_normal_flow():
    assert is_flow_escalated("謎", QUADRANT_SUPPLY_RISK) is True
