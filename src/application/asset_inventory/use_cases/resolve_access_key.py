from __future__ import annotations

from application.asset_inventory.domain.repositories.ports import ResolveAccessKeyFn
from application.asset_inventory.domain.value_objects.errors import DesknetServiceAuthError

SERVICE_AUTH_ERROR_MESSAGE = (
    "desknet's サービス連携アカウントでログインできません。"
    "管理者に DESKNETS_ASSET_INVENTORY_LOGIN_ID の設定をご確認ください。"
)
MISSING_KEY_ERROR_MESSAGE = "desknet's のアクセスキーがありません。再ログインしてください。"


class ResolveAccessKey:
    def __init__(self, resolve_fn: ResolveAccessKeyFn) -> None:
        self._resolve = resolve_fn

    def execute(self, session_access_key: str) -> tuple[str, str | None]:
        try:
            access_key = self._resolve(str(session_access_key or "").strip())
        except DesknetServiceAuthError:
            return "", SERVICE_AUTH_ERROR_MESSAGE
        if not access_key:
            return "", MISSING_KEY_ERROR_MESSAGE
        return access_key, None
