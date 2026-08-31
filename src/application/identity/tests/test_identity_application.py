from __future__ import annotations

import pytest

from application.identity.use_cases.desknet_login import DesknetLogin
from application.identity.use_cases.dev_login import DevLogin
from application.identity.use_cases.login_page import LoginPage
from application.identity.domain.value_objects.errors import DesknetAuthError
from application.identity.domain.value_objects.user_info import DesknetUserInfo, split_desknet_name


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
    enabled = LoginPage(lambda: True).execute("desknet", "/next")
    disabled = LoginPage(lambda: False).execute("desknet", "/next")
    assert enabled.show_dev_login is True
    assert disabled.show_dev_login is False


def test_desknet_login_usecase_requires_credentials():
    use_case = DesknetLogin(FakeAuthGateway(), FakeUserRepository())
    with pytest.raises(ValueError, match="社員番号"):
        use_case.execute("http://example", "", "pw", 10.0)


def test_desknet_login_usecase_maps_auth_error():
    use_case = DesknetLogin(
        FakeAuthGateway(error=DesknetAuthError("bad")),
        FakeUserRepository(),
    )
    with pytest.raises(DesknetAuthError):
        use_case.execute("http://example", "001", "pw", 10.0)


def test_dev_login_usecase_checks_availability():
    use_case = DevLogin(lambda: False, lambda **_: None)
    with pytest.raises(PermissionError):
        use_case.execute("001", "pw")


def test_dev_login_usecase_uses_injected_authenticator():
    calls: list[dict[str, str]] = []

    def authenticator(**kwargs: str) -> object:
        calls.append(kwargs)
        return object()

    use_case = DevLogin(lambda: True, authenticator)
    user = use_case.execute("001", "secret")
    assert user is not None
    assert calls == [{"username": "001", "password": "secret"}]
