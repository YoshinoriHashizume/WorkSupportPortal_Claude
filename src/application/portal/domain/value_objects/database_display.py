from __future__ import annotations

from application.portal.domain.value_objects.constants import (
    MANAGEMENT_MENU_GROUP_KEY,
    SENSITIVE_COLUMN_NAMES,
)
from application.portal.domain.value_objects.menu import MENU_GROUPS, PortalMenuGroup


def assignable_menu_groups() -> list[PortalMenuGroup]:
    return [group for group in MENU_GROUPS if group.key != MANAGEMENT_MENU_GROUP_KEY]


def menu_group_choices_in_order() -> list[dict[str, str]]:
    return [{"key": group.key, "title": group.title} for group in assignable_menu_groups()]


def display_database_value(column_name: str, value: object) -> str:
    if value is None:
        return ""
    normalized_column = column_name.lower()
    if normalized_column in SENSITIVE_COLUMN_NAMES or "token" in normalized_column or "secret" in normalized_column:
        return "********"

    text = str(value)
    return text if len(text) <= 200 else f"{text[:200]}..."
