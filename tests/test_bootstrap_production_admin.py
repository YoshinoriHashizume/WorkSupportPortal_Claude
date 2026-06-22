from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.portal.bootstrap_production_admin import BootstrapProductionAdminConfig, bootstrap_production_admin
from apps.portal.favorites import can_access_menu_item, is_portal_admin
from apps.portal.menu import MENU_GROUPS
from apps.portal.models import PortalMenuGroupAccess, UserAccessRequest


@pytest.mark.django_db
def test_bootstrap_production_admin_creates_desknet_admin():
    result = bootstrap_production_admin(
        BootstrapProductionAdminConfig(
            username="10001",
            last_name="橋爪",
            first_name="良典",
        )
    )

    assert result.created is True
    user = get_user_model().objects.get(username="10001")
    assert not user.has_usable_password()
    assert is_portal_admin(user)
    assert UserAccessRequest.objects.get(user=user).status == UserAccessRequest.Status.APPROVED
    assert PortalMenuGroupAccess.objects.filter(user=user).count() == len(MENU_GROUPS)
    assert can_access_menu_item(user, "inventory-order-alert")


@pytest.mark.django_db
def test_bootstrap_production_admin_command(settings):
    from io import StringIO

    from django.core.management import call_command

    settings.AUTH_DEV_MODE = False
    out = StringIO()
    call_command(
        "bootstrap_production_admin",
        username="10002",
        last_name="山田",
        first_name="花子",
        stdout=out,
    )
    assert "10002" in out.getvalue()
    assert get_user_model().objects.filter(username="10002").exists()
