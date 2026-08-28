"""SLIMS 取込の排他制御の検証。

L3レビュー指摘 L3-4 の是正（[tasks.md](../../../docs/spec/l3-review-remediation/tasks.md) B-2）。
取込は既存スナップショットを全件削除してから INSERT するため、同時実行すると
スナップショットが部分破壊されうる。排他ロックを取得できない要求は取込を行わない。
"""

from __future__ import annotations

import pytest
from django.db import connection

from application.inventory_order_alert.domain.value_objects.errors import (
    IMPORT_IN_PROGRESS_MESSAGE,
    ImportInProgressError,
)
from application.inventory_order_alert.infrastructure.persistence.import_lock import slims_import_lock

postgres_only = pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="アドバイザリロックは PostgreSQL でのみ有効（SQLite は単一プロセス前提で no-op）",
)


def test_import_in_progress_error_carries_code_and_message():
    error = ImportInProgressError()

    assert error.code == "IMPORT_IN_PROGRESS"
    assert str(error) == IMPORT_IN_PROGRESS_MESSAGE


@postgres_only
@pytest.mark.django_db(transaction=True)
def test_second_lock_from_another_connection_is_rejected():
    """別コネクションが保持中はロックを取得できず、取込を行わない。"""
    from django.db import connections, transaction

    other = connections.create_connection("default")
    other.set_autocommit(False)
    try:
        with other.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_xact_lock(%s)", [521_000_001])
            assert cursor.fetchone()[0] is True

        with pytest.raises(ImportInProgressError):
            with transaction.atomic(), slims_import_lock():
                pytest.fail("ロックを取得できてはならない")
    finally:
        other.rollback()
        other.close()


@postgres_only
@pytest.mark.django_db(transaction=True)
def test_lock_is_released_when_transaction_ends():
    """トランザクションスコープのロックのため、終了後は再取得できる。"""
    from django.db import transaction

    with transaction.atomic(), slims_import_lock():
        pass

    with transaction.atomic(), slims_import_lock():
        pass
