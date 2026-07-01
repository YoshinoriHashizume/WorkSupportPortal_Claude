from __future__ import annotations

import pytest

from applications.identity.usecase.usecase_desknet_login import DesknetLoginUsecase
from applications.identity.usecase.usecase_dev_login import DevLoginUsecase
from applications.identity.usecase.usecase_login_page import LoginPageUsecase
from applications.identity.domain.errors import DesknetAuthError
from applications.identity.domain.user_info import DesknetUserInfo, split_desknet_name


class FakeAuthGateway:
    def __init__(self, user_info: DesknetUserInfo | None = None, error: Exception | None = None) -> None:
        self._user_info = user_info
        self._error = error

    def authenticate(self, login_url: str, employee_id: str, password: str, timeout: float) -> DesknetUserInfo:
        if self._error:
            raise self._error
        assert self._user_info is not None
        return self._user_info


class FakeUserRepository:
    def __init__(self, user: object | None = None) -> None:
        self._user = user or object()

    def upsert_from_desknet(self, user_info: DesknetUserInfo) -> object:
        return self._user


def test_split_desknet_name_splits_full_width_space():
    last, first = split_desknet_name("山田\u3000太郎")
    assert last == "山田"
    assert first == "太郎"


def test_login_page_usecase_reflects_dev_login_flag():
    enabled = LoginPageUsecase(lambda: True).execute("desknet", "/next")
    disabled = LoginPageUsecase(lambda: False).execute("desknet", "/next")
    assert enabled.show_dev_login is True
    assert disabled.show_dev_login is False


def test_desknet_login_usecase_requires_credentials():
    use_case = DesknetLoginUsecase(FakeAuthGateway(), FakeUserRepository())
    with pytest.raises(ValueError, match="社員番号"):
        use_case.execute("http://example", "", "pw", 10.0)


def test_desknet_login_usecase_maps_auth_error():
    use_case = DesknetLoginUsecase(
        FakeAuthGateway(error=DesknetAuthError("bad")),
        FakeUserRepository(),
    )
    with pytest.raises(DesknetAuthError):
        use_case.execute("http://example", "001", "pw", 10.0)


def test_dev_login_usecase_checks_availability():
    use_case = DevLoginUsecase(lambda: False)
    with pytest.raises(PermissionError):
        use_case.execute("001", "pw")
