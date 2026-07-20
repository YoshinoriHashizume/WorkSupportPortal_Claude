from __future__ import annotations

import pytest

from config.test_db_guard import assert_pytest_uses_test_database


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
