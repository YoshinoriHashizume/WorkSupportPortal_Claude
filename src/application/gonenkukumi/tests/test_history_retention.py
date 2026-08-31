"""検索履歴の保持上限の検証。

L3レビュー指摘 L3-19 の是正（[tasks.md](../../../docs/spec/l3-review-remediation/tasks.md) B-5）。
履歴行はユーザー数 × 検索回数で無制限に増加していたため、保存時に上限超過分を削除する。
"""

from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model

from application.gonenkukumi.domain.value_objects.schemas import GonenKukumiSearchParams
from application.gonenkukumi.infrastructure.persistence.history_repository import (
    HISTORY_RETENTION_LIMIT,
    DjangoGonenKukumiHistoryRepository,
)
from application.gonenkukumi.models import GonenKukumiSearchHistory


def _params(year_month: str) -> GonenKukumiSearchParams:
    return GonenKukumiSearchParams(
        cust_code="101",
        cust_item="ITEM-001",
        option_change="*",
        year_month=year_month,
        as_of_date=date(2026, 8, 7),
    )


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="gonenkukumi-history-user")


@pytest.mark.django_db
def test_history_is_capped_at_retention_limit(user):
    repository = DjangoGonenKukumiHistoryRepository()

    for index in range(HISTORY_RETENTION_LIMIT + 15):
        repository.save(user.id, _params(f"2026-{(index % 12) + 1:02d}"))

    assert GonenKukumiSearchHistory.objects.filter(user_id=user.id).count() == HISTORY_RETENTION_LIMIT


@pytest.mark.django_db
def test_history_keeps_the_newest_rows(user):
    repository = DjangoGonenKukumiHistoryRepository()

    for index in range(HISTORY_RETENTION_LIMIT + 5):
        repository.save(user.id, _params(f"2026-{(index % 12) + 1:02d}"))

    remaining = GonenKukumiSearchHistory.objects.filter(user_id=user.id).order_by("-executed_at")
    newest = remaining.first()
    oldest_kept = remaining.last()

    # 直近の保存が残り、最初の 5 件は削除されている
    assert newest is not None and oldest_kept is not None
    assert newest.executed_at >= oldest_kept.executed_at
    assert remaining.count() == HISTORY_RETENTION_LIMIT


@pytest.mark.django_db
def test_retention_is_per_user(user):
    other = get_user_model().objects.create_user(username="gonenkukumi-history-other")
    repository = DjangoGonenKukumiHistoryRepository()

    for index in range(HISTORY_RETENTION_LIMIT + 3):
        repository.save(user.id, _params("2026-05"))
    repository.save(other.id, _params("2026-05"))

    assert GonenKukumiSearchHistory.objects.filter(user_id=user.id).count() == HISTORY_RETENTION_LIMIT
    assert GonenKukumiSearchHistory.objects.filter(user_id=other.id).count() == 1
