from __future__ import annotations

from django.http import HttpRequest

from .favorites import favorite_items_for_user, menu_groups_with_items, menu_items_with_favorite_state


def portal_menu(request: HttpRequest) -> dict[str, object]:
    return {
        "portal_menu_items": menu_items_with_favorite_state(request.user),
        "portal_menu_groups": menu_groups_with_items(request.user),
        "portal_favorite_items": favorite_items_for_user(request.user),
    }
