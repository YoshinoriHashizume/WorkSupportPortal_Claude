from __future__ import annotations

from application.identity.use_cases.desknet_login import DesknetLogin
from application.identity.use_cases.dev_login import DevLogin
from application.identity.use_cases.login_page import LoginPage
from application.identity.infrastructure.desknet.client import DesknetAuthClient
from application.identity.infrastructure.dev_login import is_dev_login_available
from application.identity.infrastructure.persistence.user_repository import DjangoUserRepository


def get_auth_gateway() -> DesknetAuthClient:
    return DesknetAuthClient()


def get_user_repository() -> DjangoUserRepository:
    return DjangoUserRepository()


def login_page_usecase() -> LoginPage:
    return LoginPage(is_dev_login_available)


def desknet_login_usecase() -> DesknetLogin:
    return DesknetLogin(get_auth_gateway(), get_user_repository())


def dev_login_usecase() -> DevLogin:
    from django.contrib.auth import authenticate

    return DevLogin(is_dev_login_available, authenticate)
