from __future__ import annotations

from django.contrib.auth import get_user_model

from apps.inventory_order_alert.domain.user_display import (
    format_user_display_name,
    user_display_name_from_model,
)


def resolve_user_display_names(usernames: set[str]) -> dict[str, str]:
    normalized = {str(username).strip() for username in usernames if str(username or "").strip()}
    if not normalized:
        return {}

    User = get_user_model()
    display_names: dict[str, str] = {}
    for user in User.objects.filter(username__in=normalized):
        display_names[user.username] = user_display_name_from_model(user)

    for username in normalized:
        display_names.setdefault(username, username)
    return display_names


__all__ = ["format_user_display_name", "resolve_user_display_names"]
