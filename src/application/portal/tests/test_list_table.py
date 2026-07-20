from __future__ import annotations

import pytest

from application.portal.domain.value_objects.list_table import (
    DEFAULT_PAGE_SIZE,
    MAX_SORT_SPECS,
    PaginatedRows,
    SortSpec,
    build_table_query_string,
    paginate_rows,
    parse_sort_specs,
    sort_spec_label,
)


def test_paginate_rows_returns_empty_page():
    result = paginate_rows([], page=1, page_size=50)
    assert result.rows == []
    assert result.total_count == 0
    assert result.page == 1
    assert result.total_pages == 1
    assert result.start_index == 0
    assert result.end_index == 0
    assert not result.has_previous
    assert not result.has_next


def test_paginate_rows_clamps_page_and_slices():
    rows = list(range(1, 101))
    result = paginate_rows(rows, page=99, page_size=20)
    assert result.page == 5
    assert result.total_pages == 5
    assert result.rows == list(range(81, 101))
    assert result.start_index == 81
    assert result.end_index == 100
    assert result.has_previous
    assert not result.has_next


def test_parse_sort_specs_uses_defaults_when_sort_missing():
    defaults = (SortSpec("status_label", "asc"),)
    specs = parse_sort_specs(
        {},
        sortable_keys={"status_label", "asset_number"},
        default_specs=defaults,
        default_direction_for_column=lambda _column: "asc",
    )
    assert specs == defaults


def test_parse_sort_specs_parses_multiple_columns():
    specs = parse_sort_specs(
        {"sort": "asset_number,status_label", "dir": "desc,asc"},
        sortable_keys={"status_label", "asset_number"},
        default_specs=(SortSpec("status_label", "asc"),),
        default_direction_for_column=lambda column: "desc" if column == "inventory_datetime" else "asc",
    )
    assert specs == (
        SortSpec("asset_number", "desc"),
        SortSpec("status_label", "asc"),
    )


def test_parse_sort_specs_skips_unknown_and_duplicate_columns():
    specs = parse_sort_specs(
        {"sort": "unknown,asset_number,asset_number", "dir": "asc"},
        sortable_keys={"asset_number"},
        default_specs=(SortSpec("asset_number", "asc"),),
        default_direction_for_column=lambda _column: "asc",
    )
    assert specs == (SortSpec("asset_number", "asc"),)


def test_parse_sort_specs_limits_to_max_sort_specs():
    sortable = {f"col{i}" for i in range(MAX_SORT_SPECS + 2)}
    specs = parse_sort_specs(
        {"sort": ",".join(sorted(sortable)), "dir": "asc"},
        sortable_keys=sortable,
        default_specs=(SortSpec("col0", "asc"),),
        default_direction_for_column=lambda _column: "asc",
    )
    assert len(specs) == MAX_SORT_SPECS


def test_build_table_query_string_includes_sort_and_page():
    query = build_table_query_string(
        sort_specs=(SortSpec("asset_number", "desc"), SortSpec("status_label", "asc")),
        page=2,
        page_size=DEFAULT_PAGE_SIZE,
        extra={"status": "matched"},
    )
    assert "sort=asset_number%2Cstatus_label" in query
    assert "dir=desc%2Casc" in query
    assert "page=2" in query
    assert f"page_size={DEFAULT_PAGE_SIZE}" in query
    assert "status=matched" in query


def test_sort_spec_label_formats_direction():
    label = sort_spec_label(
        SortSpec("asset_number", "desc"),
        column_labels={"asset_number": "資産番号"},
    )
    assert label == "資産番号（降順）"
