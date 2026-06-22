from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.portal.bootstrap_local_dev import BootstrapLocalDevConfig, bootstrap_local_dev
from apps.portal.favorites import can_access_menu_item, is_portal_admin
from apps.portal.menu import MENU_GROUPS
from apps.portal.models import PortalMenuGroupAccess, UserAccessRequest


@pytest.mark.django_db
def test_bootstrap_local_dev_creates_admin_with_all_menu_groups():
    result = bootstrap_local_dev(
        BootstrapLocalDevConfig(
            username="10001",
            password="dev",
            last_name="開発",
            first_name="管理者",
        )
    )

    assert result.created is True
    user = get_user_model().objects.get(username="10001")
    assert user.check_password("dev")
    assert is_portal_admin(user)
    assert UserAccessRequest.objects.get(user=user).status == UserAccessRequest.Status.APPROVED
    assert PortalMenuGroupAccess.objects.filter(user=user).count() == len(MENU_GROUPS)
    assert can_access_menu_item(user, "inventory-order-alert")
    assert can_access_menu_item(user, "five-year-nine")


@pytest.mark.django_db
def test_bootstrap_local_dev_is_idempotent():
    config = BootstrapLocalDevConfig(
        username="10001",
        password="dev",
        last_name="開発",
        first_name="管理者",
    )
    bootstrap_local_dev(config)
    result = bootstrap_local_dev(config)

    assert result.created is False
    assert get_user_model().objects.filter(username="10001").count() == 1
    assert PortalMenuGroupAccess.objects.filter(user=get_user_model().objects.get(username="10001")).count() == len(
        MENU_GROUPS
    )


@pytest.mark.django_db
def test_bootstrap_local_dev_command_skips_when_auth_dev_mode_false(settings):
    from django.core.management import call_command
    from io import StringIO

    settings.AUTH_DEV_MODE = False
    out = StringIO()
    call_command("bootstrap_local_dev", stdout=out)
    assert "スキップ" in out.getvalue()
    assert not get_user_model().objects.exists()


@pytest.mark.django_db
def test_bootstrap_local_dev_command_runs_when_auth_dev_mode_true(settings):
    from django.core.management import call_command
    from io import StringIO

    settings.AUTH_DEV_MODE = True
    settings.DEBUG = True
    settings.AUTH_DEV_USERNAME = "10001"
    settings.AUTH_DEV_PASSWORD = "dev"
    out = StringIO()
    call_command("bootstrap_local_dev", stdout=out)
    assert "10001" in out.getvalue()
    user = get_user_model().objects.get(username="10001")
    assert user.groups.filter(name="管理者").exists()
