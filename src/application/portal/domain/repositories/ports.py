from __future__ import annotations

from datetime import datetime
from typing import Protocol

from application.portal.domain.value_objects.bootstrap import (
    BootstrapLocalDevConfig,
    BootstrapProductionAdminConfig,
    BootstrapUserResult,
)


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


class MenuUsageLogRepository(Protocol):
    """メニュー利用ログ（E-601）を追記する。更新・削除の手段は公開しない。"""

    def record(self, *, user: object, menu_key: str, usage_type: str) -> None: ...


class UsageStatusRepository(Protocol):
    """利用状況の集計を読み出す。集計期間は aware な datetime で受け取る。"""

    def overall_counts(self, *, start_at: datetime, end_at: datetime) -> dict[str, int]: ...

    def menu_counts(self, *, start_at: datetime, end_at: datetime) -> list[dict[str, object]]: ...

    def last_used_at_by_menu_key(self) -> dict[str, object]: ...

    def user_counts(self, *, start_at: datetime, end_at: datetime) -> list[dict[str, object]]: ...

    def last_used_at_by_user(self) -> dict[int, object]: ...

    def menu_counts_by_user(
        self, *, start_at: datetime, end_at: datetime
    ) -> list[dict[str, object]]: ...

    def used_menu_keys_by_user(
        self, *, start_at: datetime, end_at: datetime
    ) -> dict[int, set[str]]: ...

    def daily_counts(self, *, start_at: datetime, end_at: datetime) -> list[dict[str, object]]: ...

    def export_entries(
        self, *, start_at: datetime, end_at: datetime
    ) -> list[dict[str, object]]: ...

    def approved_user_entries(self) -> list[dict[str, object]]: ...

    def menu_group_grants(self) -> list[dict[str, object]]: ...


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


class BootstrapLocalDevRunner(Protocol):
    """開発用ログインユーザーを作成／更新し、管理者権限とメニュー権限を付与する。"""

    def __call__(self, config: BootstrapLocalDevConfig) -> BootstrapUserResult: ...


class BootstrapProductionAdminRunner(Protocol):
    """本番の初期管理者ユーザーを作成／更新する。パスワードは設定しない。"""

    def __call__(self, config: BootstrapProductionAdminConfig) -> BootstrapUserResult: ...
