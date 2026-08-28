"""メニュー利用の記録（A-601）のユースケース。"""

from __future__ import annotations

from application.portal.domain.repositories.ports import MenuUsageLogRepository
from application.portal.domain.value_objects.usage_record import UsageRecordTarget


class RecordUsage:
    """判別済みの記録対象を、そのままメニュー利用ログとして追記する。"""

    def __init__(self, *, repository: MenuUsageLogRepository) -> None:
        self._repository = repository

    def record(self, *, user: object, target: UsageRecordTarget) -> None:
        self._repository.record(
            user=user,
            menu_key=target.menu_key,
            usage_type=target.usage_type,
        )
