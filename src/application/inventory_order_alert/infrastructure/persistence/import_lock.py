from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from django.db import connection

from application.inventory_order_alert.domain.value_objects.errors import ImportInProgressError

# SLIMS 取込の排他を表す固定キー。他機能のアドバイザリロックと衝突しない値を割り当てる。
SLIMS_IMPORT_LOCK_KEY = 521_000_001


@contextmanager
def slims_import_lock() -> Iterator[None]:
    """SLIMS 取込の排他ロックを取得する。取得できない場合は ImportInProgressError。

    PostgreSQL では **トランザクションスコープ** のアドバイザリロックを使うため、
    必ず ``transaction.atomic()`` の内側で呼び出すこと。トランザクション終了時に
    自動解放されるため、解放漏れやプロセス異常終了によるロック残留が起きない。

    ロック機構を持たない開発用の SQLite バックエンドでは何もしない（単一プロセス前提）。
    """
    if connection.vendor != "postgresql":
        yield
        return

    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_xact_lock(%s)", [SLIMS_IMPORT_LOCK_KEY])
        acquired = bool(cursor.fetchone()[0])
    if not acquired:
        raise ImportInProgressError()
    yield
