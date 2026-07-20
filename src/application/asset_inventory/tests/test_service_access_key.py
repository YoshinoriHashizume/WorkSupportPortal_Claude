from __future__ import annotations

import pytest
from django.test import override_settings

from application.asset_inventory.domain.value_objects.errors import format_desknet_user_error_message
from application.asset_inventory.infrastructure.desknet.service_access_key import (
    clear_service_access_key_cache,
    resolve_asset_inventory_access_key,
)


def test_format_desknet_user_error_message_for_w10008_without_service_account():
    message = format_desknet_user_error_message(
        "W:アクセス権がありません。[W10008]",
        has_service_account=False,
    )
    assert "ポータルの総務権限とは別" in message
    assert "サービス連携アカウント" in message


def test_format_desknet_user_error_message_for_w10008_with_service_account():
    message = format_desknet_user_error_message(
        "W:アクセス権がありません。[W10008]",
        has_service_account=True,
    )
    assert "サービス連携アカウント" in message
    assert "DESKNETS_ASSET_INVENTORY_LOGIN_ID" in message


@override_settings(DESKNETS_ASSET_INVENTORY_LOGIN_ID="", DESKNETS_ASSET_INVENTORY_PASSWORD="")
def test_resolve_asset_inventory_access_key_uses_session_key_when_service_account_not_configured():
    assert resolve_asset_inventory_access_key("session-key") == "session-key"


@override_settings(
    DESKNETS_ASSET_INVENTORY_LOGIN_ID="service-user",
    DESKNETS_ASSET_INVENTORY_PASSWORD="secret",
    DESKNETS_LOGIN_URL="https://example.test/cgi-bin/dneo/dneo.cgi",
    DESKNETS_TIMEOUT_SECONDS=10,
)
def test_resolve_asset_inventory_access_key_uses_service_account(monkeypatch):
    clear_service_access_key_cache()
    monkeypatch.setattr(
        "application.asset_inventory.infrastructure.desknet.service_access_key.authenticate_desknet_user",
        lambda login_url, employee_id, password, timeout: type(
            "Info",
            (),
            {"access_key": "service-access-key"},
        )(),
    )
    assert resolve_asset_inventory_access_key("session-key") == "service-access-key"
    clear_service_access_key_cache()
