from __future__ import annotations

from django.utils import timezone

from application.portal.models import MenuUsageLog


class DjangoMenuUsageLogRepository:
    """メニュー利用ログを 1 行追記する。更新・削除の手段は公開しない。"""

    def record(self, *, user: object, menu_key: str, usage_type: str) -> None:
        if not menu_key:
            return
        MenuUsageLog.objects.create(
            user=user,
            menu_key=menu_key,
            usage_type=usage_type,
            used_at=timezone.now(),
        )
