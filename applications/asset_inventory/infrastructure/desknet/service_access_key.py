from __future__ import annotations

import threading
import time

from django.conf import settings

from applications.identity.infrastructure.desknet.client import authenticate_desknet_user

_cache_lock = threading.Lock()
_cached_access_key = ""
_cached_at = 0.0
_CACHE_TTL_SECONDS = 48 * 3600


def _service_account_configured() -> bool:
    login_id = str(getattr(settings, "DESKNETS_ASSET_INVENTORY_LOGIN_ID", "") or "").strip()
    password = str(getattr(settings, "DESKNETS_ASSET_INVENTORY_PASSWORD", "") or "")
    return bool(login_id and password)


def _fetch_service_access_key() -> str:
    login_id = str(settings.DESKNETS_ASSET_INVENTORY_LOGIN_ID).strip()
    password = str(settings.DESKNETS_ASSET_INVENTORY_PASSWORD)
    user_info = authenticate_desknet_user(
        settings.DESKNETS_LOGIN_URL,
        login_id,
        password,
        float(settings.DESKNETS_TIMEOUT_SECONDS),
    )
    return user_info.access_key


def get_service_access_key(*, force_refresh: bool = False) -> str:
    if not _service_account_configured():
        return ""

    global _cached_access_key, _cached_at
    with _cache_lock:
        now = time.monotonic()
        if not force_refresh and _cached_access_key and (now - _cached_at) < _CACHE_TTL_SECONDS:
            return _cached_access_key
        _cached_access_key = _fetch_service_access_key()
        _cached_at = now
        return _cached_access_key


def resolve_asset_inventory_access_key(session_access_key: str) -> str:
    service_key = get_service_access_key()
    if service_key:
        return service_key
    return session_access_key.strip()


def clear_service_access_key_cache() -> None:
    global _cached_access_key, _cached_at
    with _cache_lock:
        _cached_access_key = ""
        _cached_at = 0.0
