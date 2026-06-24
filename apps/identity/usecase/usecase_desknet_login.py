from __future__ import annotations

from dataclasses import dataclass

from apps.identity.domain.errors import DesknetAuthError
from apps.identity.domain.ports import DesknetAuthGateway, UserRepository
from apps.identity.domain.user_info import DesknetUserInfo


@dataclass(frozen=True)
class DesknetLoginResult:
    user: object
    user_info: DesknetUserInfo
    requires_access_approval: bool


class DesknetLoginUsecase:
    def __init__(self, auth_gateway: DesknetAuthGateway, user_repository: UserRepository) -> None:
        self._auth_gateway = auth_gateway
        self._user_repository = user_repository

    def execute(
        self,
        login_url: str,
        employee_id: str,
        password: str,
        timeout: float,
    ) -> DesknetLoginResult:
        if not employee_id or not password:
            raise ValueError("社員番号とパスワードを入力してください。")
        try:
            user_info = self._auth_gateway.authenticate(login_url, employee_id, password, timeout)
        except DesknetAuthError:
            raise
        user = self._user_repository.upsert_from_desknet(user_info)
        access_request = getattr(user, "access_request", None)
        requires_access_approval = bool(
            access_request and getattr(access_request, "status", "") != "approved"
        )
        return DesknetLoginResult(user=user, user_info=user_info, requires_access_approval=requires_access_approval)
