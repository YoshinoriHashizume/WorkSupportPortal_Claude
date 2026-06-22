from __future__ import annotations


def is_test_database_name(db_name: object) -> bool:
    return str(db_name or "").startswith("test_")


def assert_pytest_uses_test_database(db_name: object) -> None:
    name = str(db_name or "")
    if not is_test_database_name(name):
        raise RuntimeError(
            "pytest は開発用 PostgreSQL ではなく test_ プレフィックス付き DB で実行してください。"
            f" 現在の DB 名: {name!r}"
        )
