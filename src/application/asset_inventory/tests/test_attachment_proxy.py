from __future__ import annotations

from application.asset_inventory.domain.value_objects.attachment_proxy import is_allowed_attachment_url
from application.asset_inventory.infrastructure.desknet.attachment import fetch_attachment_content
from application.asset_inventory.use_cases.fetch_attachment import FetchAttachment


def test_TC_AIV_DOM_064_allowed_attachment_url():
    login_url = "https://maruei01.dn-cloud.com/cgi-bin/dneo/dneo.cgi"
    source = (
        "https://maruei01.dn-cloud.com/cgi-bin/dneo/appsuite.cgi"
        "?action=download_data_file&app_id=408&field_id=122&id=184"
    )
    assert is_allowed_attachment_url(source, login_url) is True


def test_TC_AIV_DOM_065_reject_foreign_attachment_url():
    login_url = "https://maruei01.dn-cloud.com/cgi-bin/dneo/dneo.cgi"
    assert is_allowed_attachment_url("https://evil.example/photo.jpg", login_url) is False


def test_TC_AIV_DOM_066_fetch_attachment_content(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        headers = {"Content-Type": "image/jpeg"}

        def read(self):
            return b"photo-bytes"

    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(
        "application.asset_inventory.infrastructure.desknet.attachment.urllib.request.urlopen",
        fake_urlopen,
    )

    content, content_type = fetch_attachment_content(
        source_url="https://example.test/file",
        access_key="key-1",
        timeout=9.0,
    )
    assert content == b"photo-bytes"
    assert content_type == "image/jpeg"
    assert captured["timeout"] == 9.0
    assert captured["headers"].get("X-desknets-auth") == "key-1" or any(
        k.lower() == "x-desknets-auth" for k in captured["headers"]
    )


def test_fetch_attachment_usecase_rejects_disallowed_url():
    calls: list[object] = []

    def fetch_fn(**kwargs):
        calls.append(kwargs)
        return b"x", "image/jpeg"

    usecase = FetchAttachment(fetch_fn, desknet_login_url="https://allowed.example/login")
    assert usecase.execute(source_url="https://evil.example/a", access_key="k", timeout=1.0) is None
    assert calls == []


def test_fetch_attachment_usecase_fetches_allowed_url():
    login = "https://maruei01.dn-cloud.com/cgi-bin/dneo/dneo.cgi"
    source = (
        "https://maruei01.dn-cloud.com/cgi-bin/dneo/appsuite.cgi"
        "?action=download_data_file&app_id=408&field_id=122&id=184"
    )

    def fetch_fn(**kwargs):
        return b"ok", "image/png"

    usecase = FetchAttachment(fetch_fn, desknet_login_url=login)
    assert usecase.execute(source_url=source, access_key="k", timeout=1.0) == (b"ok", "image/png")
