from __future__ import annotations

from pathlib import Path


JS_PATH = Path(__file__).resolve().parents[3] / "static" / "js" / "portal-customer-select.js"


def test_portal_customer_select_keeps_options_when_api_fails():
    source = JS_PATH.read_text(encoding="utf-8")
    assert "portal-customer-select:error" in source
    assert 'credentials: "same-origin"' in source
    load_block = source.split("async function loadSelect(select)", 1)[1].split("window.portalCustomerSelectLabel", 1)[0]
    assert "fillSelect(select, payload.customers" in load_block
    assert "return;" in load_block
