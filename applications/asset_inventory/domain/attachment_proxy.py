from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request

from applications.asset_inventory.domain.errors import DesknetApiError


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
