from __future__ import annotations

from apps.identity.usecase.usecase_desknet_login import DesknetLoginUsecase
from apps.identity.usecase.usecase_dev_login import DevLoginUsecase
from apps.identity.usecase.usecase_login_page import LoginPageUsecase
from apps.identity.infrastructure.desknet.client import DesknetAuthClient
from apps.identity.infrastructure.dev_login import is_dev_login_available
from apps.identity.infrastructure.persistence.user_repository import DjangoUserRepository


def get_auth_gateway() -> DesknetAuthClient:
    return DesknetAuthClient()


def get_user_repository() -> DjangoUserRepository:
    return DjangoUserRepository()


def login_page_usecase() -> LoginPageUsecase:
    return LoginPageUsecase(is_dev_login_available)


def desknet_login_usecase() -> DesknetLoginUsecase:
    return DesknetLoginUsecase(get_auth_gateway(), get_user_repository())


def dev_login_usecase() -> DevLoginUsecase:
    return DevLoginUsecase(is_dev_login_available)
