from __future__ import annotations

import urllib.parse

from application.asset_inventory.domain.value_objects.errors import DesknetApiError


def is_allowed_attachment_url(source_url: str, desknet_login_url: str) -> bool:
    source = urllib.parse.urlparse(source_url.strip())
    if source.scheme not in {"http", "https"} or not source.netloc:
        return False
    allowed_host = urllib.parse.urlparse(desknet_login_url).netloc
    if source.netloc != allowed_host:
        return False
    query = urllib.parse.parse_qs(source.query)
    action = (query.get("action") or [""])[0]
    return action == "download_data_file"


# 後方互換: テストや呼び出し側が DesknetApiError を同モジュールから参照できるようにする
__all__ = ["DesknetApiError", "is_allowed_attachment_url"]
