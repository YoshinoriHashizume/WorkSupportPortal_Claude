from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEPENDENT_CUST_JS = ROOT / "static" / "js" / "portal-list-dependent-cust-filter.js"


def test_portal_list_dependent_cust_filter_js_exports_helpers():
    source = DEPENDENT_CUST_JS.read_text(encoding="utf-8")
    assert "window.PortalListDependentCustFilter" in source
    assert "buildCustChrgCustIndex" in source
    assert "custOptionsForChrg" in source
    assert "renderCustCodeSelect" in source


def test_inventory_order_alert_list_client_uses_dependent_cust_filter():
    source = (ROOT / "static" / "js" / "inventory-order-alert-list-client.js").read_text(encoding="utf-8")
    assert "PortalListDependentCustFilter" in source
    assert "renderCustCodeSelect" in source
    assert "buildCustChrgCustIndex" in source


def test_shipment_trend_list_client_uses_dependent_cust_filter():
    source = (ROOT / "static" / "js" / "shipment-trend-list-client.js").read_text(encoding="utf-8")
    assert "PortalListDependentCustFilter" in source
    assert "renderCustCodeSelect" in source


def test_inventory_order_alert_template_loads_dependent_cust_script():
    template = (ROOT / "templates" / "inventory_order_alert" / "list.html").read_text(encoding="utf-8")
    assert "portal-list-dependent-cust-filter.js" in template
    assert "visible_cust_options" in template
    assert template.index("portal-list-dependent-cust-filter.js") < template.index(
        "inventory-order-alert-list-client.js"
    )


def test_shipment_trend_template_loads_dependent_cust_script():
    template = (ROOT / "templates" / "shipment_trend" / "list.html").read_text(encoding="utf-8")
    assert "portal-list-dependent-cust-filter.js" in template
    assert "visible_cust_options" in template
    assert template.index("portal-list-dependent-cust-filter.js") < template.index(
        "shipment-trend-list-client.js"
    )
