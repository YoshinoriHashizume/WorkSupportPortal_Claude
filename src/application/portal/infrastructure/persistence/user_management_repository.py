from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from application.portal.domain.value_objects.constants import (
    ADMIN_GROUP_NAME,
    GENERAL_USER_GROUP_NAME,
    ROLE_GROUP_NAMES,
)
from application.portal.domain.value_objects.database_display import assignable_menu_groups
from application.portal.domain.value_objects.menu import MENU_GROUPS
from application.portal.domain.value_objects.menu_access import normalize_menu_group_key
from application.portal.models import PortalMenuGroupAccess, UserAccessRequest


class DjangoUserManagementRepository:
    def list_entries(self) -> list[dict[str, object]]:
        User = get_user_model()
        access_requests = {request.user_id: request for request in UserAccessRequest.objects.select_related("reviewed_by")}
        menu_group_titles = {group.key: group.title for group in MENU_GROUPS}
        entries = []
        users = User.objects.prefetch_related("groups", "portal_menu_group_accesses").order_by("username")
        for user in users:
            role_names = [name for name in user.groups.values_list("name", flat=True) if name in ROLE_GROUP_NAMES]
            menu_groups = [
                menu_group_titles.get(access.group_key, access.group_key)
                for access in user.portal_menu_group_accesses.all()
            ]
            role = "管理者" if "管理者" in role_names else "一般ユーザー"
            selected_menu_group_keys = list(
                dict.fromkeys(
                    normalize_menu_group_key(key)
                    for key in user.portal_menu_group_accesses.values_list("group_key", flat=True)
                )
            )
            entries.append(
                {
                    "user": user,
                    "full_name": f"{user.last_name} {user.first_name}".strip() or user.username,
                    "role": "、".join(role_names) or "-",
                    "editable_role": role,
                    "menu_groups": "、".join(menu_groups) or "-",
                    "selected_menu_group_keys": selected_menu_group_keys,
                    "access_request": access_requests.get(user.id),
                    "status_label": access_requests[user.id].get_status_display() if user.id in access_requests else "-",
                }
            )
        return entries

    def get_user(self, user_id: str) -> object | None:
        User = get_user_model()
        try:
            return User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return None

    def delete_user(self, target_user: object) -> None:
        target_user.delete()

    def update_profile(
        self,
        target_user: object,
        *,
        last_name: str,
        first_name: str,
        email: str,
    ) -> None:
        target_user.last_name = last_name
        target_user.first_name = first_name
        target_user.email = email
        target_user.save(update_fields=["last_name", "first_name", "email"])

    def set_role_and_menu_groups(
        self,
        target_user: object,
        *,
        role_name: str,
        menu_group_keys: list[str],
    ) -> None:
        resolved_role = ADMIN_GROUP_NAME if role_name == ADMIN_GROUP_NAME else GENERAL_USER_GROUP_NAME
        role_group, _ = Group.objects.get_or_create(name=resolved_role)
        target_user.groups.set([role_group])
        valid_menu_group_keys = {group.key for group in assignable_menu_groups()}
        PortalMenuGroupAccess.objects.filter(user=target_user).delete()
        if resolved_role != ADMIN_GROUP_NAME:
            PortalMenuGroupAccess.objects.bulk_create(
                [
                    PortalMenuGroupAccess(user=target_user, group_key=group_key)
                    for group_key in menu_group_keys
                    if group_key in valid_menu_group_keys
                ],
                ignore_conflicts=True,
            )
