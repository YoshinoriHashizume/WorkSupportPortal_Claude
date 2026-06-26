from __future__ import annotations

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.asset_inventory.domain.ports import ManagementRow
from apps.portal.models import PortalMenuGroupAccess


@pytest.fixture
def production_user(db):
    user = get_user_model().objects.create_user(username="portal-search-disclosure-user")
    group, _ = Group.objects.get_or_create(name="一般ユーザー")
    user.groups.add(group)
    PortalMenuGroupAccess.objects.create(user=user, group_key="production")
    return user


@pytest.fixture
def general_affairs_user(db):
    user = get_user_model().objects.create_user(username="portal-search-disclosure-ga-user")
    group, _ = Group.objects.get_or_create(name="一般ユーザー")
    user.groups.add(group)
    PortalMenuGroupAccess.objects.create(user=user, group_key="general-affairs")
    return user


def test_portal_search_disclosure_shared_assets_exist():
    root = Path(__file__).resolve().parents[1]
    css = (root / "static" / "css" / "app.css").read_text(encoding="utf-8")
    js = (root / "static" / "js" / "portal-search-disclosure.js").read_text(encoding="utf-8")
    base = (root / "templates" / "base.html").read_text(encoding="utf-8")
    open_partial = (root / "templates" / "includes" / "portal_search_disclosure_open.html").read_text(encoding="utf-8")
    close_partial = (root / "templates" / "includes" / "portal_search_disclosure_close.html").read_text(encoding="utf-8")

    assert ".portal-search-disclosure {" in css
    assert "width: 100%" in css.split(".portal-search-disclosure-toggle {")[1].split("}")[0]
    toggle_rule = css.split(".portal-search-disclosure-toggle {")[1].split("}")[0]
    assert "font-size: var(--portal-font-size-caption)" in toggle_rule
    assert "padding: 6px 14px" in toggle_rule
    panel_rule = css.split(".portal-search-disclosure-panel {")[1].split("}")[0]
    assert "padding: 16px 18px 12px" in panel_rule
    assert 'STORAGE_PREFIX = "portal-search-disclosure:"' not in js
    assert "section.open = true" in js
    assert "localStorage" not in js
    disclosure_rule = css.split(".portal-search-disclosure {")[1].split("}")[0]
    assert "display: flex" in disclosure_rule
    assert "flex-direction: column" in disclosure_rule
    panel_rule = css.split(".portal-search-disclosure-panel {")[1].split("}")[0]
    assert "order: 1" in panel_rule
    toggle_rule = css.split(".portal-search-disclosure-toggle {")[1].split("}")[0]
    assert "order: 2" in toggle_rule
    assert open_partial.index("<summary") < open_partial.index('class="portal-search-disclosure-panel"')
    assert "portal-search-disclosure.js" in base
    assert 'class="portal-search-disclosure card"' in open_partial
    assert "折りたたむ" in open_partial
    assert "展開" in open_partial


@pytest.mark.django_db
def test_asset_inventory_renders_search_disclosure(client, general_affairs_user, monkeypatch):
    result = type(
        "R",
        (),
        {
            "management_rows": (ManagementRow("1", "2025棚卸", "2025", "", "", "415", "408"),),
            "selected_management_id": "1",
            "rows": (),
            "filtered_rows": (),
            "counts": type("C", (), {"matched": 0, "asset_only": 0, "inventory_only": 0})(),
            "filtered_counts": type("C", (), {"matched": 0, "asset_only": 0, "inventory_only": 0})(),
            "site_options": (),
            "site_filter": "all",
            "status_filter": "all",
            "plate_filter": "all",
            "page": 1,
            "page_size": 50,
            "total_pages": 1,
            "sort_specs": (),
            "start_index": 0,
            "end_index": 0,
            "has_previous": False,
            "has_next": False,
            "error_message": None,
        },
    )()

    monkeypatch.setattr(
        "apps.asset_inventory.views.list_page_usecase",
        lambda: type("U", (), {"execute": lambda *args, **kwargs: result})(),
    )
    monkeypatch.setattr("apps.asset_inventory.views.build_table_headers", lambda **kwargs: [])
    monkeypatch.setattr("apps.asset_inventory.views.build_row_color_rule_rows", lambda: [])

    client.force_login(general_affairs_user)
    session = client.session
    session["desknet_access_key"] = "test-key"
    session.save()

    html = client.get("/app/general-affairs/asset-inventory").content.decode("utf-8")
    assert 'id="aiv-search-disclosure"' in html
    assert 'data-storage-key="aiv-search-v2"' in html
    assert " open" in html.split('id="aiv-search-disclosure"')[1].split(">")[0]
    assert 'class="portal-search-disclosure card"' in html
    assert "折りたたむ" in html and "展開" in html
    assert "aiv-filter-panel-title" not in html


def test_asset_inventory_management_filter_label_is_left_of_select():
    css = (Path(__file__).resolve().parents[1] / "static" / "css" / "app.css").read_text(encoding="utf-8")
    label_rule = css.split(".asset-inventory-page .aiv-management-filter label {")[1].split("}")[0]
    assert "display: inline-flex" in label_rule
    assert "align-items: center" in label_rule


def test_receipt_comparison_search_filter_labels_are_left_of_inputs():
    css = (Path(__file__).resolve().parents[1] / "static" / "css" / "app.css").read_text(encoding="utf-8")
    label_rule = css.split(
        ".receipt-comparison-page .portal-search-disclosure-panel > .receipt-filter label {"
    )[1].split("}")[0]
    assert "display: inline-flex" in label_rule
    assert "align-items: center" in label_rule
    field_rule = css.split(
        ".receipt-comparison-page .portal-search-disclosure-panel > .receipt-filter select,"
    )[1].split("}")[0]
    assert "width: auto" in field_rule


@pytest.mark.django_db
def test_receipt_comparison_finished_product_renders_search_disclosure(client, production_user):
    client.force_login(production_user)
    html = client.get("/app/production/receipt-comparison?type=finished-product").content.decode("utf-8")
    head_index = html.index('class="portal-section-head receipt-head"')
    disclosure_index = html.index('id="receipt-comparison-search-disclosure"')
    results_index = html.index('class="receipt-results-card card receipt-results-main-form"')
    assert head_index < disclosure_index < results_index
    assert 'data-storage-key="receipt-comparison-search-finished-product-v2"' in html
    assert 'class="receipt-filter"' in html
    assert 'class="receipt-filter card"' not in html
    assert "折りたたむ" in html and "展開" in html


@pytest.mark.django_db
def test_receipt_comparison_supplied_parts_renders_search_disclosure(client, production_user):
    client.force_login(production_user)
    html = client.get("/app/production/receipt-comparison?type=supplied-parts").content.decode("utf-8")
    assert 'data-storage-key="receipt-comparison-search-supplied-parts-v2"' in html
    assert 'id="receipt-comparison-search-disclosure"' in html
