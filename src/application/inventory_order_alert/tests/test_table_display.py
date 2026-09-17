from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
    QUADRANT_LOW_FLOW_NO_INCOMING,
    responsible_departments,
)
from application.inventory_order_alert.domain.value_objects.table_display import (
    DEFAULT_DIRECTION,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SORT,
    SORTABLE_COLUMNS,
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

#: 緊急度ランクの逆順（通常流動品が先頭）。ソートで並べ替えられることを見るための入力順。
QUADRANTS_IN_REVERSE_RANK = (
    QUADRANT_NORMAL_FLOW,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_INCOMING,
)
QUADRANTS_IN_RANK_ORDER = (
    QUADRANT_LOW_FLOW_NO_INCOMING,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
)
#: 流動区分キー（ASCII）の辞書順。ランク順とは別物であることを D-106 で確かめる。
QUADRANTS_IN_KEY_ORDER = (
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
    QUADRANT_LOW_FLOW_NO_INCOMING,
)


def _row(**kwargs) -> dict[str, object]:
    base: dict[str, object] = {
        "flow_quadrant": QUADRANT_NORMAL_FLOW,
        "cust_code": "100",
        "cust_name": "A",
        "cust_chrg_psn_cd": "",
        "item_cd": "ITEM-001",
        "post_shipment_total_qty": 0,
        "stock_qty": "",
    }
    base.update(kwargs)
    return base


def _quadrant_row(quadrant: str, **kwargs) -> dict[str, object]:
    return _row(
        flow_quadrant=quadrant,
        responsible_department="・".join(responsible_departments(quadrant)),
        **kwargs,
    )


def _params(**kwargs) -> TableDisplayParams:
    defaults = {"sort_specs": (SortSpec(DEFAULT_SORT, "asc"),), "page": 1, "page_size": DEFAULT_PAGE_SIZE}
    defaults.update(kwargs)
    return TableDisplayParams(**defaults)


def test_sortable_columns_first_entry_is_flow_quadrant():
    assert SORTABLE_COLUMNS[0] == ("flow_quadrant", "流動区分")


def test_sortable_columns_label_slims_stock_quantity():
    assert ("stock_qty", "在庫数(SLIMS)") in SORTABLE_COLUMNS


def test_sortable_columns_include_mari_stock_after_slims_stock():
    columns = [column for column, _label in SORTABLE_COLUMNS]
    stock_index = columns.index("stock_qty")

    assert SORTABLE_COLUMNS[stock_index + 1] == ("mari_stock_qty", "在庫数(MARI)")


def test_sortable_columns_do_not_include_responsible_department():
    columns = [column for column, _label in SORTABLE_COLUMNS]

    # 責任部署は詳細ダイアログへ移した（design.md §6.1）
    assert "responsible_department" not in columns


def test_sort_rows_by_mari_stock_quantity_descending():
    rows = [
        _row(item_cd="A", mari_stock_qty=10),
        _row(item_cd="B", mari_stock_qty=30),
        _row(item_cd="C", mari_stock_qty=20),
    ]

    sorted_rows = sort_rows_legacy(rows, sort="mari_stock_qty", direction="desc")

    assert [row["item_cd"] for row in sorted_rows] == ["B", "C", "A"]


def test_sort_rows_treats_missing_mari_stock_as_smallest():
    rows = [
        _row(item_cd="A", mari_stock_qty=10),
        _row(item_cd="B", mari_stock_qty=""),
        _row(item_cd="C"),
    ]

    sorted_rows = sort_rows_legacy(rows, sort="mari_stock_qty", direction="asc")

    # 空（該当なし）と未取得はいずれも値ではないため先頭に来る
    assert sorted_rows[-1]["item_cd"] == "A"


def test_sort_rows_by_mari_stock_keeps_tiebreakers():
    rows = [
        _row(cust_code="200", item_cd="ITEM-B", mari_stock_qty=10),
        _row(cust_code="100", item_cd="ITEM-B", mari_stock_qty=10),
        _row(cust_code="100", item_cd="ITEM-A", mari_stock_qty=10),
    ]

    sorted_rows = sort_rows_legacy(rows, sort="mari_stock_qty", direction="asc")

    assert [row["item_cd"] for row in sorted_rows] == ["ITEM-A", "ITEM-B", "ITEM-B"]
    assert [row["cust_code"] for row in sorted_rows] == ["100", "100", "200"]


def test_sortable_columns_do_not_include_alert_level():
    columns = [column for column, _label in SORTABLE_COLUMNS]

    assert "alert_level" not in columns


def test_default_sort_is_flow_quadrant_ascending():
    assert DEFAULT_SORT == "flow_quadrant"
    assert DEFAULT_DIRECTION == "asc"


def test_sort_summary_rows_orders_flow_quadrant_by_urgency_rank_ascending():
    rows = [_quadrant_row(quadrant) for quadrant in QUADRANTS_IN_REVERSE_RANK]

    sorted_rows = sort_rows_legacy(rows, sort="flow_quadrant", direction="asc")

    assert [row["flow_quadrant"] for row in sorted_rows] == list(QUADRANTS_IN_RANK_ORDER)


def test_sort_summary_rows_orders_flow_quadrant_descending():
    rows = [_quadrant_row(quadrant) for quadrant in QUADRANTS_IN_REVERSE_RANK]

    sorted_rows = sort_rows_legacy(rows, sort="flow_quadrant", direction="desc")

    assert [row["flow_quadrant"] for row in sorted_rows] == list(reversed(QUADRANTS_IN_RANK_ORDER))


def test_sort_summary_rows_uses_rank_not_label_collation():
    rows = [_quadrant_row(quadrant) for quadrant in QUADRANTS_IN_REVERSE_RANK]

    sorted_rows = sort_rows_legacy(rows, sort="flow_quadrant", direction="asc")

    assert [row["flow_quadrant"] for row in sorted_rows] != list(QUADRANTS_IN_KEY_ORDER)
    assert sorted_rows[0]["flow_quadrant"] == QUADRANT_LOW_FLOW_NO_INCOMING


def test_sort_summary_rows_supports_flow_quadrant_in_five_key_multi_sort():
    rows = [
        _quadrant_row(QUADRANT_LOW_FLOW_NO_INCOMING, cust_code="100", item_cd="A", post_shipment_count=5, stock_qty="10"),
        _quadrant_row(QUADRANT_LOW_FLOW_NO_INCOMING, cust_code="100", item_cd="A", post_shipment_count=5, stock_qty="20"),
        _quadrant_row(QUADRANT_LOW_FLOW_NO_INCOMING, cust_code="100", item_cd="A", post_shipment_count=9, stock_qty="1"),
        _quadrant_row(QUADRANT_LOW_FLOW_NO_INCOMING, cust_code="100", item_cd="B", post_shipment_count=1, stock_qty="1"),
        _quadrant_row(QUADRANT_LOW_FLOW_NO_INCOMING, cust_code="200", item_cd="A", post_shipment_count=1, stock_qty="1"),
        _quadrant_row(QUADRANT_NORMAL_FLOW, cust_code="100", item_cd="A", post_shipment_count=1, stock_qty="1"),
    ]

    sorted_rows = sort_rows(
        rows,
        sort_specs=(
            SortSpec("flow_quadrant", "asc"),
            SortSpec("cust_code", "asc"),
            SortSpec("item_cd", "asc"),
            SortSpec("post_shipment_count", "desc"),
            SortSpec("stock_qty", "desc"),
        ),
    )

    assert [
        (row["flow_quadrant"], row["cust_code"], row["item_cd"], row["post_shipment_count"], row["stock_qty"])
        for row in sorted_rows
    ] == [
        (QUADRANT_LOW_FLOW_NO_INCOMING, "100", "A", 9, "1"),
        (QUADRANT_LOW_FLOW_NO_INCOMING, "100", "A", 5, "20"),
        (QUADRANT_LOW_FLOW_NO_INCOMING, "100", "A", 5, "10"),
        (QUADRANT_LOW_FLOW_NO_INCOMING, "100", "B", 1, "1"),
        (QUADRANT_LOW_FLOW_NO_INCOMING, "200", "A", 1, "1"),
        (QUADRANT_NORMAL_FLOW, "100", "A", 1, "1"),
    ]


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
        _quadrant_row(QUADRANT_NORMAL_FLOW, post_shipment_total_qty=1),
        _quadrant_row(QUADRANT_LOW_FLOW_NO_INCOMING, post_shipment_total_qty=99),
        _quadrant_row(QUADRANT_DORMANT_STOCK, post_shipment_total_qty=50),
    ]
    params = _params(sort_specs=(SortSpec("flow_quadrant", "asc"),), page=1, page_size=2)
    paginated = apply_table_display(rows, params)
    assert [row["flow_quadrant"] for row in paginated.rows] == [QUADRANT_LOW_FLOW_NO_INCOMING, QUADRANT_DORMANT_STOCK]
    assert paginated.total_pages == 2


def test_sort_rows_by_flow_quadrant_uses_cust_code_and_item_cd_as_tiebreakers():
    rows = [
        _quadrant_row(QUADRANT_LOW_FLOW_NO_INCOMING, cust_code="200", item_cd="ITEM-B"),
        _quadrant_row(QUADRANT_LOW_FLOW_NO_INCOMING, cust_code="100", item_cd="ITEM-B"),
        _quadrant_row(QUADRANT_LOW_FLOW_NO_INCOMING, cust_code="100", item_cd="ITEM-A"),
    ]
    sorted_rows = sort_rows_legacy(rows, sort="flow_quadrant", direction="asc")
    assert [row["item_cd"] for row in sorted_rows] == ["ITEM-A", "ITEM-B", "ITEM-B"]
    assert [row["cust_code"] for row in sorted_rows] == ["100", "100", "200"]


def test_toggle_sort_direction_flips_current_column():
    params = _params(sort_specs=(SortSpec("item_cd", "asc"),))
    assert toggle_sort_direction(params, "item_cd") == "desc"
    assert toggle_sort_direction(params, "cust_code") == "asc"


def test_sort_rows_by_confirmation_status_uses_logical_order():
    rows = [
        _row(confirmation_status="確認済み", item_cd="A"),
        _row(confirmation_status="未確認", item_cd="B"),
        _row(confirmation_status="確認中", item_cd="C"),
    ]
    sorted_rows = sort_rows_legacy(rows, sort="confirmation_status", direction="asc")
    assert [row["item_cd"] for row in sorted_rows] == ["B", "C", "A"]
    sorted_rows_desc = sort_rows_legacy(rows, sort="confirmation_status", direction="desc")
    assert [row["item_cd"] for row in sorted_rows_desc] == ["A", "C", "B"]


# --- 05_single-flow-view 第 2 段階: TC-SFV-D-059 在庫月数ソート（空は末尾） ---

from application.inventory_order_alert.domain.value_objects.table_display import (  # noqa: E402
    SORT_ONLY_COLUMNS,
    SORTABLE_KEYS,
    sort_rows,
    sort_spec_label,
)


def _months_row(months_of_stock: float | None, item_cd: str) -> dict[str, object]:
    return {"cust_code": "100", "item_cd": item_cd, "months_of_stock": months_of_stock}


def test_d059_months_of_stock_sort_asc_puts_none_last():
    rows = [_months_row(3.0, "A"), _months_row(None, "B"), _months_row(0.5, "C")]

    ordered = sort_rows(rows, sort_specs=(SortSpec("months_of_stock", "asc"),))

    assert [row["months_of_stock"] for row in ordered] == [0.5, 3.0, None]


def test_d059_months_of_stock_sort_desc_puts_none_last():
    rows = [_months_row(3.0, "A"), _months_row(None, "B"), _months_row(0.5, "C")]

    ordered = sort_rows(rows, sort_specs=(SortSpec("months_of_stock", "desc"),))

    assert [row["months_of_stock"] for row in ordered] == [3.0, 0.5, None]


def test_d059_months_of_stock_missing_key_is_treated_as_none():
    rows = [{"cust_code": "100", "item_cd": "A"}, _months_row(1.0, "B")]

    ordered = sort_rows(rows, sort_specs=(SortSpec("months_of_stock", "asc"),))

    assert [row["item_cd"] for row in ordered] == ["B", "A"]


def test_d059_months_of_stock_is_sortable_but_not_a_table_column():
    assert SORT_ONLY_COLUMNS == (("months_of_stock", "在庫月数"),)
    assert "months_of_stock" in SORTABLE_KEYS
    assert "months_of_stock" not in [column for column, _label in SORTABLE_COLUMNS]
    assert parse_sort_specs({"sort": "months_of_stock", "dir": "asc"}) == (SortSpec("months_of_stock", "asc"),)
    assert sort_spec_label(SortSpec("months_of_stock", "desc")) == "在庫月数（降順）"
