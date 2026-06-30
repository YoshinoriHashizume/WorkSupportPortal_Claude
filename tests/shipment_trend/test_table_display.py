from __future__ import annotations

from apps.shipment_trend.domain.table_display import (
    DEFAULT_SORT,
    DEFAULT_SORT_SPECS,
    SortSpec,
    apply_table_display,
    format_fiscal_year,
    parse_table_display_params,
    sort_rows,
)


def test_format_fiscal_year():
    assert format_fiscal_year(2023) == "2023"
    assert format_fiscal_year(None) == "—"


def test_sort_rows_first_fiscal_year_asc():
    rows = [
        {"first_fiscal_year": 2025, "item_cd": "A"},
        {"first_fiscal_year": 2023, "item_cd": "B"},
        {"first_fiscal_year": None, "item_cd": "C"},
    ]
    sorted_rows = sort_rows(rows, (SortSpec("first_fiscal_year", "asc"),))
    assert [row["item_cd"] for row in sorted_rows] == ["B", "A", "C"]


def test_default_sort_specs_change_rate_asc():
    assert DEFAULT_SORT == "change_rate_pct"
    assert DEFAULT_SORT_SPECS[0].column == "change_rate_pct"
    assert DEFAULT_SORT_SPECS[0].direction == "asc"


def test_parse_table_display_params_uses_default_when_sort_missing():
    specs = parse_table_display_params({})
    assert specs[0].column == "change_rate_pct"
    assert specs[0].direction == "asc"


def test_sort_rows_change_rate_asc_puts_largest_negative_first():
    rows = [
        {"change_rate_pct": 10.0, "change_qty": 10, "item_cd": "A"},
        {"change_rate_pct": -10.0, "change_qty": -10, "item_cd": "B"},
        {"change_rate_pct": -50.0, "change_qty": -50, "item_cd": "C"},
        {"change_rate_pct": None, "change_qty": 0, "item_cd": "D"},
        {"change_rate_pct": 0.0, "change_qty": 0, "item_cd": "E"},
    ]
    sorted_rows = sort_rows(rows, DEFAULT_SORT_SPECS)
    assert [row["item_cd"] for row in sorted_rows] == ["C", "B", "E", "A", "D"]


def test_apply_table_display_default_sort():
    rows = [
        {"change_rate_pct": 5.0, "change_qty": 5, "item_cd": "A"},
        {"change_rate_pct": -30.0, "change_qty": -30, "item_cd": "B"},
    ]
    paginated = apply_table_display(rows, sort_specs=DEFAULT_SORT_SPECS, page=1, page_size=50)
    assert paginated.rows[0]["item_cd"] == "B"
