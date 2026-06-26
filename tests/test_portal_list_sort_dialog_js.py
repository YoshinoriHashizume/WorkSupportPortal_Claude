from __future__ import annotations

from pathlib import Path


SORT_DIALOG_JS_PATH = Path(__file__).resolve().parents[1] / "static" / "js" / "portal-list-sort-dialog.js"


def test_portal_list_sort_dialog_js_exports_init():
    source = SORT_DIALOG_JS_PATH.read_text(encoding="utf-8")
    assert "window.PortalListSortDialog" in source
    assert "init: initSortDialog" in source
    assert "applySortSpecs" in source
    assert "showModal" in source


def test_portal_list_sort_dialog_js_supports_drag_and_drop():
    source = SORT_DIALOG_JS_PATH.read_text(encoding="utf-8")
    assert "draggable" in source
    assert "insertBefore" in source
    assert "dragstart" in source
    assert "refreshSortRowOrders" in source
