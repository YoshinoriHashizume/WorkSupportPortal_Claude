from __future__ import annotations

from pathlib import Path


CORE_JS_PATH = Path(__file__).resolve().parents[1] / "static" / "js" / "portal-list-core.js"


def test_portal_list_core_js_exports_helpers():
    source = CORE_JS_PATH.read_text(encoding="utf-8")
    assert "window.PortalListCore" in source
    assert "parseSortSpecs" in source
    assert "readBaseStateFromUrl" in source
    assert "paginateRows" in source
    assert "sortRows" in source
    assert "renderTableHeaders" in source
    assert "renderPagination" in source
    assert "bindPaginationControls" in source
    assert "bindPrefixFilterInput" in source
    assert "updatePrefixDatalist" in source
    assert "matchesPrefixFilter" in source
    assert "replaceUrl" in source
    assert "history.replaceState" in source


def test_portal_list_core_js_supports_link_and_button_header_modes():
    source = CORE_JS_PATH.read_text(encoding="utf-8")
    header_block = source.split("function renderTableHeaders", 1)[1].split("function renderPagination", 1)[0]
    assert 'headerMode === "button"' in header_block
    assert '<a href="#" ' in header_block
    assert "headerButtonClass" in header_block


def test_portal_list_core_js_prefix_filter_sync_updates_input_value():
    source = CORE_JS_PATH.read_text(encoding="utf-8")
    sync_block = source.split("sync(value) {", 1)[1].split("updatePrefixDatalist", 1)[0]
    assert "debounceTimer" in sync_block
    assert "input.value = normalized" in sync_block


def test_portal_list_core_js_sort_rows_supports_tiebreakers():
    source = CORE_JS_PATH.read_text(encoding="utf-8")
    sort_block = source.split("function sortRows", 1)[1].split("function appendSortQueryParams", 1)[0]
    assert "tiebreakers" in sort_block
    assert "activeColumns" in sort_block
