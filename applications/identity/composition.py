from __future__ import annotations

from applications.identity.usecase.usecase_desknet_login import DesknetLoginUsecase
from applications.identity.usecase.usecase_dev_login import DevLoginUsecase
from applications.identity.usecase.usecase_login_page import LoginPageUsecase
from applications.identity.infrastructure.desknet.client import DesknetAuthClient
from applications.identity.infrastructure.dev_login import is_dev_login_available
from applications.identity.infrastructure.persistence.user_repository import DjangoUserRepository


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
