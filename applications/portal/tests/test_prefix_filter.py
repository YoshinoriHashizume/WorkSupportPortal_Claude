from __future__ import annotations

from applications.portal.domain.prefix_filter import (
    extract_distinct_values,
    extract_distinct_values_from_rows,
    filter_prefix_options,
    matches_prefix_filter,
)


def _normalize_asset_number(value: str) -> str:
    text = value.strip()
    if text and text[0] in {"L", "l"}:
        text = text[1:].strip()
    return text


def test_filter_prefix_options_empty_query_returns_all():
    options = ("ITEM-1", "ITEM-2")
    assert filter_prefix_options(options, "") == options


def test_filter_prefix_options_prefix_match():
    options = ("ITEM-1", "ITEM-10", "ITEM-2")
    assert filter_prefix_options(options, "ITEM-1") == ("ITEM-1", "ITEM-10")


def test_filter_prefix_options_excludes_middle_match():
    options = ("ABC-101", "101-XYZ")
    assert filter_prefix_options(options, "101") == ("101-XYZ",)


def test_matches_prefix_filter_empty_query():
    assert matches_prefix_filter("ITEM-1", "") is True


def test_matches_prefix_filter_prefix_only():
    assert matches_prefix_filter("ITEM-100", "ITEM-1") is True
    assert matches_prefix_filter("ABC-101", "101") is False


def test_matches_prefix_filter_with_custom_normalize():
    assert matches_prefix_filter("L5262", "52", normalize=_normalize_asset_number) is True
    assert matches_prefix_filter("L5262", "5262", normalize=_normalize_asset_number) is True


def test_extract_distinct_values_sorted_unique():
    assert extract_distinct_values(["B", "A", "A", ""]) == ("A", "B")


def test_extract_distinct_values_from_rows_by_column():
    rows = [
        {"item_cd": "ITEM-2"},
        {"item_cd": "ITEM-1"},
        {"item_cd": "ITEM-1"},
    ]
    assert extract_distinct_values_from_rows(rows, "item_cd") == ("ITEM-1", "ITEM-2")
