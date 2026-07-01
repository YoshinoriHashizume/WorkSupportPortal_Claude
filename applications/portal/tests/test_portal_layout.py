from __future__ import annotations

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from applications.portal.models import PortalMenuGroupAccess


@pytest.fixture
def production_user(db):
    user = get_user_model().objects.create_user(username="portal-layout-user")
    group, _ = Group.objects.get_or_create(name="一般ユーザー")
    user.groups.add(group)
    PortalMenuGroupAccess.objects.create(user=user, group_key="production")
    return user


def test_portal_layout_css_defines_shared_viewport_and_typography():
    css = (Path(__file__).resolve().parents[3] / "static" / "css" / "app.css").read_text(encoding="utf-8")
    assert ":root {" in css
    assert "--portal-font-size-heading: 22px;" in css
    assert "--portal-font-size-body: 14px;" in css
    assert "--portal-control-height: 40px;" in css
    assert "body.portal-app-page { overflow: hidden; height: 100dvh; }" in css
    assert "body.portal-app-page .content > .portal-dashboard" in css
    assert "body.portal-app-page.portal-menu-page .content > .portal-dashboard" in css
    assert "overflow: visible" in css.split("body.portal-app-page.portal-menu-page .content > .portal-dashboard,")[1].split("}")[0]
    assert "body.portal-app-page .content > .db-viewer" in css
    assert "font-size: var(--portal-font-size-heading)" in css


@pytest.mark.django_db
def test_authenticated_pages_use_portal_app_page_body_class(client, production_user):
    client.force_login(production_user)
    pages = [
        "/app",
        "/app/production/receipt-comparison?type=finished-product",
        "/app/production/inventory-order-alert",
        "/app/production/five-year-nine",
    ]
    for path in pages:
        html = client.get(path).content.decode("utf-8")
        assert "portal-app-page" in html, path
    menu_html = client.get("/app").content.decode("utf-8")
    assert "portal-menu-page" in menu_html


@pytest.mark.django_db
def test_welcome_and_logout_live_in_fixed_sidebar_footer(client, production_user):
    client.force_login(production_user)
    html = client.get("/app").content.decode("utf-8")
    assert 'class="sidebar-foot"' in html
    assert 'class="sidebar-welcome"' in html
    assert 'class="sidebar-logout"' in html
    assert "ようこそ" in html
    assert 'href="/logout"' in html
    assert 'class="topbar"' not in html
    nav_end = html.index("</nav>")
    foot_start = html.index('class="sidebar-foot"')
    assert foot_start > nav_end


def test_portal_layout_css_uses_full_viewport_without_topbar():
    css = (Path(__file__).resolve().parents[3] / "static" / "css" / "app.css").read_text(encoding="utf-8")
    assert "--portal-topbar-height: 0px;" in css
    foot_rule = css.split(".sidebar-foot {")[1].split("}")[0]
    assert "flex-shrink: 0" in foot_rule
