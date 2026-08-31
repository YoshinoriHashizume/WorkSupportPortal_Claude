from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from application.identity.infrastructure.dev_login import is_dev_login_available
from application.portal.interfaces.wiring import bootstrap_local_dev_usecase
from application.portal.domain.value_objects.bootstrap import BootstrapLocalDevConfig
from application.portal.interfaces.favorites import ADMIN_GROUP_NAME


@pytest.mark.django_db
def test_is_dev_login_available_false_when_auth_dev_mode_disabled(settings):
    settings.AUTH_DEV_MODE = False
    assert is_dev_login_available() is False


@pytest.mark.django_db
def test_is_dev_login_available_true_when_only_bootstrap_admin_exists(settings):
    settings.AUTH_DEV_MODE = True
    settings.AUTH_DEV_USERNAME = "10001"
    bootstrap_local_dev_usecase().execute(
        BootstrapLocalDevConfig(
            username="10001",
            password="dev",
            last_name="開発",
            first_name="管理者",
        )
    )

    assert is_dev_login_available() is True


@pytest.mark.django_db
def test_is_dev_login_available_false_when_non_bootstrap_admin_exists(settings):
    settings.AUTH_DEV_MODE = True
    settings.AUTH_DEV_USERNAME = "10001"
    bootstrap_local_dev_usecase().execute(
        BootstrapLocalDevConfig(
            username="10001",
            password="dev",
            last_name="開発",
            first_name="管理者",
        )
    )

    User = get_user_model()
    admin_group = Group.objects.get(name=ADMIN_GROUP_NAME)
    other_admin = User.objects.create_user(username="20001", password="unused")
    other_admin.groups.add(admin_group)

    assert is_dev_login_available() is False
