from __future__ import annotations

from django.contrib.auth import get_user_model


def format_user_display_name(*, last_name: str, first_name: str, username: str) -> str:
    name = f"{last_name or ''}{first_name or ''}".strip()
    return name or username


def user_display_name_from_model(user: object) -> str:
    return format_user_display_name(
        last_name=str(getattr(user, "last_name", "") or ""),
        first_name=str(getattr(user, "first_name", "") or ""),
        username=str(getattr(user, "username", "") or ""),
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
