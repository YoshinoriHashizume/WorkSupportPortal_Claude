from __future__ import annotations


def is_test_database_name(db_name: object) -> bool:
    name = str(db_name or "")
    if name.startswith("test_"):
        return True
    # pytest-django の SQLite インメモリ（--nomigrations / 既定）
    if "memorydb" in name or name in {":memory:", "file:memorydb_default?mode=memory&cache=shared"}:
        return True
    if name.endswith(".sqlite3") and "test" in name.lower():
        return True
    return False


def assert_pytest_uses_test_database(db_name: object) -> None:
    name = str(db_name or "")
    if not is_test_database_name(name):
        raise RuntimeError(
            "pytest は開発用 PostgreSQL ではなく test_ プレフィックス付き DB "
            "（または pytest 用 SQLite）で実行してください。"
            f" 現在の DB 名: {name!r}"
        )
