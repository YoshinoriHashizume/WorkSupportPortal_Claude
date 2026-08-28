"""利用状況画面・CSV 出力の Interfaces 層テスト（test-design.md TC-UI-020〜041）。"""

from __future__ import annotations

import csv
import io
from datetime import timedelta
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import resolve, reverse
from django.utils import timezone

from application.portal.domain.value_objects.constants import (
    ADMIN_GROUP_NAME,
    GENERAL_USER_GROUP_NAME,
)
from application.portal.domain.value_objects.usage_period import MESSAGE_OUT_OF_ORDER
from application.portal.domain.value_objects.usage_record import (
    USAGE_TYPE_EXPORT,
    USAGE_TYPE_VIEW,
)
from application.portal.domain.value_objects.usage_status_display import (
    EXPORT_LOG_SORT_LABELS,
    MENU_USAGE_SORT_LABELS,
    RETIRED_MENU_SUFFIX,
    UNKNOWN_USER_LABEL,
    UNUSED_GRANT_SORT_LABELS,
    USAGE_STATUS_PURPOSE_NOTE,
    USER_USAGE_SORT_LABELS,
)
from application.portal.models import MenuUsageLog, PortalMenuGroupAccess, UserAccessRequest
from application.portal.use_cases.usage_status import (
    MESSAGE_ROW_LIMIT_EXCEEDED,
    CsvPayload,
    UsageStatus,
)
from application.shared.domain.value_objects.list_table import DEFAULT_PAGE_SIZE

USAGE_STATUS_URL = "/app/management/usage-status"
USAGE_STATUS_EXPORT_URL = "/app/management/usage-status/export.csv"

LIST_CLIENT_JS_PATH = (
    Path(__file__).resolve().parents[3] / "static" / "js" / "usage-status-list-client.js"
)

SECTION_LABELS = {
    "menus": MENU_USAGE_SORT_LABELS,
    "users": USER_USAGE_SORT_LABELS,
    "unused-grants": UNUSED_GRANT_SORT_LABELS,
    "exports": EXPORT_LOG_SORT_LABELS,
}


# --- テストデータの準備 -------------------------------------------------------


def _approve(user):
    access_request, _ = UserAccessRequest.objects.get_or_create(user=user)
    access_request.status = UserAccessRequest.Status.APPROVED
    access_request.save()
    return user


def _create_admin(username: str = "usage-admin"):
    user = get_user_model().objects.create_user(
        username=username, last_name="管理", first_name="太郎"
    )
    group, _ = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
    user.groups.add(group)
    return _approve(user)


def _create_general_user(
    username: str = "usage-general",
    *,
    menu_group_keys: tuple[str, ...] = ("sales",),
    is_active: bool = True,
):
    user = get_user_model().objects.create_user(
        username=username, last_name="一般", first_name="花子"
    )
    group, _ = Group.objects.get_or_create(name=GENERAL_USER_GROUP_NAME)
    user.groups.add(group)
    for group_key in menu_group_keys:
        PortalMenuGroupAccess.objects.create(user=user, group_key=group_key)
    _approve(user)
    if not is_active:
        user.is_active = False
        user.save()
    return user


def _record_log(*, user, menu_key: str, usage_type: str = USAGE_TYPE_VIEW, days_ago: int = 1):
    return MenuUsageLog.objects.create(
        user=user,
        menu_key=menu_key,
        usage_type=usage_type,
        used_at=timezone.now() - timedelta(days=days_ago),
    )


def _csv_rows(response) -> list[list[str]]:
    text = response.content.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


# --- 認可・到達性 -------------------------------------------------------------


@pytest.mark.django_db
def test_usage_status_page_returns_200_for_admin(client):
    client.force_login(_create_admin())

    response = client.get(USAGE_STATUS_URL)

    assert response.status_code == 200
    assert "portal/usage_status.html" in [template.name for template in response.templates]


@pytest.mark.django_db
def test_usage_status_page_forbids_general_user(client):
    client.force_login(_create_general_user())

    response = client.get(USAGE_STATUS_URL)

    assert response.status_code == 403


@pytest.mark.django_db
def test_usage_status_export_forbids_general_user(client):
    client.force_login(_create_general_user())

    response = client.get(USAGE_STATUS_EXPORT_URL, {"section": "menus"})

    assert response.status_code == 403


@pytest.mark.django_db
def test_usage_status_page_redirects_anonymous_to_login(client):
    response = client.get(USAGE_STATUS_URL)

    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


@pytest.mark.django_db
def test_usage_status_appears_in_admin_menu_only(client):
    client.force_login(_create_admin())
    admin_dashboard = client.get("/app")
    assert admin_dashboard.status_code == 200
    admin_html = admin_dashboard.content.decode("utf-8")
    assert USAGE_STATUS_URL in admin_html
    assert "利用状況" in admin_html

    client.logout()
    client.force_login(_create_general_user())
    general_dashboard = client.get("/app")
    assert general_dashboard.status_code == 200
    assert USAGE_STATUS_URL not in general_dashboard.content.decode("utf-8")


# --- 画面の表示内容 -----------------------------------------------------------


@pytest.mark.django_db
def test_usage_status_page_always_shows_purpose_note(client):
    client.force_login(_create_admin())

    normal = client.get(USAGE_STATUS_URL)
    invalid = client.get(USAGE_STATUS_URL, {"start": "2026-08-28", "end": "2026-08-27"})

    assert USAGE_STATUS_PURPOSE_NOTE in normal.content.decode("utf-8")
    assert USAGE_STATUS_PURPOSE_NOTE in invalid.content.decode("utf-8")


@pytest.mark.django_db
def test_usage_status_page_defaults_to_last_30_days(client):
    client.force_login(_create_admin())

    response = client.get(USAGE_STATUS_URL)

    today = timezone.localdate()
    assert response.context["start"] == (today - timedelta(days=29)).isoformat()
    assert response.context["end"] == today.isoformat()


@pytest.mark.django_db
def test_usage_status_page_shows_error_for_invalid_period(client):
    admin = _create_admin()
    _record_log(user=admin, menu_key="shipment-trend-list")
    client.force_login(admin)

    response = client.get(USAGE_STATUS_URL, {"start": "2026-08-28", "end": "2026-08-27"})

    assert response.status_code == 200
    assert MESSAGE_OUT_OF_ORDER in response.content.decode("utf-8")
    for key in ("menu_usage_page", "user_usage_page", "unused_grant_page", "export_log_page"):
        assert response.context[key].total_count == 0


@pytest.mark.django_db
def test_usage_status_page_shows_no_rows_message_without_logs(client):
    client.force_login(_create_admin())

    response = client.get(USAGE_STATUS_URL)

    summary = response.context["summary"]
    assert summary.usage_count == 0
    assert summary.export_count == 0
    assert summary.active_user_count == 0
    # 未利用付与・出力操作の記録は 0 件。メニュー別は全メニューを 0 回で並べる（REQ-F-008）
    assert response.context["unused_grant_page"].total_count == 0
    assert response.context["export_log_page"].total_count == 0
    assert "該当なし" in response.content.decode("utf-8")
    assert all(row.view_count == 0 for row in response.context["menu_usage_rows"].rows)


@pytest.mark.django_db
def test_usage_status_page_marks_retired_menu(client):
    admin = _create_admin()
    _record_log(user=admin, menu_key="legacy-report")
    client.force_login(admin)

    response = client.get(USAGE_STATUS_URL)

    assert f"legacy-report{RETIRED_MENU_SUFFIX}" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_usage_status_page_shows_unknown_user_label(client):
    admin = _create_admin()
    _record_log(user=None, menu_key="shipment-trend-list", usage_type=USAGE_TYPE_EXPORT)
    client.force_login(admin)

    response = client.get(USAGE_STATUS_URL)

    export_rows = response.context["export_log_rows"].rows
    assert [row.display_name for row in export_rows] == [UNKNOWN_USER_LABEL]
    assert UNKNOWN_USER_LABEL in response.content.decode("utf-8")
    # 物理削除されたユーザーはユーザー別一覧に現れない（承認済み有効ユーザーのみ 0 回で並ぶ）
    user_rows = response.context["user_usage_rows"].rows
    assert UNKNOWN_USER_LABEL not in [row.display_name for row in user_rows]
    assert [row.username for row in user_rows] == ["usage-admin"]
    assert all(row.usage_count == 0 and row.export_count == 0 for row in user_rows)


@pytest.mark.django_db
def test_usage_status_page_excludes_inactive_user_from_user_rows(client):
    admin = _create_admin()
    retired_user = _create_general_user("retired-user", is_active=False)
    _record_log(user=retired_user, menu_key="shipment-trend-list")
    client.force_login(admin)

    response = client.get(USAGE_STATUS_URL)

    usernames = [row.username for row in response.context["user_usage_rows"].rows]
    assert retired_user.username not in usernames
    assert retired_user.username not in [
        row.username for row in response.context["unused_grant_rows"].rows
    ]
    assert response.context["summary"].usage_count == 1
    shipment_row = next(
        row
        for row in response.context["menu_usage_rows"].rows
        if row.menu_title == "出荷トレンド一覧"
    )
    assert shipment_row.view_count == 1


@pytest.mark.django_db
def test_usage_status_page_filters_by_menu_group(client):
    admin = _create_admin()
    _record_log(user=admin, menu_key="shipment-trend-list")
    _record_log(user=admin, menu_key="asset-inventory")
    client.force_login(admin)

    response = client.get(USAGE_STATUS_URL, {"group": "sales"})

    group_titles = {row.group_title for row in response.context["menu_usage_rows"].rows}
    assert group_titles == {"営業"}
    menu_titles = {row.menu_title for row in response.context["menu_usage_rows"].rows}
    assert "資産棚卸結果" not in menu_titles


# --- CSV 出力 -----------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("section", ["menus", "users", "unused-grants", "exports"])
def test_usage_status_export_returns_csv_per_section(client, section):
    client.force_login(_create_admin())

    response = client.get(USAGE_STATUS_EXPORT_URL, {"section": section})

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/csv")
    assert "attachment" in response.headers["Content-Disposition"]
    assert "usage_status" in response.headers["Content-Disposition"]
    assert response.content.startswith("﻿".encode("utf-8"))
    assert _csv_rows(response)[0] == list(SECTION_LABELS[section].values())


@pytest.mark.django_db
def test_usage_status_export_applies_same_period_and_filter(client):
    admin = _create_admin()
    sales_user = _create_general_user("sales-user", menu_group_keys=("sales",))
    _create_general_user("ga-user", menu_group_keys=("general-affairs",))
    _record_log(user=sales_user, menu_key="shipment-trend-list")
    client.force_login(admin)

    today = timezone.localdate()
    params = {
        "start": (today - timedelta(days=6)).isoformat(),
        "end": today.isoformat(),
        "group": "sales",
    }
    page = client.get(USAGE_STATUS_URL, params)
    export = client.get(USAGE_STATUS_EXPORT_URL, {**params, "section": "users"})

    page_usernames = [row.username for row in page.context["user_usage_rows"].rows]
    csv_usernames = [row[0] for row in _csv_rows(export)[1:]]
    assert page_usernames == [sales_user.username]
    assert csv_usernames == page_usernames


@pytest.mark.django_db
def test_usage_status_export_shows_message_over_row_limit(client, monkeypatch):
    client.force_login(_create_admin())
    monkeypatch.setattr(
        UsageStatus,
        "csv_payload",
        lambda self, **kwargs: CsvPayload(rows=None, error_message=MESSAGE_ROW_LIMIT_EXCEEDED),
    )

    response = client.get(USAGE_STATUS_EXPORT_URL, {"section": "menus"})

    assert response.status_code == 200
    assert "Content-Disposition" not in response.headers
    assert MESSAGE_ROW_LIMIT_EXCEEDED in response.content.decode("utf-8")


# --- 自身の利用の記録 ---------------------------------------------------------


@pytest.mark.django_db
def test_usage_status_page_records_its_own_view(client):
    client.force_login(_create_admin())

    client.get(USAGE_STATUS_URL)

    assert (
        MenuUsageLog.objects.filter(menu_key="usage-status", usage_type=USAGE_TYPE_VIEW).count()
        == 1
    )


@pytest.mark.django_db
def test_usage_status_export_records_its_own_export(client):
    client.force_login(_create_admin())

    client.get(USAGE_STATUS_EXPORT_URL, {"section": "menus"})

    assert (
        MenuUsageLog.objects.filter(menu_key="usage-status", usage_type=USAGE_TYPE_EXPORT).count()
        == 1
    )


# --- URL 解決・一覧クライアント -----------------------------------------------


def test_usage_status_url_resolves_before_slug_placeholder():
    from application.portal.interfaces import views

    assert reverse("portal:usage_status") == USAGE_STATUS_URL
    assert reverse("portal:usage_status_export_csv") == USAGE_STATUS_EXPORT_URL
    assert resolve(USAGE_STATUS_URL).func is views.usage_status_page
    assert resolve(USAGE_STATUS_EXPORT_URL).func is views.usage_status_export_csv


def test_usage_status_list_client_js_defines_required_keys():
    source = LIST_CLIENT_JS_PATH.read_text(encoding="utf-8")

    assert "window.PortalListCore" in source
    for element_id in (
        "menu-usage-rows",
        "user-usage-rows",
        "unused-grant-rows",
        "export-log-rows",
    ):
        assert element_id in source
    assert "readBaseStateFromUrl" in source
    assert "renderPagination" in source


# --- 並び替え・ページング -----------------------------------------------------


@pytest.mark.django_db
def test_usage_status_page_applies_page_query_parameters(client):
    client.force_login(_create_admin())

    response = client.get(USAGE_STATUS_URL, {"page": "2", "size": "10"})

    menu_page = response.context["menu_usage_page"]
    assert menu_page.page == 2
    assert menu_page.page_size == 10
    assert len(menu_page.rows) == menu_page.total_count - 10


@pytest.mark.django_db
def test_usage_status_page_ignores_invalid_page_query_parameters(client):
    client.force_login(_create_admin())

    response = client.get(USAGE_STATUS_URL, {"page": "abc", "size": "-1"})

    assert response.status_code == 200
    menu_page = response.context["menu_usage_page"]
    assert menu_page.page == 1
    assert menu_page.page_size == DEFAULT_PAGE_SIZE
