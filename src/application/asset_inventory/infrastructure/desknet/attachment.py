from __future__ import annotations

import urllib.error
import urllib.request

from application.asset_inventory.domain.value_objects.errors import DesknetApiError


def fetch_attachment_content(
    *,
    source_url: str,
    access_key: str,
    timeout: float,
) -> tuple[bytes, str]:
    if not access_key:
        raise DesknetApiError("desknet's のアクセスキーがありません。")

    request = urllib.request.Request(
        source_url,
        method="GET",
        headers={"X-Desknets-Auth": access_key},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type") or "application/octet-stream"
            return response.read(), content_type
    except urllib.error.HTTPError as exc:
        raise DesknetApiError(f"desknet's 添付ファイル HTTP エラー: {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise DesknetApiError(f"desknet's 添付ファイル接続エラー: {exc.reason}") from exc
