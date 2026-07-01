from __future__ import annotations

from applications.portal.domain.constants import ADMIN_GROUP_NAME
from applications.portal.domain.menu_access import can_access_menu_group, can_access_menu_item
from applications.portal.domain.ports import MenuAccessRepository


class MenuAccessUsecase:
    def __init__(self, menu_access_repository: MenuAccessRepository) -> None:
        self._menu_access = menu_access_repository

    def is_portal_admin(self, user: object) -> bool:
        return bool(
            getattr(user, "is_superuser", False)
            or ADMIN_GROUP_NAME in self._menu_access.user_group_names(user)
        )

    def can_access_menu_group(self, user: object, group_key: str) -> bool:
        return can_access_menu_group(
            is_admin=self.is_portal_admin(user),
            accessible_group_keys=self._menu_access.accessible_menu_group_keys(user),
            group_key=group_key,
        )

    def can_access_menu_item(self, user: object, menu_key: str) -> bool:
        return can_access_menu_item(
            is_admin=self.is_portal_admin(user),
            accessible_group_keys=self._menu_access.accessible_menu_group_keys(user),
            menu_key=menu_key,
        )
