from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from application.portal.domain.value_objects.menu_access import normalize_menu_group_key
from application.portal.interfaces.favorites import can_access_menu_item, menu_groups_with_items
from application.portal.models import PortalMenuGroupAccess, UserAccessRequest


def test_normalize_menu_group_key_maps_japanese_title_to_canonical_key():
    assert normalize_menu_group_key("総務") == "general-affairs"
    assert normalize_menu_group_key("general-affairs") == "general-affairs"
    assert normalize_menu_group_key("生産管理") == "production"


@pytest.mark.django_db
def test_legacy_soumu_group_key_grants_asset_inventory_access(client):
    user = get_user_model().objects.create_user(username="legacy-ga-user")
    general_group, _ = Group.objects.get_or_create(name="一般ユーザー")
    user.groups.add(general_group)
    PortalMenuGroupAccess.objects.create(user=user, group_key="総務")
    access_request, _ = UserAccessRequest.objects.get_or_create(user=user)
    access_request.status = UserAccessRequest.Status.APPROVED
    access_request.save()

    assert can_access_menu_item(user, "asset-inventory") is True
    groups = menu_groups_with_items(user)
    general_affairs = next(group for group in groups if group["key"] == "general-affairs")
    assert any(item["key"] == "asset-inventory" for item in general_affairs["items"])

    client.force_login(user)
    session = client.session
    session["desknet_access_key"] = "test-key"
    session.save()

    response = client.get("/app/general-affairs/asset-inventory")
    assert response.status_code != 403


@pytest.mark.django_db
def test_general_affairs_user_sees_asset_inventory_in_menu_and_can_open_page(client, monkeypatch):
    from application.asset_inventory.domain.repositories.ports import ListPageResult, ReconcileCounts

    user = get_user_model().objects.create_user(username="ga-menu-user")
    general_group, _ = Group.objects.get_or_create(name="一般ユーザー")
    user.groups.add(general_group)
    PortalMenuGroupAccess.objects.create(user=user, group_key="general-affairs")
    access_request, _ = UserAccessRequest.objects.get_or_create(user=user)
    access_request.status = UserAccessRequest.Status.APPROVED
    access_request.save()

    client.force_login(user)
    dashboard = client.get("/app")
    assert dashboard.status_code == 200
    dashboard_html = dashboard.content.decode("utf-8")
    assert "資産棚卸結果" in dashboard_html

    empty_result = ListPageResult(
        management_rows=(),
        selected_management_id="",
        rows=(),
        all_rows=(),
        filtered_rows=(),
        counts=ReconcileCounts(),
        filtered_counts=ReconcileCounts(),
        site_options=(),
        site_filter="all",
        status_filter="all",
        plate_filter="all",
        asset_number_filter="",
        asset_number_options=(),
        page=1,
        page_size=50,
        total_pages=1,
        sort_specs=(),
    )
    monkeypatch.setattr(
        "application.asset_inventory.interfaces.views.list_page_usecase",
        lambda: type("U", (), {"execute": lambda self, access_key, query, session=None: empty_result})(),
    )

    session = client.session
    session["desknet_access_key"] = "test-key"
    session.save()

    response = client.get("/app/general-affairs/asset-inventory")
    assert response.status_code == 200
    assert "資産棚卸結果" in response.content.decode("utf-8")
