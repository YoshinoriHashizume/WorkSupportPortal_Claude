from __future__ import annotations

import os

import pytest

from config.test_db_guard import assert_pytest_uses_test_database


#: 実 Oracle に接続してテストしたい場合に立てる環境変数。
#: 立てない限り、テストは `.env` の `ORACLE_USE_MOCK` に関わらずモックを使う。
REAL_ORACLE_ENV_VAR = "WSP_TEST_ORACLE_REAL"


def pytest_configure(config) -> None:
    """テストの既定を Oracle モックに固定する。

    `.env` の `ORACLE_USE_MOCK=false` をそのまま拾うと、ビューテストが実 Oracle へ
    接続を試みて環境依存で失敗する（thin モードでは `DPY-3015` 等）。テストは
    周囲の `.env` に依存すべきではないため、ここで既定値を与える。

    - 個別テストの `monkeypatch.setenv("ORACLE_USE_MOCK", ...)` は従来どおり優先される
      （本フックはセッション開始時に一度だけ既定値を置くため）。
    - 実 Oracle に対して検証したい場合は `WSP_TEST_ORACLE_REAL=1` を設定する。
      このとき `ORACLE_USE_MOCK` は変更せず、`.env` の設定に従う。
    """
    if str(os.environ.get(REAL_ORACLE_ENV_VAR, "") or "").strip().lower() in {"1", "true", "yes", "on"}:
        return
    os.environ["ORACLE_USE_MOCK"] = "true"


@pytest.fixture(scope="session")
def django_db_use_migrations() -> bool:
    """SQLite では一部マイグレーションが失敗するため、テストはモデルからスキーマ生成する。"""
    return False


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        from django.db import connection

        assert_pytest_uses_test_database(connection.settings_dict.get("NAME"))
    yield
