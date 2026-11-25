"""照合単位行（T-213）の絞り込み・選択肢・並べ替え（spec/13 test-design TC-RUR-D-040〜045）。"""

from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.list_filter import build_filter_options
from application.inventory_order_alert.domain.value_objects.list_query import ListQuery
from application.inventory_order_alert.domain.value_objects.list_rows import filter_summary_rows
from application.inventory_order_alert.domain.value_objects.reconciliation_unit_row import build_reconciliation_unit_rows
from application.inventory_order_alert.domain.value_objects.table_display import SortSpec, sort_rows
from application.inventory_order_alert.tests.test_reconciliation_unit_row import _row, _unit_a_rows

AS_OF = date(2026, 11, 25)


def _units(rows):
    return build_reconciliation_unit_rows(rows)


def test_d040_non_representative_customer_matches():
    rows = _units(_unit_a_rows())

    assert len(filter_summary_rows(rows, ListQuery(as_of_date=AS_OF, cust_code="176"))) == 1


def test_d041_non_representative_vendor_matches():
    rows = _units(
        [
            _row("104", "X", level1_vend_cd="9028", unconfirmed_order_trend=[{"month": "2026-11", "qty": 10}]),
            _row("104", "X", level1_item_cd="X-9050", level1_vend_cd="9050"),
        ]
    )

    assert len(filter_summary_rows(rows, ListQuery(as_of_date=AS_OF, vend_code="9050"))) == 1


def test_d042_no_value_matches_means_hidden():
    rows = _units(_unit_a_rows())

    assert filter_summary_rows(rows, ListQuery(as_of_date=AS_OF, cust_code="999")) == []


def test_d043_customer_options_include_non_representatives():
    options = build_filter_options(_units(_unit_a_rows()))

    assert {option.value for option in options.cust_options} == {"104", "176"}


def test_d044_person_options_include_non_representatives():
    rows = _unit_a_rows()
    rows[1]["cust_chrg_psn_cd"] = "12"

    options = build_filter_options(_units(rows))

    assert {option.value for option in options.cust_chrg_psn_options} == {"22", "12"}


def test_d045_text_columns_sort_by_the_representative_value():
    first = _units(
        [
            _row("176", "A", unconfirmed_order_trend=[{"month": "2026-11", "qty": 9}]),
            _row("100", "A"),
        ]
    )
    second = _units([_row("150", "B")])

    ordered = sort_rows(first + second, sort_specs=(SortSpec(column="cust_code", direction="asc"),))

    assert [row["cust_code"] for row in ordered] == ["150", "176"]


def test_d040b_list_filters_match_any_member():
    """一覧画面の絞り込み（`apply_list_filters`）も照合単位行のどの値でも当たる（REQ-RUR-F-004）。"""
    from application.inventory_order_alert.domain.value_objects.list_filter import ListFilterParams, apply_list_filters

    rows = _unit_a_rows()
    rows[1]["cust_chrg_psn_cd"] = "12"
    units = _units(rows)

    assert len(apply_list_filters(units, ListFilterParams(cust_code="176"))) == 1
    assert len(apply_list_filters(units, ListFilterParams(cust_chrg_psn_cd="12"))) == 1
    assert apply_list_filters(units, ListFilterParams(cust_code="999")) == []
