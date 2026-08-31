from __future__ import annotations

from collections.abc import Callable


class DevLogin:
    def __init__(
        self,
        dev_login_available: Callable[[], bool],
        authenticator: Callable[..., object | None],
    ) -> None:
        self._dev_login_available = dev_login_available
        self._authenticator = authenticator

    def execute(self, employee_id: str, password: str) -> object | None:
        if not self._dev_login_available():
            raise PermissionError("dev login unavailable")
        if not employee_id or not password:
            raise ValueError("社員番号とパスワードを入力してください。")
        return self._authenticator(username=employee_id, password=password)
