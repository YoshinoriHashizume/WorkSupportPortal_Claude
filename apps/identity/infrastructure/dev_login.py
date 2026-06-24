from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import Group

from apps.portal.domain.constants import ADMIN_GROUP_NAME


def is_dev_login_available() -> bool:
    if not settings.AUTH_DEV_MODE:
        return False

    admin_group = Group.objects.filter(name=ADMIN_GROUP_NAME).first()
    if admin_group is None:
        return True

    dev_username = settings.AUTH_DEV_USERNAME
    return not admin_group.user_set.exclude(username=dev_username).exists()
