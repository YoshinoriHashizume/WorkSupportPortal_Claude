from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PREFIX_FILTER_JS = ROOT / "static" / "js" / "portal-list-prefix-filter.js"


def test_portal_list_prefix_filter_js_exports_factory():
    source = PREFIX_FILTER_JS.read_text(encoding="utf-8")
    assert "window.PortalListPrefixFilter" in source
    assert "createPrefixColumnFilter" in source
    assert "matchesRow" in source
    assert "bind" in source
    assert "filterRows" in source
    assert "PortalListCore" in source
