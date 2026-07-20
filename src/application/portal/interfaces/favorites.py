from __future__ import annotations

from application.portal.interfaces.wiring import favorites_usecase, menu_access_usecase
from application.portal.domain.value_objects.menu_access import (
    is_menu_path_active,
    menu_title,
    receipt_comparison_menu_key,
    receipt_comparison_type_from_path,
)
from application.portal.domain.value_objects.constants import ADMIN_GROUP_NAME, MANAGEMENT_GROUP_KEY, RECEIPT_COMPARISON_MENU_KEYS


def user_group_names(user: object) -> set[str]:
    from application.portal.interfaces.wiring import get_menu_access_repository

    return get_menu_access_repository().user_group_names(user)


def accessible_menu_group_keys(user: object) -> set[str]:
    from application.portal.interfaces.wiring import get_menu_access_repository

    return get_menu_access_repository().accessible_menu_group_keys(user)


def is_portal_admin(user: object) -> bool:
    return menu_access_usecase().is_portal_admin(user)


def can_access_menu_group(user: object, group_key: str) -> bool:
    return menu_access_usecase().can_access_menu_group(user, group_key)


def can_access_menu_item(user: object, menu_key: str) -> bool:
    return menu_access_usecase().can_access_menu_item(user, menu_key)


def is_menu_favorited(user: object, menu_key: str) -> bool:
    return favorites_usecase().is_menu_favorited(user, menu_key)


def page_favorite_toggle_context(user: object, menu_key: str) -> dict[str, object]:
    from application.portal.domain.value_objects.menu import MENU_BY_KEY

    item = MENU_BY_KEY[menu_key]
    return {
        "menu_key": menu_key,
        "menu_title": item.title,
        "is_favorite": is_menu_favorited(user, menu_key),
    }


def favorite_keys_for_user(user: object) -> list[str]:
    return favorites_usecase().favorite_keys_for_user(user)


def favorite_items_for_user(user: object) -> list[dict[str, object]]:
    return favorites_usecase().favorite_items_for_user(user)


def next_sort_order(user: object) -> int:
    return favorites_usecase().next_sort_order(user)


def reorder_favorites(user: object, menu_keys) -> None:
    return favorites_usecase().reorder_favorites(user, menu_keys)


def menu_items_with_favorite_state(user: object, current_path: str = "", current_type: str = "") -> list[dict[str, object]]:
    return favorites_usecase().menu_items_with_favorite_state(user, current_path, current_type)


def menu_groups_with_items(user: object, current_path: str = "", current_type: str = "") -> list[dict[str, object]]:
    return favorites_usecase().menu_groups_with_items(user, current_path, current_type)


__all__ = [
    "ADMIN_GROUP_NAME",
    "MANAGEMENT_GROUP_KEY",
    "RECEIPT_COMPARISON_MENU_KEYS",
    "accessible_menu_group_keys",
    "can_access_menu_group",
    "can_access_menu_item",
    "favorite_items_for_user",
    "favorite_keys_for_user",
    "is_menu_favorited",
    "page_favorite_toggle_context",
    "is_menu_path_active",
    "is_portal_admin",
    "menu_groups_with_items",
    "menu_items_with_favorite_state",
    "menu_title",
    "next_sort_order",
    "receipt_comparison_menu_key",
    "receipt_comparison_type_from_path",
    "reorder_favorites",
    "user_group_names",
]
