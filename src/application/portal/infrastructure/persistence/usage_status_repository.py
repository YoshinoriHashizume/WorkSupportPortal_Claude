"""利用状況の集計を読み出す（design.md §5.3・§6.7）。"""

from __future__ import annotations

from datetime import datetime

from django.contrib.auth import get_user_model
from django.db.models import Count, Max, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from application.portal.domain.value_objects.constants import (
    ADMIN_GROUP_NAME,
    GENERAL_USER_GROUP_NAME,
)
from application.portal.domain.value_objects.usage_record import (
    USAGE_TYPE_EXPORT,
    USAGE_TYPE_VIEW,
)
from application.portal.models import MenuUsageLog, PortalMenuGroupAccess, UserAccessRequest


def _display_name(last_name: str, first_name: str, username: str) -> str:
    return f"{last_name} {first_name}".strip() or username


class DjangoUsageStatusRepository:
    """メニュー利用ログと利用申請・メニューグループ付与を集計する。

    集計期間は半開区間（`start_at` 以上・`end_at` 未満）で絞り込む。
    メニュー名・メニューグループ名の解決と最多利用メニュー（V-609）の判定は domain の責務であり、
    ここでは `menu_key` と回数を返すだけにとどめる。
    """

    # -- メニュー利用ログの集計 ------------------------------------------------

    @staticmethod
    def _logs_in_period(*, start_at: datetime, end_at: datetime):
        return MenuUsageLog.objects.filter(used_at__gte=start_at, used_at__lt=end_at)

    def overall_counts(self, *, start_at: datetime, end_at: datetime) -> dict[str, int]:
        aggregated = self._logs_in_period(start_at=start_at, end_at=end_at).aggregate(
            usage_count=Count("id"),
            export_count=Count("id", filter=Q(usage_type=USAGE_TYPE_EXPORT)),
            # 利用ユーザー数（V-604）。物理削除されたユーザーの行（user_id が NULL）は数えない
            active_user_count=Count("user", distinct=True),
        )
        return {
            "usage_count": int(aggregated["usage_count"] or 0),
            "export_count": int(aggregated["export_count"] or 0),
            "active_user_count": int(aggregated["active_user_count"] or 0),
        }

    def menu_counts(self, *, start_at: datetime, end_at: datetime) -> list[dict[str, object]]:
        rows = (
            self._logs_in_period(start_at=start_at, end_at=end_at)
            .values("menu_key")
            .annotate(
                view_count=Count("id", filter=Q(usage_type=USAGE_TYPE_VIEW)),
                export_count=Count("id", filter=Q(usage_type=USAGE_TYPE_EXPORT)),
                user_count=Count("user", distinct=True),
            )
            .order_by("menu_key")
        )
        return [
            {
                "menu_key": row["menu_key"],
                "view_count": int(row["view_count"]),
                "export_count": int(row["export_count"]),
                "user_count": int(row["user_count"]),
            }
            for row in rows
        ]

    def last_used_at_by_menu_key(self) -> dict[str, object]:
        """メニューごとの最終利用日時。集計期間ではなく全期間から求める。"""
        rows = MenuUsageLog.objects.values("menu_key").annotate(last_used_at=Max("used_at"))
        return {row["menu_key"]: row["last_used_at"] for row in rows}

    def user_counts(self, *, start_at: datetime, end_at: datetime) -> list[dict[str, object]]:
        rows = (
            self._logs_in_period(start_at=start_at, end_at=end_at)
            .exclude(user__isnull=True)
            .values("user_id")
            .annotate(
                usage_count=Count("id"),
                export_count=Count("id", filter=Q(usage_type=USAGE_TYPE_EXPORT)),
            )
            .order_by("user_id")
        )
        return [
            {
                "user_id": row["user_id"],
                "usage_count": int(row["usage_count"]),
                "export_count": int(row["export_count"]),
            }
            for row in rows
        ]

    def last_used_at_by_user(self) -> dict[int, object]:
        """ユーザーごとの最終利用日時。集計期間ではなく全期間から求める。"""
        rows = (
            MenuUsageLog.objects.exclude(user__isnull=True)
            .values("user_id")
            .annotate(last_used_at=Max("used_at"))
        )
        return {row["user_id"]: row["last_used_at"] for row in rows}

    def menu_counts_by_user(
        self, *, start_at: datetime, end_at: datetime
    ) -> list[dict[str, object]]:
        rows = (
            self._logs_in_period(start_at=start_at, end_at=end_at)
            .exclude(user__isnull=True)
            .values("user_id", "menu_key")
            .annotate(count=Count("id"))
            .order_by("user_id", "menu_key")
        )
        return [
            {
                "user_id": row["user_id"],
                "menu_key": row["menu_key"],
                "count": int(row["count"]),
            }
            for row in rows
        ]

    def used_menu_keys_by_user(
        self, *, start_at: datetime, end_at: datetime
    ) -> dict[int, set[str]]:
        pairs = (
            self._logs_in_period(start_at=start_at, end_at=end_at)
            .exclude(user__isnull=True)
            .values_list("user_id", "menu_key")
            .distinct()
        )
        used_menu_keys: dict[int, set[str]] = {}
        for user_id, menu_key in pairs:
            used_menu_keys.setdefault(user_id, set()).add(menu_key)
        return used_menu_keys

    def daily_counts(self, *, start_at: datetime, end_at: datetime) -> list[dict[str, object]]:
        """日別の利用回数。日付は現在のタイムゾーン（Asia/Tokyo）で解釈する。"""
        rows = (
            self._logs_in_period(start_at=start_at, end_at=end_at)
            .annotate(on=TruncDate("used_at"))
            .values("on")
            .annotate(count=Count("id"))
            .order_by("on")
        )
        return [{"on": row["on"], "count": int(row["count"])} for row in rows]

    def export_entries(
        self, *, start_at: datetime, end_at: datetime
    ) -> list[dict[str, object]]:
        logs = (
            self._logs_in_period(start_at=start_at, end_at=end_at)
            .filter(usage_type=USAGE_TYPE_EXPORT)
            .select_related("user")
            .order_by("-used_at")
        )
        entries = []
        for log in logs:
            user = log.user
            entries.append(
                {
                    "used_at": log.used_at,
                    "user_id": log.user_id,
                    "username": user.username if user is not None else None,
                    "display_name": (
                        _display_name(user.last_name, user.first_name, user.username)
                        if user is not None
                        else None
                    ),
                    "menu_key": log.menu_key,
                }
            )
        return entries

    # -- 利用申請・メニューグループ付与 ----------------------------------------

    def approved_user_entries(self) -> list[dict[str, object]]:
        """利用申請が許可済み（S-602）のユーザーを返す。無効（S-604）なユーザーも含む。"""
        approved_user_ids = UserAccessRequest.objects.filter(
            status=UserAccessRequest.Status.APPROVED
        ).values_list("user_id", flat=True)
        users = (
            get_user_model()
            .objects.filter(id__in=approved_user_ids)
            .prefetch_related("groups")
            .order_by("username")
        )
        entries = []
        for user in users:
            group_names = {group.name for group in user.groups.all()}
            entries.append(
                {
                    "user_id": user.pk,
                    "username": user.username,
                    "display_name": _display_name(user.last_name, user.first_name, user.username),
                    "role": (
                        ADMIN_GROUP_NAME
                        if ADMIN_GROUP_NAME in group_names
                        else GENERAL_USER_GROUP_NAME
                    ),
                    "is_active": bool(user.is_active),
                    "last_login": user.last_login,
                }
            )
        return entries

    def menu_group_grants(self) -> list[dict[str, object]]:
        """メニューグループの付与を付与日（V-613 ＝ `created_at` の日付）つきで返す。"""
        accesses = PortalMenuGroupAccess.objects.select_related("user").order_by(
            "user__username", "group_key"
        )
        grants = []
        for access in accesses:
            user = access.user
            grants.append(
                {
                    "user_id": access.user_id,
                    "username": user.username,
                    "display_name": _display_name(user.last_name, user.first_name, user.username),
                    "group_key": access.group_key,
                    "granted_on": timezone.localtime(access.created_at).date(),
                }
            )
        return grants
