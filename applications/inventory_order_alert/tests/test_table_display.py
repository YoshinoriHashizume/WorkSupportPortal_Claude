from __future__ import annotations

from applications.inventory_order_alert.domain.table_display import (
    DEFAULT_PAGE_SIZE,
    DEFAULT_SORT,
    SortSpec,
    TableDisplayParams,
    apply_table_display,
    paginate_rows,
    parse_sort_specs,
    parse_table_display_params,
    sort_rows,
    sort_rows_legacy,
    toggle_sort_direction,
)


def _row(**kwargs) -> dict[str, object]:
    base = {
        "alert_level": "アラート無し",
        "cust_code": "100",
        "cust_name": "A",
        "cust_chrg_psn_cd": "",
        "item_cd": "ITEM-001",
        "post_shipment_total_qty": 0,
        "stock_qty": "",
    }
    base.update(kwargs)
    return base


def _params(**kwargs) -> TableDisplayParams:
    defaults = {"sort_specs": (SortSpec(DEFAULT_SORT, "asc"),), "page": 1, "page_size": DEFAULT_PAGE_SIZE}
    defaults.update(kwargs)
    return TableDisplayParams(**defaults)


def test_parse_table_display_params_defaults():
    params = parse_table_display_params({})
    assert params.sort == DEFAULT_SORT
    assert params.direction == "asc"
    assert params.page == 1
    assert params.page_size == DEFAULT_PAGE_SIZE


def test_parse_table_display_params_custom_values():
    params = parse_table_display_params({"sort": "item_cd", "dir": "desc", "page": "3", "page_size": "100"})
    assert params.sort == "item_cd"
    assert params.direction == "desc"
    assert params.page == 3
    assert params.page_size == 100


def test_parse_sort_specs_supports_multiple_columns():
    specs = parse_sort_specs({"sort": "last_incoming_date,last_ship_date", "dir": "asc,desc"})
    assert len(specs) == 2
    assert specs[0].column == "last_incoming_date"
    assert specs[0].direction == "asc"
    assert specs[1].column == "last_ship_date"
    assert specs[1].direction == "desc"


def test_sort_rows_by_item_cd_desc():
    rows = [_row(item_cd="B"), _row(item_cd="A")]
    sorted_rows = sort_rows_legacy(rows, sort="item_cd", direction="desc")
    assert [row["item_cd"] for row in sorted_rows] == ["B", "A"]


def test_sort_rows_with_multiple_specs():
    rows = [
        _row(item_cd="A", last_incoming_date="2026/06/01"),
        _row(item_cd="B", last_incoming_date="2026/06/01"),
        _row(item_cd="C", last_incoming_date="2026/01/01"),
    ]
    sorted_rows = sort_rows(
        rows,
        sort_specs=(
            SortSpec("last_incoming_date", "asc"),
            SortSpec("item_cd", "asc"),
        ),
    )
    assert [row["item_cd"] for row in sorted_rows] == ["C", "A", "B"]


def test_paginate_rows_returns_page_slice():
    rows = [_row(item_cd=f"ITEM-{index}") for index in range(25)]
    paginated = paginate_rows(rows, page=2, page_size=20)
    assert paginated.total_count == 25
    assert paginated.total_pages == 2
    assert paginated.page == 2
    assert len(paginated.rows) == 5
    assert paginated.start_index == 21
    assert paginated.end_index == 25
    assert paginated.has_previous is True
    assert paginated.has_next is False


def test_sort_rows_by_cust_chrg_psn_cd_numerically():
    rows = [
        _row(cust_chrg_psn_cd="100"),
        _row(cust_chrg_psn_cd="2", item_cd="ITEM-2"),
        _row(cust_chrg_psn_cd="10", item_cd="ITEM-3"),
    ]
    sorted_rows = sort_rows_legacy(rows, sort="cust_chrg_psn_cd", direction="asc")
    assert [row["cust_chrg_psn_cd"] for row in sorted_rows] == ["2", "10", "100"]


def test_sort_rows_by_last_incoming_date_puts_empty_first_in_asc():
    rows = [
        _row(last_incoming_date="2026/06/01", item_cd="B"),
        _row(last_incoming_date="", item_cd="A"),
        _row(last_incoming_date="2026/01/01", item_cd="C"),
    ]
    sorted_rows = sort_rows_legacy(rows, sort="last_incoming_date", direction="asc")
    assert [row["item_cd"] for row in sorted_rows] == ["A", "C", "B"]


def test_sort_rows_by_last_incoming_date_puts_empty_last_in_desc():
    rows = [
        _row(last_incoming_date="2026/06/01", item_cd="B"),
        _row(last_incoming_date="", item_cd="A"),
        _row(last_incoming_date="2026/01/01", item_cd="C"),
    ]
    sorted_rows = sort_rows_legacy(rows, sort="last_incoming_date", direction="desc")
    assert [row["item_cd"] for row in sorted_rows] == ["B", "C", "A"]


def test_apply_table_display_sorts_then_paginates():
    rows = [
        _row(alert_level="アラート無し", post_shipment_total_qty=1),
        _row(alert_level="重点", post_shipment_total_qty=99),
        _row(alert_level="警告（出荷あり）", post_shipment_total_qty=50),
    ]
    params = _params(sort_specs=(SortSpec("alert_level", "asc"),), page=1, page_size=2)
    paginated = apply_table_display(rows, params)
    assert [row["alert_level"] for row in paginated.rows] == ["重点", "警告（出荷あり）"]
    assert paginated.total_pages == 2


def test_sort_rows_by_alert_level_uses_cust_code_and_item_cd_as_tiebreakers():
    rows = [
        _row(alert_level="重点", cust_code="200", item_cd="ITEM-B"),
        _row(alert_level="重点", cust_code="100", item_cd="ITEM-B"),
        _row(alert_level="重点", cust_code="100", item_cd="ITEM-A"),
    ]
    sorted_rows = sort_rows_legacy(rows, sort="alert_level", direction="asc")
    assert [row["item_cd"] for row in sorted_rows] == ["ITEM-A", "ITEM-B", "ITEM-B"]
    assert [row["cust_code"] for row in sorted_rows] == ["100", "100", "200"]


def test_toggle_sort_direction_flips_current_column():
    params = _params(sort_specs=(SortSpec("item_cd", "asc"),))
    assert toggle_sort_direction(params, "item_cd") == "desc"
    assert toggle_sort_direction(params, "cust_code") == "asc"
