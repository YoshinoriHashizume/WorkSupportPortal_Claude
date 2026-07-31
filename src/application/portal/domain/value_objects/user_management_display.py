from __future__ import annotations

from application.portal.domain.value_objects.constants import VALID_SORT_DIRECTIONS

USER_MANAGEMENT_SORT_LABELS = {
    "username": "社員番号",
    "last_name": "姓",
    "first_name": "名",
    "full_name": "表示名",
    "role": "権限",
    "menu_groups": "使えるグループ",
    "status": "申請状態",
    "is_active": "有効",
    "last_login": "最終ログイン",
}


def user_management_sort_value(entry: dict[str, object], sort_key: str) -> object:
    user = entry["user"]
    if sort_key == "username":
        return user.username
    if sort_key == "last_name":
        return user.last_name
    if sort_key == "first_name":
        return user.first_name
    if sort_key == "full_name":
        return entry["full_name"]
    if sort_key == "role":
        return entry["role"]
    if sort_key == "menu_groups":
        return entry["menu_groups"]
    if sort_key == "status":
        return entry["status_label"]
    if sort_key == "is_active":
        return "1" if user.is_active else "0"
    if sort_key == "last_login":
        return user.last_login.isoformat() if user.last_login else ""
    return user.username


def sort_user_management_entries(
    entries: list[dict[str, object]],
    sort_key: str = "username",
    sort_direction: str = "asc",
) -> list[dict[str, object]]:
    valid_sort_key = sort_key if sort_key in USER_MANAGEMENT_SORT_LABELS else "username"
    reverse = sort_direction == "desc"
    return sorted(
        entries,
        key=lambda entry: str(user_management_sort_value(entry, valid_sort_key)),
        reverse=reverse,
    )


def user_management_column_headers(sort_key: str, sort_direction: str) -> list[dict[str, object]]:
    active_sort_key = sort_key if sort_key in USER_MANAGEMENT_SORT_LABELS else "username"
    active_direction = sort_direction if sort_direction in VALID_SORT_DIRECTIONS else "asc"
    return [
        {
            "key": key,
            "label": label,
            "sort_direction": "desc" if key == active_sort_key and active_direction == "asc" else "asc",
            "is_sorted": key == active_sort_key,
        }
        for key, label in USER_MANAGEMENT_SORT_LABELS.items()
    ]
