from __future__ import annotations

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.portal.models import PortalMenuGroupAccess


@pytest.fixture
def production_user(db):
    user = get_user_model().objects.create_user(username="portal-layout-user")
    group, _ = Group.objects.get_or_create(name="一般ユーザー")
    user.groups.add(group)
    PortalMenuGroupAccess.objects.create(user=user, group_key="production")
    return user


def test_portal_layout_css_defines_shared_viewport_and_typography():
    css = (Path(__file__).resolve().parents[1] / "static" / "css" / "app.css").read_text(encoding="utf-8")
    assert ":root {" in css
    assert "--portal-font-size-heading: 22px;" in css
    assert "--portal-font-size-body: 14px;" in css
    assert "--portal-control-height: 40px;" in css
    assert "body.portal-app-page { overflow: hidden; height: 100dvh; }" in css
    assert "body.portal-app-page .content > .portal-dashboard" in css
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
