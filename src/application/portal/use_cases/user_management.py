from __future__ import annotations

from application.portal.domain.repositories.ports import UserManagementRepository
from application.portal.domain.value_objects.constants import (
    GENERAL_USER_GROUP_NAME,
    ROLE_GROUP_NAMES,
    VALID_SORT_DIRECTIONS,
)
from application.portal.domain.value_objects.database_display import menu_group_choices_in_order
from application.portal.domain.value_objects.user_management_display import (
    USER_MANAGEMENT_SORT_LABELS,
    sort_user_management_entries,
    user_management_column_headers,
)


class UserManagement:
    def __init__(self, repository: UserManagementRepository) -> None:
        self._repository = repository

    def delete_user(self, *, actor: object, target_user: object) -> bool:
        if target_user.id == getattr(actor, "id", None):
            return False
        self._repository.delete_user(target_user)
        return True

    def page_context(self, *, sort_key: str, sort_direction: str) -> dict[str, object]:
        resolved_direction = sort_direction if sort_direction in VALID_SORT_DIRECTIONS else "asc"
        resolved_sort_key = sort_key if sort_key in USER_MANAGEMENT_SORT_LABELS else "username"
        entries = sort_user_management_entries(
            self._repository.list_entries(),
            resolved_sort_key,
            resolved_direction,
        )
        return {
            "user_entries": entries,
            "column_headers": user_management_column_headers(resolved_sort_key, resolved_direction),
            "sort_key": resolved_sort_key,
            "sort_direction": resolved_direction,
            "role_group_names": ROLE_GROUP_NAMES,
            "menu_group_choices": menu_group_choices_in_order(),
        }

    def process(
        self,
        *,
        actor: object,
        user_id: str,
        action: str,
        last_name: str,
        first_name: str,
        email: str,
        role: str,
        menu_group_keys: list[str],
    ) -> bool:
        """処理したら True。対象ユーザー不在なら False。"""
        target_user = self._repository.get_user(user_id)
        if target_user is None:
            return False

        if action == "delete":
            self.delete_user(actor=actor, target_user=target_user)
            return True

        self._repository.update_profile(
            target_user,
            last_name=last_name,
            first_name=first_name,
            email=email,
        )
        self._repository.set_role_and_menu_groups(
            target_user,
            role_name=role or GENERAL_USER_GROUP_NAME,
            menu_group_keys=menu_group_keys,
        )
        return True
