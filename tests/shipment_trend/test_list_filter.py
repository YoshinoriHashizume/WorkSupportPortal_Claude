from __future__ import annotations

from apps.shipment_trend.domain.list_filter import (
    FilterOption,
    ListFilterParams,
    apply_list_filters,
    build_filter_options,
    filter_item_cd_options,
    matches_item_cd_filter,
    parse_list_filter_params,
    visible_cust_options,
)


def test_list_filter_cust_and_chrg():
    rows = [
        {"cust_code": "101", "cust_name": "A", "cust_chrg_psn_cd": "S1", "item_cd": "ITEM-1"},
        {"cust_code": "102", "cust_name": "B", "cust_chrg_psn_cd": "S2", "item_cd": "ITEM-2"},
    ]
    options = build_filter_options(rows)
    params = parse_list_filter_params({"cust_code": "101", "cust_chrg_psn_cd": "S1"}, options)
    filtered = apply_list_filters(rows, params)
    assert len(filtered) == 1
    assert filtered[0]["cust_code"] == "101"


def test_list_filter_invalid_option_ignored():
    rows = [{"cust_code": "101", "cust_name": "A", "cust_chrg_psn_cd": "S1", "item_cd": "ITEM-1"}]
    options = build_filter_options(rows)
    params = parse_list_filter_params({"cust_code": "999"}, options)
    assert params == ListFilterParams()


def test_build_filter_options_collects_item_cd():
    rows = [
        {"cust_code": "101", "item_cd": "ITEM-2"},
        {"cust_code": "102", "item_cd": "ITEM-1"},
    ]
    options = build_filter_options(rows)
    assert options.item_cd_options == ("ITEM-1", "ITEM-2")


def test_build_filter_options_sorts_chrg_psn_numerically():
    rows = [
        {"cust_code": "101", "cust_name": "A", "cust_chrg_psn_cd": "100", "item_cd": "ITEM-1"},
        {"cust_code": "102", "cust_name": "B", "cust_chrg_psn_cd": "2", "item_cd": "ITEM-2"},
        {"cust_code": "103", "cust_name": "C", "cust_chrg_psn_cd": "A01", "item_cd": "ITEM-3"},
    ]
    options = build_filter_options(rows)
    assert [option.value for option in options.cust_chrg_psn_options] == ["2", "100", "A01"]


def test_matches_item_cd_filter_prefix_only():
    assert matches_item_cd_filter("ITEM-100", "ITEM-1")
    assert not matches_item_cd_filter("ITEM-100", "ITEM-2")
    assert matches_item_cd_filter("ITEM-100", "")
    assert not matches_item_cd_filter("ABC-101", "101")


def test_filter_item_cd_options_prefix():
    options = ("ITEM-1", "ITEM-10", "ITEM-2")
    assert filter_item_cd_options(options, "ITEM-1") == ("ITEM-1", "ITEM-10")
    assert filter_item_cd_options(options, "") == options


def test_filter_item_cd_options_excludes_middle_match():
    options = ("ABC-101", "101-XYZ")
    assert filter_item_cd_options(options, "101") == ("101-XYZ",)
    assert filter_item_cd_options(options, "ABC") == ("ABC-101",)


def test_apply_list_filters_item_cd_prefix():
    rows = [
        {"item_cd": "ITEM-100"},
        {"item_cd": "ITEM-200"},
    ]
    params = ListFilterParams(item_cd="ITEM-1")
    filtered = apply_list_filters(rows, params)
    assert len(filtered) == 1
    assert filtered[0]["item_cd"] == "ITEM-100"


def test_parse_list_filter_params_item_cd():
    rows = [{"cust_code": "101", "item_cd": "ITEM-1"}]
    options = build_filter_options(rows)
    params = parse_list_filter_params({"item_cd": " item-1 "}, options)
    assert params.item_cd == "item-1"


def test_parse_list_filter_params_cust_must_match_selected_chrg():
    rows = [
        {"cust_code": "101", "cust_name": "A", "cust_chrg_psn_cd": "S1", "item_cd": "ITEM-1"},
        {"cust_code": "102", "cust_name": "B", "cust_chrg_psn_cd": "S2", "item_cd": "ITEM-2"},
    ]
    options = build_filter_options(rows)
    params = parse_list_filter_params({"cust_code": "102", "cust_chrg_psn_cd": "S1"}, options)
    assert params.cust_chrg_psn_cd == "S1"
    assert params.cust_code == ""


def test_visible_cust_options_filters_by_chrg():
    rows = [
        {"cust_code": "101", "cust_name": "A", "cust_chrg_psn_cd": "S1", "item_cd": "ITEM-1"},
        {"cust_code": "102", "cust_name": "B", "cust_chrg_psn_cd": "S2", "item_cd": "ITEM-2"},
    ]
    options = build_filter_options(rows)
    assert visible_cust_options(options, "S1") == (FilterOption("101", "101 - A"),)
    assert visible_cust_options(options, "") == options.cust_options
