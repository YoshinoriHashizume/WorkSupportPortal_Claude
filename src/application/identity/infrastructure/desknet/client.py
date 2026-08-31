from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

import requests

from application.identity.domain.value_objects.errors import DesknetAuthError
from application.identity.domain.value_objects.user_info import DesknetUserInfo


def desknet_login_api_url(login_url: str) -> str:
    parsed = urlsplit(login_url)
    path = parsed.path
    if path.endswith("/dneo.cgi"):
        path = f"{path[:-len('/dneo.cgi')]}/dneor.cgi"
    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))


def authenticate_desknet_user(login_url: str, employee_id: str, password: str, timeout: float = 10) -> DesknetUserInfo:
    try:
        response = requests.post(
            desknet_login_api_url(login_url),
            data={"action": "login", "login_id": employee_id, "password": password},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise DesknetAuthError("desknet's に接続できませんでした。時間をおいて再度お試しください。") from exc
    except ValueError as exc:
        raise DesknetAuthError("desknet's の応答を解析できませんでした。") from exc

    if str(payload.get("status") or "").lower() != "ok":
        raise DesknetAuthError("社員番号またはパスワードが正しくありません。")

    access_key = str(payload.get("access_key") or "").strip()
    if not access_key:
        raise DesknetAuthError("desknet's の認証応答にアクセスキーが含まれていません。")

    return DesknetUserInfo(
        employee_id=employee_id,
        user_id=str(payload.get("user_id") or "").strip(),
        name=str(payload.get("name") or "").strip(),
        default_group_id=str(payload.get("default_group_id") or "").strip(),
        access_key=access_key,
    )


class DesknetAuthClient:
    def authenticate(self, login_url: str, employee_id: str, password: str, timeout: float) -> DesknetUserInfo:
        return authenticate_desknet_user(login_url, employee_id, password, timeout)
