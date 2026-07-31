from __future__ import annotations

from typing import Protocol


class FavoriteRepository(Protocol):
    def favorite_keys_for_user(self, user: object) -> list[str]: ...

    def next_sort_order(self, user: object) -> int: ...

    def get_or_create_favorite(self, user: object, menu_key: str, sort_order: int) -> None: ...

    def delete_favorite(self, user: object, menu_key: str) -> None: ...

    def list_favorites(self, user: object) -> dict[str, object]: ...

    def reorder_favorites(self, user: object, menu_keys: list[str]) -> None: ...


class MenuAccessRepository(Protocol):
    def user_group_names(self, user: object) -> set[str]: ...

    def accessible_menu_group_keys(self, user: object) -> set[str]: ...


class NoticeRepository(Protocol):
    def list_published(self, *, limit: int) -> list[object]: ...

    def list_all(self) -> list[object]: ...

    def delete(self, notice_id: str) -> None: ...

    def create(self, *, title: str, body: str, is_published: bool, created_by: object) -> None: ...

    def update(self, notice_id: str, *, title: str, body: str, is_published: bool) -> None: ...


class AccessRequestRepository(Protocol):
    def list_pending_entries(self) -> list[dict[str, object]]: ...

    def list_role_groups(self) -> list[object]: ...

    def approve(
        self,
        *,
        request_id: str,
        reviewer: object,
        role_name: str,
        menu_group_keys: list[str],
        note: str,
    ) -> None: ...

    def reject(self, *, request_id: str, reviewer: object, note: str) -> None: ...


class UserManagementRepository(Protocol):
    def list_entries(self) -> list[dict[str, object]]: ...

    def get_user(self, user_id: str) -> object | None: ...

    def delete_user(self, target_user: object) -> None: ...

    def update_profile(
        self,
        target_user: object,
        *,
        last_name: str,
        first_name: str,
        email: str,
    ) -> None: ...

    def set_role_and_menu_groups(
        self,
        target_user: object,
        *,
        role_name: str,
        menu_group_keys: list[str],
    ) -> None: ...


class DatabaseBrowser(Protocol):
    def list_table_names(self) -> list[str]: ...

    def fetch_table_preview(
        self,
        table_name: str,
        *,
        sort_column: str,
        sort_direction: str,
        row_limit: int,
    ) -> dict[str, object]: ...
