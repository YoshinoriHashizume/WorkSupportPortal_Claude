from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class LoginPageContext:
    auth_provider: str
    show_dev_login: bool
    next_url: str


class LoginPageUsecase:
    def __init__(self, dev_login_available: Callable[[], bool]) -> None:
        self._dev_login_available = dev_login_available

    def execute(self, auth_provider: str, next_url: str) -> LoginPageContext:
        return LoginPageContext(
            auth_provider=auth_provider,
            show_dev_login=self._dev_login_available(),
            next_url=next_url,
        )
