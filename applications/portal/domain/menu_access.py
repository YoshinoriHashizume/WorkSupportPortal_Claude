from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from applications.portal.domain.constants import MANAGEMENT_GROUP_KEY, RECEIPT_COMPARISON_PATH, RECEIPT_COMPARISON_MENU_KEYS
from applications.portal.domain.menu import MENU_BY_KEY, MENU_GROUP_BY_KEY, MENU_GROUP_KEY_BY_TITLE, MENU_ITEMS, PortalMenuItem


def normalize_menu_group_key(group_key: str) -> str:
    key = (group_key or "").strip()
    if key in MENU_GROUP_BY_KEY:
        return key
    return MENU_GROUP_KEY_BY_TITLE.get(key, key)


def normalize_menu_group_keys(group_keys: set[str]) -> set[str]:
    return {normalize_menu_group_key(key) for key in group_keys}


def receipt_comparison_menu_key(comparison_type: str) -> str:
    return RECEIPT_COMPARISON_MENU_KEYS.get(
        comparison_type,
        RECEIPT_COMPARISON_MENU_KEYS["finished-product"],
    )


def receipt_comparison_type_from_path(path: str) -> str:
    if "/supplied-parts" in path:
        return "supplied-parts"
    return "finished-product"


def menu_title(menu_key: str) -> str:
    item = MENU_BY_KEY.get(menu_key)
    return item.title if item else menu_key


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


def can_access_menu_group(
    *,
    is_admin: bool,
    accessible_group_keys: set[str],
    group_key: str,
) -> bool:
    if is_admin:
        return True
    if group_key == MANAGEMENT_GROUP_KEY:
        return False
    return group_key in accessible_group_keys


def can_access_menu_item(
    *,
    is_admin: bool,
    accessible_group_keys: set[str],
    menu_key: str,
) -> bool:
    item = MENU_BY_KEY.get(menu_key)
    if item is None:
        return False
    if not item.href:
        return any(
            can_access_menu_item(
                is_admin=is_admin,
                accessible_group_keys=accessible_group_keys,
                menu_key=child.key,
            )
            for child in MENU_ITEMS
            if child.parent_key == menu_key
        )
    return can_access_menu_group(
        is_admin=is_admin,
        accessible_group_keys=accessible_group_keys,
        group_key=item.group_key,
    )


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
