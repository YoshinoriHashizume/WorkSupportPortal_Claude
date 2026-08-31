from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DesknetUserInfo:
    employee_id: str
    user_id: str
    name: str
    default_group_id: str
    access_key: str


def split_desknet_name(name: str) -> tuple[str, str]:
    parts = (name or "").replace("\u3000", " ").split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    return "", name.strip()
