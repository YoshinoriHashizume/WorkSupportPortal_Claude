"""照合単位（T-208）のテスト（test-design.md TC-SFV-D-080〜087）。

得意先品番と (内作品番 × 仕入先) の組を節点とする二部グラフの連結成分。
"""

from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.reconciliation_unit import (
    ReconciliationUnit,
    ReconciliationUnits,
)

PAIR_P = ("96160-00500-9065", "9065")
PAIR_Q = ("94223-80600-9209", "9209")


def _row(item_cd: str, pair: tuple[str, str], *, cust_code: str = "100") -> dict[str, object]:
    level1_item_cd, level1_vend_cd = pair
    return {
        "cust_code": cust_code,
        "item_cd": item_cd,
        "level1_item_cd": level1_item_cd,
        "level1_vend_cd": level1_vend_cd,
    }


# --- TC-SFV-D-080: 1 得意先品番・1 組は単独の単位 ---


def test_d080_single_item_single_pair_is_one_unit():
    units = ReconciliationUnits.build([_row("X", PAIR_P)])

    assert len(units) == 1
    [unit] = list(units)
    assert isinstance(unit, ReconciliationUnit)
    assert unit.item_cds == frozenset({"X"})
    assert unit.level1_pairs == frozenset({PAIR_P})
    assert unit.row_keys == (("100", "X"),)
    assert unit.key == "X"


# --- TC-SFV-D-081: 組を共有する 2 得意先品番は 1 単位 ---


def test_d081_two_items_sharing_a_pair_form_one_unit():
    units = ReconciliationUnits.build([_row("96160-00500", PAIR_P), _row("10523-X0A02", PAIR_P, cust_code="137")])

    assert len(units) == 1
    unit = units.unit_of("96160-00500")
    assert unit is not None
    assert unit.item_cds == frozenset({"96160-00500", "10523-X0A02"})
    assert unit.level1_pairs == frozenset({PAIR_P})


# --- TC-SFV-D-082: 得意先品番が複数の組を持つと連結する ---


def test_d082_item_with_multiple_pairs_links_units():
    units = ReconciliationUnits.build([_row("X", PAIR_P), _row("X", PAIR_Q), _row("Z", PAIR_Q)])

    assert len(units) == 1
    unit = units.unit_of("Z")
    assert unit is not None
    assert unit.item_cds == frozenset({"X", "Z"})
    assert unit.level1_pairs == frozenset({PAIR_P, PAIR_Q})


# --- TC-SFV-D-083: 無関係な行は別単位 ---


def test_d083_unrelated_rows_are_separate_units():
    units = ReconciliationUnits.build([_row("X", PAIR_P), _row("Y", PAIR_Q)])

    assert len(units) == 2
    assert units.unit_of("X") is not units.unit_of("Y")


# --- TC-SFV-D-084: 同じ得意先品番の複数得意先は 1 単位に複数行 ---


def test_d084_same_item_across_customers_is_one_unit_with_two_rows():
    units = ReconciliationUnits.build([_row("X", PAIR_P, cust_code="100"), _row("X", PAIR_P, cust_code="137")])

    assert len(units) == 1
    unit = units.unit_of("X")
    assert unit is not None
    assert unit.row_keys == (("100", "X"), ("137", "X"))
    assert unit.item_cds == frozenset({"X"})


# --- TC-SFV-D-085: unit_of は代表キーが同じ単位を返す ---


def test_d085_unit_of_returns_same_unit_and_key_is_min_item_cd():
    units = ReconciliationUnits.build([_row("96160-00500", PAIR_P), _row("10523-X0A02", PAIR_P, cust_code="137")])

    assert units.unit_of("96160-00500") is units.unit_of("10523-X0A02")
    assert units.unit_of("96160-00500").key == "10523-X0A02"


def test_d085_row_keys_do_not_depend_on_input_order():
    rows_a = [_row("B", PAIR_P, cust_code="200"), _row("A", PAIR_P, cust_code="100")]
    rows_b = list(reversed(rows_a))

    assert ReconciliationUnits.build(rows_a).unit_of("A").row_keys == ReconciliationUnits.build(rows_b).unit_of("A").row_keys


# --- TC-SFV-D-086: 空の行リスト ---


def test_d086_empty_rows():
    units = ReconciliationUnits.build([])

    assert len(units) == 0
    assert units.unit_of("X") is None


# --- TC-SFV-D-087: level1 が空の行は自身だけの単位 ---


def test_d087_rows_with_empty_pair_are_not_linked_together():
    units = ReconciliationUnits.build([_row("X", ("", "")), _row("Y", ("", "")), _row("Z", PAIR_P)])

    assert len(units) == 3
    assert units.unit_of("X").item_cds == frozenset({"X"})
    assert units.unit_of("X").level1_pairs == frozenset()
    assert units.unit_of("Y").item_cds == frozenset({"Y"})


def test_d087_empty_pair_rows_of_the_same_item_still_share_a_unit():
    units = ReconciliationUnits.build([_row("X", ("", ""), cust_code="100"), _row("X", ("", ""), cust_code="137")])

    assert len(units) == 1
    assert units.unit_of("X").row_keys == (("100", "X"), ("137", "X"))


def test_rows_of_returns_the_rows_that_belong_to_the_unit():
    rows = [_row("96160-00500", PAIR_P), _row("10523-X0A02", PAIR_P, cust_code="137"), _row("Y", PAIR_Q)]
    units = ReconciliationUnits.build(rows)

    assert units.rows_of(units.unit_of("96160-00500"), rows) == rows[:2]
