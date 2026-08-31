from __future__ import annotations


def format_user_display_name(*, last_name: str, first_name: str, username: str) -> str:
    name = f"{last_name or ''}{first_name or ''}".strip()
    return name or username


def user_display_name_from_model(user: object) -> str:
    return format_user_display_name(
        last_name=str(getattr(user, "last_name", "") or ""),
        first_name=str(getattr(user, "first_name", "") or ""),
        username=str(getattr(user, "username", "") or ""),
    )
