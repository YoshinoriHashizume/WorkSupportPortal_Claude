from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from apps.asset_inventory.infrastructure.desknet.client import (
    appsr_api_url,
    encode_fields_parameter,
    extract_api_error_message,
    fetch_all_list_data,
    normalize_list_response,
    record_field_value,
)
from apps.asset_inventory.domain.errors import DesknetApiError


def test_TC_AIV_INF_004_appsr_url():
    assert appsr_api_url("https://example.com/cgi-bin/dneo/dneo.cgi").endswith("appsr.cgi")


def test_record_field_value_extracts_val():
    assert record_field_value({"val": "ABC"}) == "ABC"


def test_record_field_value_extracts_date_dict():
    assert record_field_value({"val": {"year": 2026, "month": 3, "day": 1}}) == "2026-03-01"


def test_TC_AIV_INF_009_record_field_value_attachment_url():
    payload = {
        "val": {
            "attach": {
                "item": [
                    {
                        "url": "https://maruei01.dn-cloud.com/cgi-bin/dneo/appsuite.cgi?action=download_data_file&id=1"
                    }
                ]
            }
        }
    }
    assert record_field_value(payload).endswith("download_data_file&id=1")


def test_TC_AIV_INF_010_record_field_value_empty_attachment():
    payload = {"val": {"attach": {"item": []}}}
    assert record_field_value(payload) == ""


def test_TC_AIV_INF_005_encode_fields_parameter():
    encoded = encode_fields_parameter(("データID", "棚卸項目"))
    assert encoded == '[{"field_name": "データID"}, {"field_name": "棚卸項目"}]'


def test_TC_AIV_INF_006_extract_api_error_message():
    assert extract_api_error_message({"status": "ng", "errormessage": "権限がありません"}) == "権限がありません"

    with pytest.raises(DesknetApiError) as exc_info:
        normalize_list_response({"status": "ng", "errormessage": "W:アクセス権がありません。[W10008]"})
    assert "ポータルの総務権限とは別" in str(exc_info.value)
    assert extract_api_error_message({"status": "ng"}) == "desknet's API エラー"


def test_TC_AIV_INF_008_no_data_response_returns_empty():
    payload = {"status": "ng", "errorno": -110, "errormessage": "W:該当データが存在しません。[W110]"}
    assert normalize_list_response(payload) == []


def test_TC_AIV_INF_007_fetch_list_data_page_uses_post(monkeypatch):
    captured: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"status": "ok", "list": {"item": []}}).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["method"] = request.method
        captured["headers"] = dict(request.header_items())
        captured["body"] = request.data.decode("utf-8")
        return FakeResponse()

    monkeypatch.setattr("apps.asset_inventory.infrastructure.desknet.client.urllib.request.urlopen", fake_urlopen)

    from apps.asset_inventory.infrastructure.desknet.client import fetch_list_data_page

    fetch_list_data_page(
        login_url="https://example.com/cgi-bin/dneo/dneo.cgi",
        access_key="key",
        app_id="401",
        offset=0,
        limit=10,
        fields=("データID",),
        timeout=10,
    )
    assert captured["method"] == "POST"
    assert "fields=" in str(captured["body"])
    assert "%7B%22field_name%22%3A+%22%E3%83%87%E3%83%BC%E3%82%BFID%22%7D" in str(captured["body"])


def test_normalize_list_response_ok():
    payload = {
        "status": "ok",
        "list": {"item": [{"資産番号": {"val": "5262"}}]},
    }
    records = normalize_list_response(payload)
    assert records[0]["資産番号"] == "5262"


def test_TC_AIV_INF_001_paging(monkeypatch):
    calls: list[int] = []

    def fake_page(**kwargs):
        calls.append(kwargs["offset"])
        if kwargs["offset"] == 0:
            return [{"データID": str(i)} for i in range(5000)]
        return [{"データID": "5000"}]

    monkeypatch.setattr(
        "apps.asset_inventory.infrastructure.desknet.client.fetch_list_data_page",
        lambda **kwargs: fake_page(**kwargs),
    )
    records = fetch_all_list_data(
        login_url="https://example.com/cgi-bin/dneo/dneo.cgi",
        access_key="key",
        app_id="401",
        fields=None,
        timeout=10,
    )
    assert len(records) == 5001
    assert calls == [0, 5000]
