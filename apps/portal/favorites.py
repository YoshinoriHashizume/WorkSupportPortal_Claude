from __future__ import annotations

from collections.abc import Iterable

from urllib.parse import parse_qs, urlparse

from .menu import MENU_BY_KEY, MENU_GROUPS, MENU_GROUP_BY_KEY, MENU_ITEMS, PortalMenuItem
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
    if item is None:
        return False
    if not item.href:
        return any(
            can_access_menu_item(user, child.key)
            for child in MENU_ITEMS
            if child.parent_key == menu_key
        )
    return bool(can_access_menu_group(user, item.group_key))


RECEIPT_COMPARISON_PATH = "/app/production/receipt-comparison"


def receipt_comparison_type_from_path(path: str) -> str:
    if "/supplied-parts" in path:
        return "supplied-parts"
    return "finished-product"


def is_menu_path_active(current_path: str, href: str, current_type: str = "") -> bool:
    if not href:
        return False
    parsed = urlparse(href)
    href_path = parsed.path.rstrip("/")
    normalized_path = current_path.rstrip("/")
    if href_path == RECEIPT_COMPARISON_PATH:
        if not normalized_path.startswith(RECEIPT_COMPARISON_PATH):
            return False
        href_type = parse_qs(parsed.query).get("type", ["finished-product"])[0]
        active_type = current_type or receipt_comparison_type_from_path(normalized_path)
        return href_type == active_type
    return normalized_path == href_path or normalized_path.startswith(f"{href_path}/")


def menu_item_payload(
    item: PortalMenuItem,
    favorite_keys: set[str],
    current_path: str = "",
    current_type: str = "",
) -> dict[str, object]:
    return {
        "key": item.key,
        "title": item.title,
        "href": item.href,
        "is_favorite": item.key in favorite_keys,
        "is_active": is_menu_path_active(current_path, item.href, current_type),
    }


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


def menu_items_with_favorite_state(user: object, current_path: str = "", current_type: str = "") -> list[dict[str, object]]:
    favorite_keys = set(favorite_keys_for_user(user))
    return [
        menu_item_payload(item, favorite_keys, current_path, current_type)
        for item in MENU_ITEMS
        if item.href and can_access_menu_item(user, item.key)
    ]


def menu_groups_with_items(user: object, current_path: str = "", current_type: str = "") -> list[dict[str, object]]:
    favorite_keys = set(favorite_keys_for_user(user))
    children_by_parent: dict[str, list[PortalMenuItem]] = {}
    for item in MENU_ITEMS:
        if item.parent_key:
            children_by_parent.setdefault(item.parent_key, []).append(item)

    items_by_group = {group.key: [] for group in MENU_GROUPS}
    for item in MENU_ITEMS:
        if item.parent_key:
            continue
        if not can_access_menu_item(user, item.key):
            continue
        if item.href:
            items_by_group.setdefault(item.group_key, []).append(
                menu_item_payload(item, favorite_keys, current_path, current_type)
            )
            continue

        children = [
            menu_item_payload(child, favorite_keys, current_path, current_type)
            for child in children_by_parent.get(item.key, [])
            if can_access_menu_item(user, child.key)
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
        if not can_access_menu_group(user, group.key):
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
