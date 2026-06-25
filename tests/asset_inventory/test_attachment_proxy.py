from __future__ import annotations

import pytest

from apps.asset_inventory.domain.attachment_proxy import (
    fetch_attachment_content,
    is_allowed_attachment_url,
)


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
        captured["auth"] = request.get_header("X-Desknets-Auth")
        return FakeResponse()

    monkeypatch.setattr(
        "apps.asset_inventory.domain.attachment_proxy.urllib.request.urlopen",
        fake_urlopen,
    )

    content, content_type = fetch_attachment_content(
        source_url="https://maruei01.dn-cloud.com/cgi-bin/dneo/appsuite.cgi?action=download_data_file&id=1",
        access_key="secret",
        timeout=5,
    )
    assert content == b"photo-bytes"
    assert content_type == "image/jpeg"
    assert "download_data_file" in str(captured["url"])
