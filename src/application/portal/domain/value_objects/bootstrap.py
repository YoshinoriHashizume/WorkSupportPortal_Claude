from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BootstrapLocalDevConfig:
    username: str
    password: str
    last_name: str
    first_name: str


@dataclass(frozen=True)
class BootstrapProductionAdminConfig:
    username: str
    last_name: str
    first_name: str


@dataclass(frozen=True)
class BootstrapUserResult:
    created: bool
    username: str
    menu_groups_granted: int
