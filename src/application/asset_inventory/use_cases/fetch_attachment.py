from __future__ import annotations

from collections.abc import Callable

from application.asset_inventory.domain.value_objects.attachment_proxy import is_allowed_attachment_url
from application.asset_inventory.domain.value_objects.errors import DesknetApiError

FetchAttachmentFn = Callable[..., tuple[bytes, str]]


class FetchAttachment:
    """添付 URL 許可判定と desknet's 取得をオーケストレーションする。"""

    def __init__(self, fetch_fn: FetchAttachmentFn, *, desknet_login_url: str) -> None:
        self._fetch = fetch_fn
        self._desknet_login_url = desknet_login_url

    def execute(
        self,
        *,
        source_url: str,
        access_key: str,
        timeout: float,
    ) -> tuple[bytes, str] | None:
        """許可外 URL のときは None。取得失敗は DesknetApiError。"""
        if not is_allowed_attachment_url(source_url, self._desknet_login_url):
            return None
        return self._fetch(source_url=source_url, access_key=access_key, timeout=timeout)


__all__ = ["DesknetApiError", "FetchAttachment", "FetchAttachmentFn"]
