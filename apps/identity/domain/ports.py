from __future__ import annotations

from typing import Protocol

from .user_info import DesknetUserInfo


class DesknetAuthGateway(Protocol):
    def authenticate(self, login_url: str, employee_id: str, password: str, timeout: float) -> DesknetUserInfo: ...


class UserRepository(Protocol):
    def upsert_from_desknet(self, user_info: DesknetUserInfo) -> object: ...
