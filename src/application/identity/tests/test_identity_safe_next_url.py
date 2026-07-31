from __future__ import annotations

import pytest
from django.test import RequestFactory

from application.identity.interfaces.views import _safe_next_url


@pytest.fixture
def rf() -> RequestFactory:
    return RequestFactory()


def test_safe_next_url_uses_post_next_when_allowed(rf, settings):
    settings.LOGIN_REDIRECT_URL = "/app/"
    request = rf.post("/auth/login", {"next": "/app/receipt-comparison/"})
    request.META["HTTP_HOST"] = "testserver"

    assert _safe_next_url(request) == "/app/receipt-comparison/"


def test_safe_next_url_falls_back_when_external_redirect(rf, settings):
    settings.LOGIN_REDIRECT_URL = "/app/"
    request = rf.post("/auth/login", {"next": "https://evil.example.com/"})
    request.META["HTTP_HOST"] = "testserver"

    assert _safe_next_url(request) == "/app/"


def test_safe_next_url_uses_get_next_when_post_missing(rf, settings):
    settings.LOGIN_REDIRECT_URL = "/app/"
    request = rf.get("/auth/login", {"next": "/app/access-status"})
    request.META["HTTP_HOST"] = "testserver"

    assert _safe_next_url(request) == "/app/access-status"


def test_safe_next_url_uses_login_redirect_when_next_missing(rf, settings):
    settings.LOGIN_REDIRECT_URL = "/app/dashboard"
    request = rf.get("/auth/login")
    request.META["HTTP_HOST"] = "testserver"

    assert _safe_next_url(request) == "/app/dashboard"
