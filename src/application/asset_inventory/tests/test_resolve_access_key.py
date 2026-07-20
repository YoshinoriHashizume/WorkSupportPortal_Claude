from __future__ import annotations

from application.asset_inventory.domain.value_objects.errors import DesknetServiceAuthError
from application.asset_inventory.use_cases.resolve_access_key import (
    MISSING_KEY_ERROR_MESSAGE,
    SERVICE_AUTH_ERROR_MESSAGE,
    ResolveAccessKey,
)


def test_resolve_access_key_returns_resolved_key():
    usecase = ResolveAccessKey(lambda _session: "service-key")
    assert usecase.execute("session-key") == ("service-key", None)


def test_resolve_access_key_returns_missing_message_when_empty():
    usecase = ResolveAccessKey(lambda _session: "")
    assert usecase.execute("") == ("", MISSING_KEY_ERROR_MESSAGE)


def test_resolve_access_key_maps_service_auth_error():
    def raise_auth(_session: str) -> str:
        raise DesknetServiceAuthError("auth failed")

    usecase = ResolveAccessKey(raise_auth)
    assert usecase.execute("session-key") == ("", SERVICE_AUTH_ERROR_MESSAGE)
