from __future__ import annotations

from collections.abc import Iterable

from application.portal.use_cases.menu_access import MenuAccess
from application.portal.domain.value_objects.menu import MENU_BY_KEY, MENU_GROUP_BY_KEY, MENU_GROUPS, MENU_ITEMS
from application.portal.domain.value_objects.menu_access import menu_item_payload
from application.portal.domain.repositories.ports import FavoriteRepository


class Favorites:
    def __init__(
        self,
        favorite_repository: FavoriteRepository,
        menu_access: MenuAccess,
    ) -> None:
        self._favorites = favorite_repository
        self._access = menu_access

    def favorite_keys_for_user(self, user: object) -> list[str]:
        return self._favorites.favorite_keys_for_user(user)

    def is_menu_favorited(self, user: object, menu_key: str) -> bool:
        return menu_key in set(self.favorite_keys_for_user(user))

    def favorite_items_for_user(self, user: object) -> list[dict[str, object]]:
        items = []
        for key in self.favorite_keys_for_user(user):
            item = MENU_BY_KEY.get(key)
            if item is None:
                continue
            if not self._access.can_access_menu_item(user, item.key):
                continue
            group = MENU_GROUP_BY_KEY.get(item.group_key)
            items.append(
                {
                    "key": item.key,
                    "title": item.title,
                    "href": item.href,
                    "group_title": group.title if group else "",
                }
            )
        return items

    def next_sort_order(self, user: object) -> int:
        return self._favorites.next_sort_order(user)

    def add_favorite(self, user: object, menu_key: str) -> None:
        self._favorites.get_or_create_favorite(user, menu_key, self.next_sort_order(user))

    def remove_favorite(self, user: object, menu_key: str) -> None:
        self._favorites.delete_favorite(user, menu_key)

    def reorder_favorites(self, user: object, menu_keys: Iterable[str]) -> None:
        allowed_keys = [key for key in menu_keys if self._access.can_access_menu_item(user, key)]
        self._favorites.reorder_favorites(user, allowed_keys)

    def menu_items_with_favorite_state(
        self,
        user: object,
        current_path: str = "",
        current_type: str = "",
    ) -> list[dict[str, object]]:
        favorite_keys = set(self.favorite_keys_for_user(user))
        return [
            menu_item_payload(item, favorite_keys, current_path, current_type)
            for item in MENU_ITEMS
            if item.href and self._access.can_access_menu_item(user, item.key)
        ]

    def menu_groups_with_items(
        self,
        user: object,
        current_path: str = "",
        current_type: str = "",
    ) -> list[dict[str, object]]:
        favorite_keys = set(self.favorite_keys_for_user(user))
        children_by_parent: dict[str, list] = {}
        for item in MENU_ITEMS:
            if item.parent_key:
                children_by_parent.setdefault(item.parent_key, []).append(item)

        items_by_group = {group.key: [] for group in MENU_GROUPS}
        for item in MENU_ITEMS:
            if item.parent_key:
                continue
            if not self._access.can_access_menu_item(user, item.key):
                continue
            if item.href:
                items_by_group.setdefault(item.group_key, []).append(
                    menu_item_payload(item, favorite_keys, current_path, current_type)
                )
                continue

            children = [
                menu_item_payload(child, favorite_keys, current_path, current_type)
                for child in children_by_parent.get(item.key, [])
                if self._access.can_access_menu_item(user, child.key)
            ]
            if not children:
                continue
            is_branch_expanded = any(child["is_active"] for child in children)
            items_by_group.setdefault(item.group_key, []).append(
                {
                    **menu_item_payload(item, favorite_keys, current_path, current_type),
                    "children": children,
                    "is_expanded": is_branch_expanded,
                }
            )

        groups = []
        for group in MENU_GROUPS:
            if not self._access.can_access_menu_group(user, group.key):
                continue
            items = items_by_group.get(group.key, [])
            is_group_expanded = any(item.get("is_active") for item in items) or any(
                child.get("is_active")
                for item in items
                for child in item.get("children", [])
            )
            groups.append(
                {
                    "key": group.key,
                    "title": group.title,
                    "items": items,
                    "is_expanded": is_group_expanded,
                }
            )
        return groups
