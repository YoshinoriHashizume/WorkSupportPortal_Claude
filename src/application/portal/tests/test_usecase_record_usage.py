"""メニュー利用の記録ユースケース（RecordUsage）のテスト。"""

from __future__ import annotations

import pytest

from application.portal.domain.value_objects.usage_record import UsageRecordTarget
from application.portal.use_cases.record_usage import RecordUsage


class FakeMenuUsageLogRepository:
    """MenuUsageLogRepository ポートを満たす記録用のフェイク。"""

    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self._error = error

    def record(self, *, user: object, menu_key: str, usage_type: str) -> None:
        if self._error is not None:
            raise self._error
        self.calls.append({"user": user, "menu_key": menu_key, "usage_type": usage_type})


def test_record_usage_passes_target_to_repository():
    """記録対象のメニューキーと利用種別と利用者がそのままリポジトリに渡る。"""
    repository = FakeMenuUsageLogRepository()
    usecase = RecordUsage(repository=repository)
    user = object()
    target = UsageRecordTarget(menu_key="shipment-trend-list", usage_type="VIEW")

    usecase.record(user=user, target=target)

    assert repository.calls == [
        {"user": user, "menu_key": "shipment-trend-list", "usage_type": "VIEW"}
    ]


def test_record_usage_passes_export_usage_type():
    """出力の記録対象は利用種別 EXPORT のままリポジトリに渡る。"""
    repository = FakeMenuUsageLogRepository()
    usecase = RecordUsage(repository=repository)
    target = UsageRecordTarget(menu_key="asset-inventory", usage_type="EXPORT")

    usecase.record(user=object(), target=target)

    assert repository.calls[0]["usage_type"] == "EXPORT"


def test_record_usage_propagates_repository_error():
    """リポジトリの例外は握りつぶさずそのまま伝播する。"""
    repository = FakeMenuUsageLogRepository(error=RuntimeError("DB エラー"))
    usecase = RecordUsage(repository=repository)
    target = UsageRecordTarget(menu_key="usage-status", usage_type="VIEW")

    with pytest.raises(RuntimeError):
        usecase.record(user=object(), target=target)
