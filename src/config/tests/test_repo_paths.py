from __future__ import annotations

from pathlib import Path

from config.repo_paths import repo_root
from config.test_db_guard import assert_pytest_uses_test_database, is_test_database_name


def test_repo_root_finds_document_directory():
    root = repo_root(Path(__file__).resolve())
    assert (root / "Document").is_dir()
    assert (root / "docker-compose.devcontainer.yaml").is_file()


def test_is_test_database_name_accepts_prefix_and_sqlite_memory():
    assert is_test_database_name("test_worksupportportal")
    assert is_test_database_name("file:memorydb_default?mode=memory&cache=shared")
    assert not is_test_database_name("worksupportportal")


def test_assert_pytest_uses_test_database_allows_memory_sqlite():
    assert_pytest_uses_test_database("file:memorydb_default?mode=memory&cache=shared")
