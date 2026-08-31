from __future__ import annotations

from django.http import HttpRequest

from .favorites import favorite_items_for_user, menu_groups_with_items, menu_items_with_favorite_state, receipt_comparison_type_from_path


def portal_menu(request: HttpRequest) -> dict[str, object]:
    current_path = request.path
    current_type = request.GET.get("type") or receipt_comparison_type_from_path(current_path)
    return {
        "portal_menu_items": menu_items_with_favorite_state(request.user, current_path, current_type),
        "portal_menu_groups": menu_groups_with_items(request.user, current_path, current_type),
        "portal_favorite_items": favorite_items_for_user(request.user),
    }
