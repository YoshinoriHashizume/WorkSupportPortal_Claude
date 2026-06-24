from __future__ import annotations

from apps.inventory_order_alert.domain.list_filter import (
    FilterOption,
    ListFilterOptions,
    apply_list_filters,
    build_display_query_string,
    build_filter_options,
    parse_list_filter_params,
)
from apps.inventory_order_alert.domain.table_display import SortSpec, TableDisplayParams


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
        _row(cust_code="201", cust_name="B社", cust_chrg_psn_cd="A01", item_cd="ITEM-3"),
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


def test_build_display_query_string_includes_active_filters():
    table_params = TableDisplayParams(sort_specs=(SortSpec("alert_level", "asc"),), page=2, page_size=50)
    query = build_display_query_string(
        table_params=table_params,
        filter_params=parse_list_filter_params(
            {"cust_code": "112", "cust_chrg_psn_cd": "A01"},
            ListFilterOptions(
                cust_options=(FilterOption("112", "112 - A"),),
                cust_chrg_psn_options=(FilterOption("A01", "A01"),),
            ),
        ),
    )
    assert "cust_code=112" in query
    assert "cust_chrg_psn_cd=A01" in query
    assert "page=2" in query
