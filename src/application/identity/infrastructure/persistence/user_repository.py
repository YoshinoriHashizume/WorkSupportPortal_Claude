from __future__ import annotations

from django.contrib.auth import get_user_model

from application.identity.domain.value_objects.user_info import DesknetUserInfo, split_desknet_name
from application.portal.models import UserAccessRequest


class DjangoUserRepository:
    def upsert_from_desknet(self, user_info: DesknetUserInfo) -> object:
        User = get_user_model()
        user, created = User.objects.get_or_create(username=user_info.employee_id)
        last_name, first_name = split_desknet_name(user_info.name)
        user.last_name = last_name
        user.first_name = first_name
        user.email = ""
        user.is_active = True
        user.set_unusable_password()
        user.save()
        if created:
            UserAccessRequest.objects.get_or_create(user=user)
        return user
