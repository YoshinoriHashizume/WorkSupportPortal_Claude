"""メニュー利用ログを記録するミドルウェアのテスト（TC-UI-001〜011）。"""

from __future__ import annotations

import logging

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse, JsonResponse
from django.test import override_settings
from django.urls import path

from application.portal.infrastructure.persistence.menu_usage_log_repository import (
    DjangoMenuUsageLogRepository,
)
from application.portal.models import MenuUsageLog, PortalMenuGroupAccess, UserAccessRequest

USAGE_LOGGING_MIDDLEWARE = "application.portal.interfaces.usage_logging.UsageLoggingMiddleware"
ACCESS_APPROVAL_MIDDLEWARE = "application.portal.interfaces.middleware.AccessApprovalMiddleware"
USAGE_LOGGING_LOGGER = "application.portal.interfaces.usage_logging"


def _middleware_with_usage_logging() -> list[str]:
    """`settings.MIDDLEWARE` に本ミドルウェアを差し込んだ一覧を返す（登録前でもテストできるようにする）。"""
    middleware = list(settings.MIDDLEWARE)
    if USAGE_LOGGING_MIDDLEWARE in middleware:
        return middleware
    middleware.insert(middleware.index(ACCESS_APPROVAL_MIDDLEWARE) + 1, USAGE_LOGGING_MIDDLEWARE)
    return middleware


with_usage_logging = override_settings(MIDDLEWARE=_middleware_with_usage_logging())


def _stub_csv_view(request):
    """出力エンドポイントの応答（200 ＋ attachment）を模した応答を返す。"""
    response = HttpResponse("列1,列2\n", content_type="text/csv; charset=cp932")
    response["Content-Disposition"] = 'attachment; filename="stub.csv"'
    return response


def _stub_json_view(request):
    return JsonResponse({"success": True, "rows": []})


urlpatterns = [
    path("app/sales/shipment-trend/export.csv", _stub_csv_view),
    path("api/shipment-trend/rows", _stub_json_view),
]

with_stub_urls = override_settings(ROOT_URLCONF=__name__)


@pytest.fixture
def admin_user(db):
    return get_user_model().objects.create_superuser(username="usage-admin", password="pass-usage-admin")


@pytest.fixture
def general_user(db):
    user = get_user_model().objects.create_user(username="usage-general", password="pass-usage-general")
    group, _ = Group.objects.get_or_create(name="一般ユーザー")
    user.groups.add(group)
    return user


@pytest.fixture
def production_user(db):
    user = get_user_model().objects.create_user(username="usage-production", password="pass-usage-production")
    group, _ = Group.objects.get_or_create(name="一般ユーザー")
    user.groups.add(group)
    PortalMenuGroupAccess.objects.create(user=user, group_key="production")
    return user


@pytest.fixture
def pending_user(db):
    user = get_user_model().objects.create_user(username="usage-pending", password="pass-usage-pending")
    UserAccessRequest.objects.create(user=user, status=UserAccessRequest.Status.PENDING)
    return user


def _raise_on_record(self, *, user, menu_key, usage_type):
    raise RuntimeError("記録に失敗しました")


@pytest.mark.django_db
@with_usage_logging
def test_middleware_records_view_for_authenticated_page_request(client, admin_user):
    """TC-UI-001: 許可済みユーザーのメニュー画面表示を VIEW として 1 件記録する。"""
    client.force_login(admin_user)

    response = client.get("/app/management/notices")

    assert response.status_code == 200
    log = MenuUsageLog.objects.get()
    assert log.user_id == admin_user.id
    assert log.menu_key == "notices"
    assert log.usage_type == "VIEW"
    assert log.used_at is not None


@pytest.mark.django_db
@with_usage_logging
def test_middleware_skips_anonymous_request(client):
    """TC-UI-002: 未認証のリクエストは記録しない。"""
    response = client.get("/app/management/notices")

    assert response.status_code == 302
    assert MenuUsageLog.objects.count() == 0


@pytest.mark.django_db
@with_usage_logging
def test_middleware_skips_forbidden_response(client, general_user):
    """TC-UI-003: 403 は記録しない。"""
    client.force_login(general_user)

    response = client.get("/app/management/notices")

    assert response.status_code == 403
    assert MenuUsageLog.objects.count() == 0


@pytest.mark.django_db
@with_usage_logging
def test_middleware_skips_redirect_response(client, pending_user):
    """TC-UI-004: 302（利用申請状況へのリダイレクト）は記録しない。"""
    client.force_login(pending_user)

    response = client.get("/app/production/receipt-comparison?type=finished-product")

    assert response.status_code == 302
    assert response.headers["Location"] == "/app/access-status"
    assert MenuUsageLog.objects.count() == 0


@pytest.mark.django_db
@with_usage_logging
@with_stub_urls
def test_middleware_skips_api_json_response(client, admin_user):
    """TC-UI-005: JSON 応答（画面表示ではない）は記録しない。"""
    client.force_login(admin_user)

    response = client.get("/api/shipment-trend/rows")

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/json")
    assert MenuUsageLog.objects.count() == 0


@pytest.mark.django_db
@with_usage_logging
@with_stub_urls
def test_middleware_records_export_for_csv_download(client, admin_user):
    """TC-UI-006: 出力エンドポイントの添付応答を EXPORT として 1 件記録する。"""
    client.force_login(admin_user)

    response = client.get("/app/sales/shipment-trend/export.csv")

    assert response.status_code == 200
    assert "attachment" in response.headers["Content-Disposition"]
    log = MenuUsageLog.objects.get()
    assert log.user_id == admin_user.id
    assert log.menu_key == "shipment-trend-list"
    assert log.usage_type == "EXPORT"


@pytest.mark.django_db
@with_usage_logging
def test_middleware_returns_response_when_recording_fails(client, admin_user, monkeypatch, caplog):
    """TC-UI-007: 記録に失敗しても業務操作の応答はそのまま返り、warning だけが残る。"""
    monkeypatch.setattr(DjangoMenuUsageLogRepository, "record", _raise_on_record)
    client.force_login(admin_user)

    with caplog.at_level(logging.WARNING, logger=USAGE_LOGGING_LOGGER):
        response = client.get("/app/management/notices")

    assert response.status_code == 200
    assert MenuUsageLog.objects.count() == 0
    warnings = [record for record in caplog.records if record.name == USAGE_LOGGING_LOGGER]
    assert len(warnings) == 1
    assert warnings[0].levelno == logging.WARNING


@pytest.mark.django_db
@with_usage_logging
def test_middleware_hides_recording_failure_from_user(client, admin_user, monkeypatch):
    """TC-UI-008: 記録の失敗を画面に見せない。"""
    monkeypatch.setattr(DjangoMenuUsageLogRepository, "record", _raise_on_record)
    client.force_login(admin_user)

    response = client.get("/app/management/notices")

    body = response.content.decode("utf-8")
    assert response.status_code == 200
    assert "記録に失敗しました" not in body
    assert "Traceback" not in body
    assert "RuntimeError" not in body


@pytest.mark.django_db
@with_usage_logging
def test_middleware_records_once_per_request(client, admin_user):
    """TC-UI-009: 1 リクエストにつき記録は 1 件だけ。"""
    client.force_login(admin_user)

    client.get("/app/management/notices")

    assert MenuUsageLog.objects.count() == 1


def test_middleware_is_registered_after_access_approval():
    """TC-UI-010: `settings.MIDDLEWARE` で `AccessApprovalMiddleware` の直後に置かれている。"""
    middleware = list(settings.MIDDLEWARE)

    assert USAGE_LOGGING_MIDDLEWARE in middleware
    assert middleware.index(USAGE_LOGGING_MIDDLEWARE) == middleware.index(ACCESS_APPROVAL_MIDDLEWARE) + 1


@pytest.mark.django_db
@with_usage_logging
def test_middleware_records_once_for_legacy_url_redirect(client, production_user):
    """TC-UI-011: 旧 URL 経由（302 → 遷移先）でも記録は遷移先の 1 件だけ。"""
    client.force_login(production_user)

    response = client.get("/app/production/receipt-comparison/finished-product", follow=True)

    assert response.status_code == 200
    assert response.redirect_chain == [("/app/production/receipt-comparison?type=finished-product", 302)]
    log = MenuUsageLog.objects.get()
    assert log.menu_key == "receipt-comparison-finished-product"
    assert log.usage_type == "VIEW"
