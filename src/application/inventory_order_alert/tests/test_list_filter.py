from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.list_filter import (
    FilterOption,
    ListFilterOptions,
    ListFilterParams,
    apply_list_filters,
    build_display_query_string,
    build_filter_options,
    list_filter_params_from_client_payload,
    matches_item_cd_filter,
    matches_level1_item_cd_filter,
    parse_list_filter_params,
)
from application.inventory_order_alert.domain.value_objects.table_display import SortSpec, TableDisplayParams


def _row(**kwargs) -> dict[str, object]:
    base = {
        "cust_code": "112",
        "cust_name": "テスト得意先",
        "cust_chrg_psn_cd": "A01",
        "item_cd": "ITEM-1",
    }
    base.update(kwargs)
    return base


def test_build_filter_options_from_rows():
    rows = [
        _row(cust_code="112", cust_name="A社", cust_chrg_psn_cd="100"),
        _row(cust_code="112", cust_name="A社", cust_chrg_psn_cd="100", item_cd="ITEM-2"),
        _row(cust_code="201", cust_name="B社", cust_chrg_psn_cd="2"),
        _row(
            cust_code="201",
            cust_name="B社",
            cust_chrg_psn_cd="A01",
            item_cd="ITEM-3",
            level1_item_cd="L1-3",
        ),
    ]
    options = build_filter_options(rows)

    assert options.cust_options == (
        FilterOption(value="112", label="112 - A社"),
        FilterOption(value="201", label="201 - B社"),
    )
    assert options.cust_chrg_psn_options == (
        FilterOption(value="2", label="2"),
        FilterOption(value="100", label="100"),
        FilterOption(value="A01", label="A01"),
    )
    assert options.item_cd_options == ("ITEM-1", "ITEM-2", "ITEM-3")
    assert options.level1_item_cd_options == ("L1-3",)


def test_apply_list_filters_by_cust_code_and_chrg_psn():
    rows = [
        _row(cust_code="112", cust_chrg_psn_cd="A01"),
        _row(cust_code="201", cust_chrg_psn_cd="B02", item_cd="ITEM-2"),
    ]
    options = build_filter_options(rows)

    filtered = apply_list_filters(
        rows,
        parse_list_filter_params({"cust_code": "112", "cust_chrg_psn_cd": "A01"}, options),
    )
    assert len(filtered) == 1
    assert filtered[0]["cust_code"] == "112"


def test_parse_list_filter_params_ignores_unknown_values():
    rows = [_row()]
    options = build_filter_options(rows)
    params = parse_list_filter_params({"cust_code": "999", "cust_chrg_psn_cd": "Z99"}, options)
    assert params.cust_code == ""
    assert params.cust_chrg_psn_cd == ""


def test_parse_list_filter_params_cust_must_match_selected_chrg():
    rows = [
        _row(cust_code="112", cust_chrg_psn_cd="A01"),
        _row(cust_code="201", cust_chrg_psn_cd="B02", item_cd="ITEM-2"),
    ]
    options = build_filter_options(rows)
    params = parse_list_filter_params({"cust_code": "201", "cust_chrg_psn_cd": "A01"}, options)
    assert params.cust_chrg_psn_cd == "A01"
    assert params.cust_code == ""


def test_visible_cust_options_filters_by_chrg():
    rows = [
        _row(cust_code="112", cust_name="A社", cust_chrg_psn_cd="A01"),
        _row(cust_code="201", cust_name="B社", cust_chrg_psn_cd="B02"),
    ]
    from application.inventory_order_alert.domain.value_objects.list_filter import visible_cust_options

    options = build_filter_options(rows)
    assert visible_cust_options(options, "A01") == (FilterOption("112", "112 - A社"),)
    assert visible_cust_options(options, "") == options.cust_options


def test_build_display_query_string_includes_active_filters():
    table_params = TableDisplayParams(sort_specs=(SortSpec("alert_level", "asc"),), page=2, page_size=50)
    query = build_display_query_string(
        table_params=table_params,
        filter_params=parse_list_filter_params(
            {"cust_code": "112", "cust_chrg_psn_cd": "A01"},
            ListFilterOptions(
                cust_options=(FilterOption("112", "112 - A"),),
                cust_chrg_psn_options=(FilterOption("A01", "A01"),),
                item_cd_options=(),
                level1_item_cd_options=(),
                cust_chrg_cust_index={"A01": {"112": "A"}},
            ),
        ),
    )
    assert "cust_code=112" in query
    assert "cust_chrg_psn_cd=A01" in query
    assert "page=2" in query


def test_apply_list_filters_item_cd_prefix():
    rows = [
        _row(item_cd="ITEM-100"),
        _row(item_cd="ITEM-200"),
    ]
    filtered = apply_list_filters(rows, ListFilterParams(item_cd="ITEM-1"))
    assert len(filtered) == 1
    assert filtered[0]["item_cd"] == "ITEM-100"


def test_apply_list_filters_level1_item_cd_prefix():
    rows = [
        _row(level1_item_cd="90249-10112-9209"),
        _row(level1_item_cd="90249-10112-9999"),
    ]
    filtered = apply_list_filters(rows, ListFilterParams(level1_item_cd="90249-10112"))
    assert len(filtered) == 1
    assert filtered[0]["level1_item_cd"] == "90249-10112-9209"


def test_matches_item_cd_filter_prefix_only():
    assert matches_item_cd_filter("ITEM-100", "ITEM-1")
    assert not matches_item_cd_filter("ITEM-100", "ITEM-2")


def test_matches_level1_item_cd_filter_prefix_only():
    assert matches_level1_item_cd_filter("90249-10112-9209", "90249")
    assert matches_level1_item_cd_filter("90249-10112-9209", "90249-10112")
    assert not matches_level1_item_cd_filter("90249-10112-9209", "9209")
    assert not matches_level1_item_cd_filter("90249-10112-9209", "9999")


def test_parse_list_filter_params_item_cd_and_level1():
    rows = [_row(item_cd="ITEM-1", level1_item_cd="L1-1")]
    options = build_filter_options(rows)
    params = parse_list_filter_params({"item_cd": " item-1 ", "level1_item_cd": "L1"}, options)
    assert params.item_cd == "item-1"
    assert params.level1_item_cd == "L1"


def test_build_display_query_string_includes_prefix_filters():
    table_params = TableDisplayParams(sort_specs=(SortSpec("alert_level", "asc"),), page=1, page_size=50)
    query = build_display_query_string(
        table_params=table_params,
        filter_params=ListFilterParams(item_cd="ITEM-1", level1_item_cd="L1"),
    )
    assert "item_cd=ITEM-1" in query
    assert "level1_item_cd=L1" in query


def test_list_filter_params_from_client_payload():
    params = list_filter_params_from_client_payload(
        {
            "custCodeFilter": "112",
            "custChrgPsnCdFilter": "A01",
            "itemCdFilter": "ITEM-1",
            "level1ItemCdFilter": "L1",
        }
    )
    assert params == ListFilterParams(
        cust_code="112",
        cust_chrg_psn_cd="A01",
        item_cd="ITEM-1",
        level1_item_cd="L1",
    )
