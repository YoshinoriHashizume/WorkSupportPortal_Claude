from __future__ import annotations

from collections.abc import Callable

from django.contrib.auth import authenticate


class DevLoginUsecase:
    def __init__(self, dev_login_available: Callable[[], bool]) -> None:
        self._dev_login_available = dev_login_available

    def execute(self, employee_id: str, password: str) -> object | None:
        if not self._dev_login_available():
            raise PermissionError("dev login unavailable")
        if not employee_id or not password:
            raise ValueError("社員番号とパスワードを入力してください。")
        return authenticate(username=employee_id, password=password)
