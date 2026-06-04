from __future__ import annotations

from collections.abc import Iterable

from .menu import MENU_BY_KEY, MENU_GROUPS, MENU_GROUP_BY_KEY, MENU_ITEMS
from .models import PortalMenuGroupAccess, UserFavoriteMenu


ADMIN_GROUP_NAME = "管理者"
MANAGEMENT_GROUP_KEY = "management"


def user_group_names(user: object) -> set[str]:
    if not getattr(user, "is_authenticated", False):
        return set()
    return set(user.groups.values_list("name", flat=True))


def accessible_menu_group_keys(user: object) -> set[str]:
    if not getattr(user, "is_authenticated", False):
        return set()
    return set(PortalMenuGroupAccess.objects.filter(user=user).values_list("group_key", flat=True))


def is_portal_admin(user: object) -> bool:
    return bool(getattr(user, "is_superuser", False) or ADMIN_GROUP_NAME in user_group_names(user))


def can_access_menu_group(user: object, group_key: str) -> bool:
    if is_portal_admin(user):
        return True
    if group_key == MANAGEMENT_GROUP_KEY:
        return False

    return group_key in accessible_menu_group_keys(user)


def can_access_menu_item(user: object, menu_key: str) -> bool:
    item = MENU_BY_KEY.get(menu_key)
    return bool(item and can_access_menu_group(user, item.group_key))


def favorite_keys_for_user(user: object) -> list[str]:
    if not getattr(user, "is_authenticated", False):
        return []
    return list(
        UserFavoriteMenu.objects.filter(user=user, menu_key__in=MENU_BY_KEY.keys())
        .order_by("sort_order", "created_at")
        .values_list("menu_key", flat=True)
    )


def favorite_items_for_user(user: object) -> list[dict[str, object]]:
    items = []
    for key in favorite_keys_for_user(user):
        item = MENU_BY_KEY.get(key)
        if item is None:
            continue
        if not can_access_menu_item(user, item.key):
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


def next_sort_order(user: object) -> int:
    latest = UserFavoriteMenu.objects.filter(user=user).order_by("-sort_order").first()
    return 0 if latest is None else latest.sort_order + 1


def reorder_favorites(user: object, menu_keys: Iterable[str]) -> None:
    allowed_keys = [key for key in menu_keys if can_access_menu_item(user, key)]
    favorites = {favorite.menu_key: favorite for favorite in UserFavoriteMenu.objects.filter(user=user)}
    for index, key in enumerate(allowed_keys):
        favorite = favorites.get(key)
        if favorite is None:
            continue
        favorite.sort_order = index
        favorite.save(update_fields=["sort_order"])


def menu_items_with_favorite_state(user: object) -> list[dict[str, object]]:
    favorite_keys = set(favorite_keys_for_user(user))
    return [
        {
            "key": item.key,
            "title": item.title,
            "href": item.href,
            "is_favorite": item.key in favorite_keys,
        }
        for item in MENU_ITEMS
        if can_access_menu_item(user, item.key)
    ]


def menu_groups_with_items(user: object) -> list[dict[str, object]]:
    favorite_keys = set(favorite_keys_for_user(user))
    items_by_group = {group.key: [] for group in MENU_GROUPS}
    for item in MENU_ITEMS:
        if not can_access_menu_item(user, item.key):
            continue
        items_by_group.setdefault(item.group_key, []).append(
            {
                "key": item.key,
                "title": item.title,
                "href": item.href,
                "is_favorite": item.key in favorite_keys,
            }
        )

    return [
        {
            "key": group.key,
            "title": group.title,
            "items": items_by_group.get(group.key, []),
        }
        for group in MENU_GROUPS
        if can_access_menu_group(user, group.key)
    ]
