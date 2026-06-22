from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

from apps.portal.menu import MENU_GROUPS
from apps.portal.models import PortalMenuGroupAccess, UserAccessRequest

ADMIN_GROUP_NAME = "管理者"


@dataclass(frozen=True)
class BootstrapLocalDevConfig:
    username: str
    password: str
    last_name: str
    first_name: str


@dataclass(frozen=True)
class BootstrapLocalDevResult:
    created: bool
    username: str
    menu_groups_granted: int


def bootstrap_local_dev(config: BootstrapLocalDevConfig) -> BootstrapLocalDevResult:
    User = get_user_model()
    admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)

    user, created = User.objects.get_or_create(username=config.username)
    user.last_name = config.last_name
    user.first_name = config.first_name
    user.is_active = True
    user.set_password(config.password)
    user.save()
    user.groups.add(admin_group)

    access_request, _ = UserAccessRequest.objects.get_or_create(user=user)
    access_request.status = UserAccessRequest.Status.APPROVED
    access_request.reviewed_at = timezone.now()
    access_request.save(update_fields=["status", "reviewed_at"])

    granted = 0
    for group in MENU_GROUPS:
        _, group_created = PortalMenuGroupAccess.objects.get_or_create(user=user, group_key=group.key)
        if group_created:
            granted += 1

    try:
        from apps.inventory_order_alert.models import InventoryOrderAlertSettings

        InventoryOrderAlertSettings.objects.get_or_create(pk=1)
    except Exception:
        pass

    return BootstrapLocalDevResult(created=created, username=config.username, menu_groups_granted=granted)
