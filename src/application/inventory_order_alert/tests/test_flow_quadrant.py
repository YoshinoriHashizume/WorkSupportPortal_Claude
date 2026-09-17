"""判定期間（V-211）・流動区分（S-203）のテスト（test-design.md TC-SFV-D-001〜025）。

05_single-flow-view で判定軸（V-210）を廃止し、判定期間を 1/3/5 年に一本化した。
流動区分は 在庫死蔵品 / 低流動品（入荷なし） / 低流動品（出荷なし） / 通常流動品 の 4 値。
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from application.inventory_order_alert.domain.value_objects import flow_quadrant as module
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    DEFAULT_EVALUATION_PERIOD,
    EVALUATION_PERIOD_YEARS,
    EVALUATION_PERIODS,
    FLOW_QUADRANT_KEYS,
    FLOW_QUADRANT_LABELS,
    FLOW_QUADRANT_SORT_RANK,
    FLOW_QUADRANTS,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_INCOMING,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
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

#: BOM 基準日（V-209）。2026/09/07 取込の実データに合わせる。1 年の境界日は 2025/09/07。
AS_OF = date(2026, 9, 7)

SELECTION_Y1 = FlowSelection(EvaluationPeriod(1))
SELECTION_Y3 = FlowSelection(EvaluationPeriod(3))
SELECTION_Y5 = FlowSelection(EvaluationPeriod(5))
ALL_SELECTIONS = (SELECTION_Y1, SELECTION_Y3, SELECTION_Y5)

#: 96160-00500（得意先 100）の実データ: 最終入荷 2025/04/02、最終出荷 2023/07/27（受け入れ基準 #2）。
ROW_96160_00500 = (date(2025, 4, 2), date(2023, 7, 27))

PROHIBITED_TERMS = ("未流動品", "デッドストック", "不良在庫", "象限", "供給リスク品", "在庫過剰リスク品")


def _resolve(last_incoming_date, last_ship_date, selection):
    return resolve_flow_quadrant(
        last_incoming_date,
        last_ship_date,
        as_of_date=AS_OF,
        selection=selection,
    )


# --- TC-SFV-D-001〜006: EvaluationPeriod / EvaluationPeriods（V-211 判定期間） ---


@pytest.mark.parametrize(
    ("years", "months", "key", "label"),
    [(1, 12, "Y1", "1年"), (3, 36, "Y3", "3年"), (5, 60, "Y5", "5年")],
)
def test_D001_evaluation_period_can_be_created_for_one_three_five_years(years, months, key, label):
    period = EvaluationPeriod(years)

    assert period.months == months
    assert period.key == key
    assert period.label == label


@pytest.mark.parametrize("years", [2, 6, 0, -1])
def test_D002_evaluation_period_rejects_years_other_than_one_three_five(years):
    with pytest.raises(ValueError):
        EvaluationPeriod(years)


def test_D002_evaluation_period_years_constant_is_one_three_five():
    assert EVALUATION_PERIOD_YEARS == (1, 3, 5)


def test_D003_evaluation_period_with_same_years_are_equal():
    assert EvaluationPeriod(3) == EvaluationPeriod(3)
    assert EvaluationPeriod(3) != EvaluationPeriod(5)


def test_D003_evaluation_period_is_immutable():
    period = EvaluationPeriod(3)

    with pytest.raises(FrozenInstanceError):
        period.years = 5  # type: ignore[misc]


def test_D004_evaluation_periods_contains_exactly_three_fixed_values_in_order():
    assert [period.years for period in EVALUATION_PERIODS] == [1, 3, 5]
    assert len(EVALUATION_PERIODS) == 3


def test_D004_evaluation_periods_default_is_one_year():
    assert EVALUATION_PERIODS.default == EvaluationPeriod(1)
    assert DEFAULT_EVALUATION_PERIOD == EvaluationPeriod(1)


def test_D004_evaluation_periods_find_by_key():
    assert EVALUATION_PERIODS.find("Y3") == EvaluationPeriod(3)
    assert EVALUATION_PERIODS.find("L3") is None
    assert EVALUATION_PERIODS.find("D1") is None
    assert EVALUATION_PERIODS.find("") is None


def test_D004_evaluation_periods_find_by_years():
    assert EVALUATION_PERIODS.find_by_years(5) == EvaluationPeriod(5)
    assert EVALUATION_PERIODS.find_by_years(2) is None
    assert EVALUATION_PERIODS.find_by_years(6) is None


@pytest.mark.parametrize(
    "name",
    [
        "FLOW_AXIS_LOW_FLOW",
        "FLOW_AXIS_DORMANT",
        "FLOW_AXIS_LABELS",
        "FLOW_AXIS_HELP_TEXTS",
        "DEFAULT_FLOW_AXIS",
        "DEFAULT_LOW_FLOW_VALUE",
        "DEFAULT_DORMANT_VALUE",
    ],
)
def test_D005_flow_axis_constants_are_removed(name):
    assert not hasattr(module, name)


def test_D005_flow_axis_methods_are_removed():
    assert not hasattr(EVALUATION_PERIODS, "for_axis")
    assert not hasattr(EVALUATION_PERIODS, "default_for_axis")
    assert not hasattr(EvaluationPeriod(1), "axis")
    assert not hasattr(SELECTION_Y1, "axis")
    assert not hasattr(SELECTION_Y1, "axis_label")


def test_D005_flow_selection_exposes_key_and_period_label():
    assert SELECTION_Y3.key == "Y3"
    assert SELECTION_Y3.period_label == "3年"


def test_D006_reference_flow_selection_is_default_one_year():
    assert REFERENCE_FLOW_SELECTION.period == DEFAULT_EVALUATION_PERIOD
    assert REFERENCE_FLOW_SELECTION.period.years == 1


# --- TC-SFV-D-010〜018: 流動区分の判定（S-203） ---


def test_D010_no_incoming_with_shipment_is_low_flow_no_incoming():
    quadrant = _resolve(date(2025, 4, 2), date(2026, 6, 1), SELECTION_Y1)

    assert quadrant == QUADRANT_LOW_FLOW_NO_INCOMING


def test_D011_incoming_without_shipment_is_low_flow_no_shipment():
    quadrant = _resolve(*ROW_96160_00500, SELECTION_Y3)

    assert quadrant == QUADRANT_LOW_FLOW_NO_SHIPMENT


def test_D012_neither_incoming_nor_shipment_is_dormant_stock():
    quadrant = _resolve(*ROW_96160_00500, SELECTION_Y1)

    assert quadrant == QUADRANT_DORMANT_STOCK


def test_D013_both_incoming_and_shipment_is_normal_flow():
    quadrant = _resolve(*ROW_96160_00500, SELECTION_Y5)

    assert quadrant == QUADRANT_NORMAL_FLOW


def test_D014_acceptance_criteria_2_for_96160_00500():
    """受け入れ基準 #2: 1 年で在庫死蔵品、3 年で低流動品（出荷なし）、5 年で通常流動品。"""
    assert _resolve(*ROW_96160_00500, SELECTION_Y1) == QUADRANT_DORMANT_STOCK
    assert _resolve(*ROW_96160_00500, SELECTION_Y3) == QUADRANT_LOW_FLOW_NO_SHIPMENT
    assert _resolve(*ROW_96160_00500, SELECTION_Y5) == QUADRANT_NORMAL_FLOW


def test_D015_exact_boundary_date_is_within_period():
    assert is_within_evaluation_period(date(2025, 9, 7), as_of_date=AS_OF, months=12) is True


def test_D015_resolve_treats_boundary_dates_as_within_period():
    quadrant = _resolve(date(2025, 9, 7), date(2025, 9, 7), SELECTION_Y1)

    assert quadrant == QUADRANT_NORMAL_FLOW


def test_D016_day_before_boundary_is_outside_period():
    assert is_within_evaluation_period(date(2025, 9, 6), as_of_date=AS_OF, months=12) is False


def test_D017_future_date_is_within_period():
    assert is_within_evaluation_period(date(2027, 1, 1), as_of_date=AS_OF, months=12) is True


def test_D017_missing_date_is_outside_period():
    assert is_within_evaluation_period(None, as_of_date=AS_OF, months=12) is False


def test_D017_both_dates_none_is_dormant_stock_for_every_period():
    for selection in ALL_SELECTIONS:
        assert _resolve(None, None, selection) == QUADRANT_DORMANT_STOCK


def test_D017_incoming_none_with_recent_shipment_is_low_flow_no_incoming():
    assert _resolve(None, date(2026, 8, 1), SELECTION_Y1) == QUADRANT_LOW_FLOW_NO_INCOMING


def test_D017_shipment_none_with_recent_incoming_is_low_flow_no_shipment():
    assert _resolve(date(2026, 8, 1), None, SELECTION_Y1) == QUADRANT_LOW_FLOW_NO_SHIPMENT


# 判定規則（月末丸め・うるう日・年またぎ）は 02 から引き継ぐ。年数化しても月数計算は同じ。


def test_is_within_evaluation_period_rounds_month_end_to_shorter_month():
    as_of = date(2026, 8, 31)

    assert is_within_evaluation_period(date(2025, 2, 28), as_of_date=as_of, months=18) is True


def test_is_within_evaluation_period_rounds_month_end_to_leap_day():
    as_of = date(2025, 2, 28)

    assert is_within_evaluation_period(date(2024, 2, 28), as_of_date=as_of, months=12) is True
    assert is_within_evaluation_period(date(2024, 2, 27), as_of_date=as_of, months=12) is False


def test_is_within_evaluation_period_handles_sixty_months_for_five_years():
    assert is_within_evaluation_period(date(2021, 9, 7), as_of_date=AS_OF, months=60) is True
    assert is_within_evaluation_period(date(2021, 9, 6), as_of_date=AS_OF, months=60) is False


def test_resolve_flow_quadrant_ignores_stock_quantity_because_it_takes_no_stock_argument():
    """在庫数は判定に用いない（S-203 補足）。引数にすら存在しないことで担保する。"""
    import inspect

    assert "stock" not in " ".join(inspect.signature(resolve_flow_quadrant).parameters)


def test_resolve_flow_quadrant_returns_one_of_four_labels_for_all_input_combinations():
    dates = (None, date(2020, 1, 1), date(2026, 8, 1), date(2027, 1, 1))
    for incoming in dates:
        for shipment in dates:
            for selection in ALL_SELECTIONS:
                assert _resolve(incoming, shipment, selection) in FLOW_QUADRANTS


def test_D018_matrix_contains_exactly_year_keys():
    matrix = resolve_flow_quadrant_matrix(*ROW_96160_00500, as_of_date=AS_OF)

    assert set(matrix) == {"Y1", "Y3", "Y5"}


def test_D018_matrix_values_are_new_ascii_keys_and_match_resolve():
    matrix = resolve_flow_quadrant_matrix(*ROW_96160_00500, as_of_date=AS_OF)

    assert matrix == {
        "Y1": "dormant-stock",
        "Y3": "low-flow-no-shipment",
        "Y5": "normal-flow",
    }
    for selection in ALL_SELECTIONS:
        assert matrix[selection.key] == FLOW_QUADRANT_KEYS[_resolve(*ROW_96160_00500, selection)]


# --- TC-SFV-D-019〜025: ラベル・キー・ランク・正規化・深刻化・責任部署 ---


def test_flow_quadrant_keys_are_new_ascii_keys():
    assert FLOW_QUADRANT_KEYS == {
        QUADRANT_LOW_FLOW_NO_INCOMING: "low-flow-no-incoming",
        QUADRANT_DORMANT_STOCK: "dormant-stock",
        QUADRANT_LOW_FLOW_NO_SHIPMENT: "low-flow-no-shipment",
        QUADRANT_NORMAL_FLOW: "normal-flow",
    }
    assert FLOW_QUADRANT_LABELS == {key: label for label, key in FLOW_QUADRANT_KEYS.items()}


def test_flow_quadrant_labels_use_ubiquitous_language():
    assert QUADRANT_LOW_FLOW_NO_INCOMING == "低流動品（入荷なし）"
    assert QUADRANT_LOW_FLOW_NO_SHIPMENT == "低流動品（出荷なし）"
    assert QUADRANT_DORMANT_STOCK == "在庫死蔵品"
    assert QUADRANT_NORMAL_FLOW == "通常流動品"


def test_flow_quadrant_labels_do_not_contain_prohibited_terms():
    for label in FLOW_QUADRANTS:
        for term in PROHIBITED_TERMS:
            assert term not in label


def test_longest_flow_quadrant_label_fits_confirmation_field_length():
    """確認記録の confirmed_flow_quadrant は max_length=40。"""
    assert max(len(label) for label in FLOW_QUADRANTS) <= 40


def test_D019_sort_rank_is_no_incoming_dormant_no_shipment_normal():
    assert FLOW_QUADRANT_SORT_RANK == {
        QUADRANT_LOW_FLOW_NO_INCOMING: 0,
        QUADRANT_DORMANT_STOCK: 1,
        QUADRANT_LOW_FLOW_NO_SHIPMENT: 2,
        QUADRANT_NORMAL_FLOW: 3,
    }
    assert FLOW_QUADRANTS == (
        QUADRANT_LOW_FLOW_NO_INCOMING,
        QUADRANT_DORMANT_STOCK,
        QUADRANT_LOW_FLOW_NO_SHIPMENT,
        QUADRANT_NORMAL_FLOW,
    )
    assert [flow_quadrant_sort_rank(label) for label in FLOW_QUADRANTS] == [0, 1, 2, 3]


@pytest.mark.parametrize(
    ("legacy_label", "expected"),
    [
        ("供給リスク品", QUADRANT_LOW_FLOW_NO_INCOMING),
        ("在庫過剰リスク品", QUADRANT_LOW_FLOW_NO_SHIPMENT),
        ("重点", QUADRANT_LOW_FLOW_NO_INCOMING),
        ("警告（出荷なし）", QUADRANT_LOW_FLOW_NO_SHIPMENT),
        ("警告（入荷）", QUADRANT_LOW_FLOW_NO_SHIPMENT),
        ("警告（出荷あり）", QUADRANT_NORMAL_FLOW),
        ("警告（出荷）", QUADRANT_NORMAL_FLOW),
        ("アラート無し", QUADRANT_NORMAL_FLOW),
        ("アラートなし", QUADRANT_NORMAL_FLOW),
        ("なし", QUADRANT_NORMAL_FLOW),
        ("問題なし", QUADRANT_NORMAL_FLOW),
    ],
)
def test_D020_normalize_maps_legacy_labels_to_new_quadrants(legacy_label, expected):
    assert normalize_flow_quadrant(legacy_label) == expected


@pytest.mark.parametrize(
    ("legacy_key", "expected"),
    [
        ("supply-risk", QUADRANT_LOW_FLOW_NO_INCOMING),
        ("excess-stock-risk", QUADRANT_LOW_FLOW_NO_SHIPMENT),
        ("dormant-stock", QUADRANT_DORMANT_STOCK),
        ("normal-flow", QUADRANT_NORMAL_FLOW),
        ("low-flow-no-incoming", QUADRANT_LOW_FLOW_NO_INCOMING),
        ("low-flow-no-shipment", QUADRANT_LOW_FLOW_NO_SHIPMENT),
    ],
)
def test_D021_normalize_maps_keys_to_labels(legacy_key, expected):
    assert normalize_flow_quadrant(legacy_key) == expected


@pytest.mark.parametrize("value", ["象限1", "", None, "  ", "unknown"])
def test_D022_normalize_maps_unknown_values_to_normal_flow(value):
    assert normalize_flow_quadrant(value) == QUADRANT_NORMAL_FLOW


def test_D022_normalize_keeps_current_labels_and_trims_whitespace():
    for label in FLOW_QUADRANTS:
        assert normalize_flow_quadrant(label) == label
        assert normalize_flow_quadrant(f"  {label}  ") == label


def test_D023_escalation_is_true_only_when_rank_decreases():
    assert is_flow_escalated(QUADRANT_DORMANT_STOCK, QUADRANT_LOW_FLOW_NO_INCOMING) is True
    assert is_flow_escalated(QUADRANT_NORMAL_FLOW, QUADRANT_DORMANT_STOCK) is True
    assert is_flow_escalated(QUADRANT_NORMAL_FLOW, QUADRANT_LOW_FLOW_NO_SHIPMENT) is True
    assert is_flow_escalated(QUADRANT_LOW_FLOW_NO_INCOMING, QUADRANT_DORMANT_STOCK) is False
    assert is_flow_escalated(QUADRANT_LOW_FLOW_NO_INCOMING, QUADRANT_LOW_FLOW_NO_INCOMING) is False


def test_D023_escalation_normalizes_legacy_saved_label():
    """確認記録に旧称が残っていても、新区分へ写像して比較する（REQ-SFV-F-017）。"""
    assert is_flow_escalated("供給リスク品", QUADRANT_LOW_FLOW_NO_INCOMING) is False
    assert is_flow_escalated("在庫過剰リスク品", QUADRANT_LOW_FLOW_NO_INCOMING) is True


def test_D024_responsible_departments_per_quadrant():
    assert responsible_departments(QUADRANT_LOW_FLOW_NO_INCOMING) == ("調達G", "営業G", "生産管理")
    assert responsible_departments(QUADRANT_DORMANT_STOCK) == ("調達G",)
    assert responsible_departments(QUADRANT_LOW_FLOW_NO_SHIPMENT) == ("営業G",)
    assert responsible_departments(QUADRANT_NORMAL_FLOW) == ("生産管理",)
    assert responsible_departments("unknown") == ()


@pytest.mark.parametrize("name", ["QUADRANT_SUPPLY_RISK", "QUADRANT_EXCESS_STOCK_RISK", "RESPONSIBLE_DEPARTMENTS"])
def test_D025_legacy_quadrant_constants_are_removed(name):
    assert not hasattr(module, name)


# --- 入荷実績なし（V-214）は判定期間に依存しない副次フラグ ---


def test_is_no_incoming_record_depends_only_on_last_incoming_date():
    assert is_no_incoming_record(None) is True
    assert is_no_incoming_record(date(2010, 1, 1)) is False


def test_no_incoming_record_can_coexist_with_dormant_stock():
    quadrant = _resolve(None, None, SELECTION_Y1)

    assert quadrant == QUADRANT_DORMANT_STOCK
    assert is_no_incoming_record(None) is True
