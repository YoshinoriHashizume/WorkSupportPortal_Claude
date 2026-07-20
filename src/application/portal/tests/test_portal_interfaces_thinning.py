from __future__ import annotations

from application.portal.domain.value_objects.database_display import (
    display_database_value,
    menu_group_choices_in_order,
)
from application.portal.domain.value_objects.user_management_display import (
    sort_user_management_entries,
    user_management_column_headers,
    user_management_sort_value,
)
from application.portal.use_cases.access_requests import AccessRequests
from application.portal.use_cases.database_page import DatabasePage
from application.portal.use_cases.notice_management import NoticeManagement
from application.portal.use_cases.user_management import UserManagement

class _FakeUser:
    def __init__(self, user_id: int, username: str = "10001") -> None:
        self.id = user_id
        self.username = username
        self.last_name = "山田"
        self.first_name = "太郎"
        self.is_active = True
        self.last_login = None


def test_display_database_value_masks_sensitive_columns():
    assert display_database_value("password", "secret") == "********"
    assert display_database_value("api_token", "abc") == "********"
    assert display_database_value("name", "ok") == "ok"


def test_menu_group_choices_exclude_management():
    keys = {item["key"] for item in menu_group_choices_in_order()}
    assert "management" not in keys
    assert "company" in keys


def test_user_management_sort_and_headers():
    entries = [
        {
            "user": _FakeUser(2, "10002"),
            "full_name": "B",
            "role": "一般ユーザー",
            "menu_groups": "-",
            "status_label": "-",
        },
        {
            "user": _FakeUser(1, "10001"),
            "full_name": "A",
            "role": "管理者",
            "menu_groups": "-",
            "status_label": "-",
        },
    ]
    sorted_entries = sort_user_management_entries(entries, "username", "asc")
    assert sorted_entries[0]["user"].username == "10001"
    assert user_management_sort_value(sorted_entries[0], "full_name") == "A"
    headers = user_management_column_headers("username", "asc")
    assert headers[0]["is_sorted"] is True
    assert headers[0]["sort_direction"] == "desc"


def test_user_management_delete_self_returns_false():
    deleted: list[object] = []

    class Repo:
        def list_entries(self):
            return []

        def get_user(self, user_id: str):
            return None

        def delete_user(self, target_user: object) -> None:
            deleted.append(target_user)

        def update_profile(self, *args, **kwargs) -> None:
            raise AssertionError("unused")

        def set_role_and_menu_groups(self, *args, **kwargs) -> None:
            raise AssertionError("unused")

    actor = _FakeUser(1)
    usecase = UserManagement(Repo())
    assert usecase.delete_user(actor=actor, target_user=actor) is False
    assert deleted == []


def test_user_management_delete_other_user():
    deleted: list[object] = []

    class Repo:
        def list_entries(self):
            return []

        def get_user(self, user_id: str):
            return None

        def delete_user(self, target_user: object) -> None:
            deleted.append(target_user)

        def update_profile(self, *args, **kwargs) -> None:
            raise AssertionError("unused")

        def set_role_and_menu_groups(self, *args, **kwargs) -> None:
            raise AssertionError("unused")

    actor = _FakeUser(1)
    target = _FakeUser(2)
    usecase = UserManagement(Repo())
    assert usecase.delete_user(actor=actor, target_user=target) is True
    assert deleted == [target]


def test_access_requests_approve_and_reject():
    calls: list[tuple] = []

    class Repo:
        def list_pending_entries(self):
            return [{"id": 1}]

        def list_role_groups(self):
            return ["管理者"]

        def approve(self, **kwargs):
            calls.append(("approve", kwargs))

        def reject(self, **kwargs):
            calls.append(("reject", kwargs))

    usecase = AccessRequests(Repo())
    context = usecase.page_context()
    assert context["access_request_entries"] == [{"id": 1}]
    usecase.process(
        reviewer=_FakeUser(1),
        request_id="9",
        action="approve",
        role="管理者",
        menu_group_keys=["company"],
        note="ok",
    )
    usecase.process(
        reviewer=_FakeUser(1),
        request_id="10",
        action="reject",
        role="",
        menu_group_keys=[],
        note="ng",
    )
    assert calls[0][0] == "approve"
    assert calls[1][0] == "reject"


def test_notice_management_create_update_delete():
    ops: list[tuple] = []

    class Repo:
        def list_published(self, *, limit: int):
            return []

        def list_all(self):
            return ["n1"]

        def delete(self, notice_id: str) -> None:
            ops.append(("delete", notice_id))

        def create(self, **kwargs) -> None:
            ops.append(("create", kwargs))

        def update(self, notice_id: str, **kwargs) -> None:
            ops.append(("update", notice_id, kwargs))

    usecase = NoticeManagement(Repo())
    assert usecase.page_context()["notices"] == ["n1"]
    usecase.process(actor=_FakeUser(1), action="delete", notice_id="3", title="", body="", is_published=False)
    usecase.process(
        actor=_FakeUser(1),
        action=None,
        notice_id=None,
        title="t",
        body="b",
        is_published=True,
    )
    usecase.process(
        actor=_FakeUser(1),
        action=None,
        notice_id="5",
        title="t2",
        body="b2",
        is_published=False,
    )
    assert ops[0] == ("delete", "3")
    assert ops[1][0] == "create"
    assert ops[2][0] == "update"


def test_database_page_without_table():
    class Browser:
        def list_table_names(self):
            return ["auth_user"]

        def fetch_table_preview(self, *args, **kwargs):
            raise AssertionError("should not fetch")

    context = DatabasePage(Browser()).execute(selected_table="", sort_column="", sort_direction="asc")
    assert context["table_names"] == ["auth_user"]
    assert context["rows"] == []


def test_database_page_unknown_table():
    class Browser:
        def list_table_names(self):
            return ["auth_user"]

        def fetch_table_preview(self, *args, **kwargs):
            raise AssertionError("should not fetch")

    context = DatabasePage(Browser()).execute(selected_table="missing", sort_column="", sort_direction="asc")
    assert context["error"] == "選択されたテーブルが見つかりません。"


def test_database_page_fetches_preview():
    class Browser:
        def list_table_names(self):
            return ["auth_user"]

        def fetch_table_preview(self, table_name, *, sort_column, sort_direction, row_limit):
            assert table_name == "auth_user"
            assert row_limit == 100
            return {
                "columns": ["id"],
                "column_headers": [{"name": "id", "sort_direction": "asc", "is_sorted": False}],
                "rows": [["1"]],
                "total_count": 1,
                "sort_column": "",
                "sort_direction": "asc",
            }

    context = DatabasePage(Browser()).execute(selected_table="auth_user", sort_column="", sort_direction="asc")
    assert context["rows"] == [["1"]]
    assert context["total_count"] == 1
