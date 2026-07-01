import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from applications.portal.favorites import can_access_menu_item, is_menu_path_active, menu_groups_with_items
from applications.portal.views import delete_portal_user
from applications.portal.models import PortalMenuGroupAccess, PortalNotice, UserAccessRequest, UserFavoriteMenu


@pytest.fixture
def user(db):
    user = get_user_model().objects.create_user(username="10001", last_name="橋爪", first_name="良典")
    admin_group, _ = Group.objects.get_or_create(name="管理者")
    user.groups.add(admin_group)
    return user


@pytest.mark.django_db
def test_dashboard_shows_portal_title_and_favorite_controls(client, user):
    for group_key in ["company", "hr", "general-affairs", "finance", "sales", "production", "quality", "management"]:
        PortalMenuGroupAccess.objects.get_or_create(user=user, group_key=group_key)
    client.force_login(user)

    response = client.get("/app")

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "ようこそ、橋爪 良典 さん" in html
    assert "業務支援ポータル" in html
    assert "基幹システム連携ポータル" not in html
    assert "基幹データ連携ポータル" not in html
    assert "<p>メニュー</p>" not in html
    assert "全社" in html
    assert "人事" in html
    assert "総務" in html
    assert "財務" in html
    assert "営業" in html
    assert "生産管理" in html
    assert "品保" in html
    assert "管理" in html
    assert "完成品" in html
    assert "支給品" in html
    assert "検収書比較" in html
    assert 'class="sidebar-menu-branch"' in html
    assert "<details" in html
    assert 'class="sidebar-menu-group"' in html
    assert "お知らせ" in html
    assert "承認依頼" in html
    assert "ユーザー管理" in html
    assert "データベース" in html
    assert 'data-menu-key="inventory-order-alert"' not in html
    assert 'class="sidebar-nav"' in html
    assert "sidebar-nav" in html
    assert "♡" not in html.split('class="sidebar-nav"')[1].split("</nav>")[0]
    assert "お気に入りはありません" in html
    assert "お知らせ" in html
    assert "現在、お知らせはありません。" in html
    assert "portal-sidebar.js" in html


@pytest.mark.django_db
def test_notices_can_be_managed_and_shown_on_dashboard(client, user):
    PortalMenuGroupAccess.objects.create(user=user, group_key="management")
    client.force_login(user)

    create_response = client.post(
        "/app/management/notices",
        {
            "title": "メンテナンス",
            "body": "本日18時から作業します。",
            "is_published": "on",
        },
    )

    assert create_response.status_code == 302
    notice = PortalNotice.objects.get(title="メンテナンス")
    assert notice.body == "本日18時から作業します。"
    assert notice.is_published is True

    notices_page = client.get("/app/management/notices").content.decode("utf-8")
    assert "portal-menu-page" in notices_page

    dashboard = client.get("/app")
    dashboard_html = dashboard.content.decode("utf-8")
    assert "portal-menu-page" in dashboard_html
    assert "メンテナンス" in dashboard_html
    assert "本日18時から作業します。" in dashboard_html

    PortalNotice.objects.create(title="新しいお知らせ", body="新しい内容", created_by=user)
    ordered_dashboard_html = client.get("/app").content.decode("utf-8")
    assert ordered_dashboard_html.index("新しいお知らせ") < ordered_dashboard_html.index("メンテナンス")

    edit_response = client.post(
        "/app/management/notices",
        {
            "notice_id": str(notice.id),
            "title": "メンテナンス更新",
            "body": "作業時間を変更しました。",
        },
    )

    assert edit_response.status_code == 302
    notice.refresh_from_db()
    assert notice.title == "メンテナンス更新"
    assert notice.body == "作業時間を変更しました。"
    assert notice.is_published is False

    hidden_dashboard = client.get("/app").content.decode("utf-8")
    assert "メンテナンス更新" not in hidden_dashboard

    delete_response = client.post(
        "/app/management/notices",
        {
            "notice_id": str(notice.id),
            "action": "delete",
        },
    )

    assert delete_response.status_code == 302
    assert not PortalNotice.objects.filter(id=notice.id).exists()


@pytest.mark.django_db
def test_general_user_sees_only_assigned_department_menu(client):
    general_user = get_user_model().objects.create_user(username="10004")
    general_group, _ = Group.objects.get_or_create(name="一般ユーザー")
    general_user.groups.add(general_group)
    PortalMenuGroupAccess.objects.create(user=general_user, group_key="production")
    client.force_login(general_user)

    response = client.get("/app")

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "生産管理" in html
    assert "5年9組" in html
    assert "完成品" in html
    assert "支給品" in html
    assert "検収書比較" in html
    assert 'class="sidebar-menu-branch"' in html
    assert "<details" in html
    assert 'class="sidebar-menu-group"' in html
    assert "承認依頼" not in html
    assert "データベース" not in html
    assert "営業" not in html


@pytest.mark.django_db
def test_general_user_cannot_open_management_directly(client):
    general_user = get_user_model().objects.create_user(username="10005")
    general_group, _ = Group.objects.get_or_create(name="一般ユーザー")
    general_user.groups.add(general_group)
    PortalMenuGroupAccess.objects.create(user=general_user, group_key="production")
    client.force_login(general_user)

    response = client.get("/app/management/database")

    assert response.status_code == 403


@pytest.mark.django_db
def test_user_without_department_cannot_open_department_app(client):
    general_user = get_user_model().objects.create_user(username="10006")
    client.force_login(general_user)

    response = client.get("/app/production/five-year-nine")

    assert response.status_code == 403


def test_is_menu_path_active():
    assert is_menu_path_active(
        "/app/production/receipt-comparison",
        "/app/production/receipt-comparison?type=finished-product",
        "finished-product",
    )
    assert is_menu_path_active(
        "/app/production/receipt-comparison/export",
        "/app/production/receipt-comparison?type=finished-product",
        "finished-product",
    )
    assert not is_menu_path_active(
        "/app/production/five-year-nine",
        "/app/production/receipt-comparison?type=finished-product",
        "finished-product",
    )


@pytest.mark.django_db
def test_receipt_comparison_branch_uses_same_row_layout_as_sibling_items(client):
    user = get_user_model().objects.create_user(username="branch-layout-user")
    group, _ = Group.objects.get_or_create(name="一般ユーザー")
    user.groups.add(group)
    PortalMenuGroupAccess.objects.create(user=user, group_key="production")
    client.force_login(user)

    response = client.get("/app")

    html = response.content.decode("utf-8")
    assert 'class="sidebar-menu-branch-icon"' in html
    assert 'class="sidebar-menu-branch-label">検収書比較</span>' in html
    assert 'class="sidebar-menu-item"' in html


@pytest.mark.django_db
def test_receipt_comparison_menu_is_grouped_under_parent(client):
    user = get_user_model().objects.create_user(username="menu-structure-user")
    group, _ = Group.objects.get_or_create(name="一般ユーザー")
    user.groups.add(group)
    PortalMenuGroupAccess.objects.create(user=user, group_key="production")

    groups = menu_groups_with_items(user)
    production = next(group for group in groups if group["key"] == "production")
    receipt_parent = next(item for item in production["items"] if item["key"] == "receipt-comparison")

    assert receipt_parent["title"] == "検収書比較"
    assert receipt_parent["href"] == ""
    assert [child["title"] for child in receipt_parent["children"]] == ["完成品", "支給品"]
    assert receipt_parent["is_expanded"] is False


@pytest.mark.django_db
def test_active_receipt_comparison_page_expands_group_and_branch(client):
    user = get_user_model().objects.create_user(username="receipt-expand-user")
    group, _ = Group.objects.get_or_create(name="一般ユーザー")
    user.groups.add(group)
    PortalMenuGroupAccess.objects.create(user=user, group_key="production")
    client.force_login(user)

    response = client.get("/app/production/receipt-comparison?type=finished-product")

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert 'data-menu-group-key="production"' in html
    assert 'data-menu-key="receipt-comparison"' in html
    assert 'data-sidebar-force-open="true"' in html
    assert "<details" in html and " open" in html
    assert 'href="/app/production/receipt-comparison?type=finished-product" class="is-active"' in html


@pytest.mark.django_db
def test_menu_groups_expand_when_current_path_matches(client):
    user = get_user_model().objects.create_user(username="expand-menu-user")
    group, _ = Group.objects.get_or_create(name="一般ユーザー")
    user.groups.add(group)
    PortalMenuGroupAccess.objects.create(user=user, group_key="production")

    groups = menu_groups_with_items(user, "/app/production/receipt-comparison", "supplied-parts")
    production = next(group for group in groups if group["key"] == "production")
    receipt_parent = next(item for item in production["items"] if item["key"] == "receipt-comparison")

    assert production["is_expanded"] is True
    assert receipt_parent["is_expanded"] is True
    assert receipt_parent["children"][1]["is_active"] is True


@pytest.mark.django_db
def test_is_menu_favorited(user):
    from applications.portal.favorites import is_menu_favorited
    from applications.portal.models import UserFavoriteMenu

    assert is_menu_favorited(user, "five-year-nine") is False
    UserFavoriteMenu.objects.create(user=user, menu_key="five-year-nine", sort_order=0)
    assert is_menu_favorited(user, "five-year-nine") is True


@pytest.mark.django_db
def test_page_favorite_toggle_context(user):
    from applications.portal.favorites import page_favorite_toggle_context
    from applications.portal.models import UserFavoriteMenu

    assert page_favorite_toggle_context(user, "notices") == {
        "menu_key": "notices",
        "menu_title": "お知らせ",
        "is_favorite": False,
    }
    UserFavoriteMenu.objects.create(user=user, menu_key="notices", sort_order=0)
    assert page_favorite_toggle_context(user, "notices")["is_favorite"] is True


@pytest.mark.django_db
def test_parent_menu_cannot_be_favorited(client, user):
    PortalMenuGroupAccess.objects.create(user=user, group_key="production")
    client.force_login(user)

    response = client.post(
        "/api/favorite-menus",
        data=json.dumps({"menuKey": "receipt-comparison"}),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert not UserFavoriteMenu.objects.filter(user=user, menu_key="receipt-comparison").exists()


@pytest.mark.django_db
def test_can_access_parent_menu_when_child_is_accessible(client):
    user = get_user_model().objects.create_user(username="parent-access-user")
    group, _ = Group.objects.get_or_create(name="一般ユーザー")
    user.groups.add(group)
    PortalMenuGroupAccess.objects.create(user=user, group_key="production")

    assert can_access_menu_item(user, "receipt-comparison") is True


@pytest.mark.django_db
def test_favorite_menu_can_be_added_deleted_and_rendered(client, user):
    PortalMenuGroupAccess.objects.create(user=user, group_key="production")
    client.force_login(user)

    add_response = client.post(
        "/api/favorite-menus",
        data=json.dumps({"menuKey": "five-year-nine"}),
        content_type="application/json",
    )

    assert add_response.status_code == 200
    assert UserFavoriteMenu.objects.filter(user=user, menu_key="five-year-nine").exists()

    dashboard = client.get("/app")
    html = dashboard.content.decode("utf-8")
    assert 'class="favorite-card"' in html
    assert "♥" in html
    assert "<span>生産管理</span>" in html

    delete_response = client.delete("/api/favorite-menus/five-year-nine")

    assert delete_response.status_code == 200
    assert not UserFavoriteMenu.objects.filter(user=user, menu_key="five-year-nine").exists()


@pytest.mark.django_db
def test_favorite_order_can_be_saved(client, user):
    PortalMenuGroupAccess.objects.create(user=user, group_key="production")
    UserFavoriteMenu.objects.create(user=user, menu_key="five-year-nine", sort_order=5)
    client.force_login(user)

    response = client.patch(
        "/api/favorite-menus/order",
        data=json.dumps({"menuKeys": ["five-year-nine"]}),
        content_type="application/json",
    )

    assert response.status_code == 200
    favorite = UserFavoriteMenu.objects.get(user=user, menu_key="five-year-nine")
    assert favorite.sort_order == 0


@pytest.mark.django_db
def test_user_management_shows_user_information(client, user):
    PortalMenuGroupAccess.objects.create(user=user, group_key="management")
    PortalMenuGroupAccess.objects.create(user=user, group_key="production")
    client.force_login(user)

    response = client.get("/app/management/users")

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "<h1>ユーザー管理</h1>" in html
    assert 'class="portal-page-description"' in html
    assert "登録済みユーザーの情報、権限、利用可能グループを確認できます。" in html
    assert 'data-menu-key="user-management"' in html
    assert "10001" in html
    assert "橋爪" in html
    assert "良典" in html
    assert "管理者" in html
    assert "生産管理" in html
    assert 'value="management"' not in html
    assert "user-edit-dialog" in html
    assert 'name="last_name"' in html
    assert 'name="first_name"' in html
    assert 'name="email"' in html
    assert 'name="role"' in html
    assert 'name="menu_groups"' in html
    assert "sort=username&dir=desc" in html
    assert "sort=last_name&dir=asc" in html

    sorted_response = client.get("/app/management/users?sort=last_name&dir=desc")

    assert sorted_response.status_code == 200
    sorted_html = sorted_response.content.decode("utf-8")
    assert "sort=last_name&dir=asc" in sorted_html
    assert "▼" in sorted_html


@pytest.mark.django_db
def test_user_management_admin_role_ignores_menu_groups(client, user):
    PortalMenuGroupAccess.objects.create(user=user, group_key="management")
    client.force_login(user)

    response = client.post(
        "/app/management/users",
        {
            "user_id": str(user.id),
            "last_name": "橋爪",
            "first_name": "良典",
            "email": "",
            "role": "管理者",
            "menu_groups": ["company", "production"],
        },
    )

    assert response.status_code == 302
    user.refresh_from_db()
    assert set(user.groups.values_list("name", flat=True)) == {"管理者"}
    assert not user.portal_menu_group_accesses.exists()


@pytest.mark.django_db
def test_user_management_shows_delete_button_for_other_users(client, user):
    PortalMenuGroupAccess.objects.create(user=user, group_key="management")
    target_user = get_user_model().objects.create_user(username="10002", last_name="山田", first_name="花子")
    client.force_login(user)

    response = client.get("/app/management/users")

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert 'value="delete"' in html
    assert "danger-button user-edit-delete-button" in html
    assert f'user-edit-dialog-{target_user.id}' in html
    assert html.count('value="delete"') == 1
    self_dialog_html = html.split(f'user-edit-dialog-{user.id}"', 1)[1].split("</dialog>", 1)[0]
    assert 'value="delete"' not in self_dialog_html


@pytest.mark.django_db
def test_user_management_deletes_user(client, user):
    PortalMenuGroupAccess.objects.create(user=user, group_key="management")
    target_user = get_user_model().objects.create_user(username="10002", last_name="山田", first_name="花子")
    UserAccessRequest.objects.create(user=target_user)
    UserFavoriteMenu.objects.create(user=target_user, menu_key="five-year-nine", sort_order=0)
    PortalMenuGroupAccess.objects.create(user=target_user, group_key="production")
    client.force_login(user)

    response = client.post(
        "/app/management/users",
        {
            "user_id": str(target_user.id),
            "action": "delete",
        },
    )

    assert response.status_code == 302
    assert not get_user_model().objects.filter(id=target_user.id).exists()
    assert not UserAccessRequest.objects.filter(user_id=target_user.id).exists()
    assert not UserFavoriteMenu.objects.filter(user_id=target_user.id).exists()
    assert not PortalMenuGroupAccess.objects.filter(user_id=target_user.id).exists()


@pytest.mark.django_db
def test_user_management_cannot_delete_self(client, user):
    PortalMenuGroupAccess.objects.create(user=user, group_key="management")
    client.force_login(user)

    response = client.post(
        "/app/management/users",
        {
            "user_id": str(user.id),
            "action": "delete",
        },
    )

    assert response.status_code == 302
    assert get_user_model().objects.filter(id=user.id).exists()


@pytest.mark.django_db
def test_delete_portal_user_returns_false_for_self(user):
    assert delete_portal_user(actor=user, target_user=user) is False
    assert get_user_model().objects.filter(id=user.id).exists()


@pytest.mark.django_db
def test_delete_portal_user_deletes_other_user(user):
    target_user = get_user_model().objects.create_user(username="10002", last_name="山田", first_name="花子")

    assert delete_portal_user(actor=user, target_user=target_user) is True
    assert not get_user_model().objects.filter(id=target_user.id).exists()


@pytest.mark.django_db
def test_user_management_updates_user_information_and_permissions(client, user):
    PortalMenuGroupAccess.objects.create(user=user, group_key="management")
    client.force_login(user)

    response = client.post(
        "/app/management/users",
        {
            "user_id": str(user.id),
            "last_name": "山田",
            "first_name": "花子",
            "email": "hanako@example.local",
            "role": "一般ユーザー",
            "menu_groups": ["company", "production"],
        },
    )

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.last_name == "山田"
    assert user.first_name == "花子"
    assert user.email == "hanako@example.local"
    assert set(user.groups.values_list("name", flat=True)) == {"一般ユーザー"}
    assert set(user.portal_menu_group_accesses.values_list("group_key", flat=True)) == {"company", "production"}


@pytest.mark.django_db
def test_database_viewer_lists_tables_and_rows(client, user):
    PortalMenuGroupAccess.objects.create(user=user, group_key="management")
    client.force_login(user)

    response = client.get("/app/management/database")

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "<h1>データベース</h1>" in html
    assert 'class="portal-page-description"' in html
    assert 'data-menu-key="database"' in html
    assert 'name="table"' in html
    assert "auth_user" in html
    assert "表示するテーブルを選択してください。" in html

    table_response = client.get("/app/management/database?table=auth_user")

    assert table_response.status_code == 200
    table_html = table_response.content.decode("utf-8")
    assert "<h2>auth_user</h2>" in table_html
    assert "sort=username&dir=asc" in table_html
    assert "10001" in table_html
    assert "********" in table_html

    sorted_response = client.get("/app/management/database?table=auth_user&sort=username&dir=desc")

    assert sorted_response.status_code == 200
    sorted_html = sorted_response.content.decode("utf-8")
    assert "ソート: username DESC" in sorted_html
    assert "sort=username&dir=asc" in sorted_html


@pytest.mark.django_db
def test_access_requests_can_be_approved_with_groups(client, user):
    target_user = get_user_model().objects.create_user(username="10002", last_name="申請", first_name="太郎")
    access_request = UserAccessRequest.objects.create(user=target_user)
    PortalMenuGroupAccess.objects.create(user=user, group_key="management")
    client.force_login(user)

    response = client.get("/app/management/access-requests")

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "申請 太郎" in html
    assert "承認待ち" in html
    assert "一般ユーザー" in html
    assert "管理者" in html
    assert "全社" in html
    assert "生産管理" in html
    assert 'value="management"' not in html
    assert 'name="menu_groups"' in html
    assert 'name="role" value="一般ユーザー" checked' in html
    assert 'name="menu_groups" value="' in html
    assert html.index("全社") < html.index("人事") < html.index("総務") < html.index("財務")
    assert html.index("財務") < html.index("営業") < html.index("生産管理") < html.index("品保")

    approve_response = client.post(
        "/app/management/access-requests",
        {
            "request_id": str(access_request.id),
            "action": "approve",
            "role": "一般ユーザー",
            "menu_groups": ["production"],
            "note": "利用可",
        },
    )

    assert approve_response.status_code == 302
    access_request.refresh_from_db()
    assert access_request.status == UserAccessRequest.Status.APPROVED
    assert access_request.note == "利用可"
    assert set(target_user.groups.values_list("name", flat=True)) == {"一般ユーザー"}
    assert set(target_user.portal_menu_group_accesses.values_list("group_key", flat=True)) == {"production"}

    completed_response = client.get("/app/management/access-requests")
    completed_html = completed_response.content.decode("utf-8")
    assert "申請 太郎" not in completed_html
    assert "承認依頼はありません。" in completed_html


@pytest.mark.django_db
def test_access_requests_can_approve_admin_role(client, user):
    target_user = get_user_model().objects.create_user(username="10007", first_name="管理 太郎")
    access_request = UserAccessRequest.objects.create(user=target_user)
    PortalMenuGroupAccess.objects.create(user=user, group_key="management")
    client.force_login(user)

    response = client.post(
        "/app/management/access-requests",
        {
            "request_id": str(access_request.id),
            "action": "approve",
            "role": "管理者",
            "menu_groups": ["company"],
        },
    )

    assert response.status_code == 302
    assert set(target_user.groups.values_list("name", flat=True)) == {"管理者"}
    assert not target_user.portal_menu_group_accesses.exists()


@pytest.mark.django_db
def test_access_requests_can_be_rejected_and_keeps_user(client, user):
    target_user = get_user_model().objects.create_user(username="10003", first_name="拒否 太郎")
    access_request = UserAccessRequest.objects.create(user=target_user)
    group, _ = Group.objects.get_or_create(name="一般ユーザー")
    target_user.groups.add(group)
    PortalMenuGroupAccess.objects.create(user=target_user, group_key="production")
    PortalMenuGroupAccess.objects.create(user=user, group_key="management")
    client.force_login(user)

    response = client.post(
        "/app/management/access-requests",
        {"request_id": str(access_request.id), "action": "reject", "note": "対象外"},
    )

    assert response.status_code == 302
    assert get_user_model().objects.filter(username="10003").exists()
    access_request.refresh_from_db()
    assert access_request.status == UserAccessRequest.Status.REJECTED
    assert access_request.note == "対象外"
    assert not target_user.groups.exists()
    assert not target_user.portal_menu_group_accesses.exists()

    completed_response = client.get("/app/management/access-requests")
    completed_html = completed_response.content.decode("utf-8")
    assert "拒否 太郎" not in completed_html
    assert "承認依頼はありません。" in completed_html


@pytest.mark.django_db
def test_pending_user_cannot_operate_until_approved(client):
    pending_user = get_user_model().objects.create_user(username="20001", first_name="承認待ち")
    UserAccessRequest.objects.create(user=pending_user)
    client.force_login(pending_user)

    dashboard_response = client.get("/app")
    search_response = client.get("/app/production/five-year-nine")
    status_response = client.get("/app/access-status")
    api_response = client.post(
        "/api/favorite-menus",
        data=json.dumps({"menuKey": "five-year-nine"}),
        content_type="application/json",
    )

    assert dashboard_response.status_code == 302
    assert dashboard_response["Location"] == "/app/access-status"
    assert search_response.status_code == 302
    assert search_response["Location"] == "/app/access-status"
    assert status_response.status_code == 200
    assert "管理者の承認をお待ちください" in status_response.content.decode("utf-8")
    assert api_response.status_code == 403
    assert api_response.json()["error"]["message"] == "利用承認が完了していません。"


@pytest.mark.django_db
def test_approved_user_can_operate(client):
    approved_user = get_user_model().objects.create_user(username="20002", first_name="承認済み")
    UserAccessRequest.objects.create(user=approved_user, status=UserAccessRequest.Status.APPROVED)
    PortalMenuGroupAccess.objects.create(user=approved_user, group_key="production")
    client.force_login(approved_user)

    response = client.get("/app")

    assert response.status_code == 200
    assert "お気に入り" in response.content.decode("utf-8")


def test_sidebar_nav_scrolls_when_menu_overflows_viewport():
    from pathlib import Path

    css = (Path(__file__).resolve().parents[3] / "static" / "css" / "app.css").read_text(encoding="utf-8")
    sidebar_rule = css.split(".sidebar {")[1].split("}")[0]
    assert "height: 100dvh" in sidebar_rule
    assert "max-height: 100dvh" in sidebar_rule
    assert "align-self: flex-start" in sidebar_rule
    assert "align-self: stretch" not in sidebar_rule
    assert "background: #0f172a" in css.split(".sidebar-nav {")[1].split("}")[0]
    nav_rule = css.split(".sidebar-nav {")[1].split("}")[0]
    assert "display: grid" in nav_rule
    assert "flex: 1 1 auto" in nav_rule
    assert "overflow-y: auto" in nav_rule
    assert "align-content: start" in nav_rule
    assert ".sidebar-nav::-webkit-scrollbar-thumb" in css
    assert "scrollbar-color: #475569 #0f172a" in css
    branch_panel_rule = css.split(".sidebar-menu-branch-panel {")[1].split("}")[0]
    assert "border-left" not in branch_panel_rule
    group_panel_rule = css.split(".sidebar-menu-group-panel {")[1].split("}")[0]
    assert "--sidebar-level1-gutter: 16px" in group_panel_rule
    assert "padding: 1px 0 0 20px" in group_panel_rule
    assert ".sidebar-menu-branch > summary {\n  display: grid;\n  grid-template-columns: var(--sidebar-level1-gutter) minmax(0, 1fr);" in css
    assert "padding-left: calc(var(--sidebar-level1-gutter) + var(--sidebar-level1-gap))" in css.split(".sidebar-menu-group-panel > .sidebar-menu-item > a {")[1].split("}")[0]
    group_summary_rule = css.split(".sidebar-menu-group > summary {")[1].split("}")[0]
    assert "padding: 8px 10px 8px 12px" in group_summary_rule
    menu_item_rule = css.split(".sidebar-menu-item a {")[1].split("}")[0]
    assert "padding: 5px 10px" in menu_item_rule
    foot_rule = css.split(".sidebar-foot {")[1].split("}")[0]
    assert "flex-shrink: 0" in foot_rule
