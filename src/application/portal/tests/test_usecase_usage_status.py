"""利用状況（画面側）のユースケースのテスト。

対応: test-design.md TC-APP-010〜025
リポジトリはフェイクに差し替え、DB を使わない。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from application.portal.domain.value_objects.usage_status_display import (
    EXPORT_LOG_SORT_LABELS,
    GROUP_TITLE_SEPARATOR,
    MENU_USAGE_SORT_LABELS,
    UNUSED_GRANT_SORT_LABELS,
    USAGE_STATUS_CSV_ROW_LIMIT,
    USAGE_STATUS_PURPOSE_NOTE,
    USER_USAGE_SORT_LABELS,
)
from application.portal.domain.value_objects.usage_period import MESSAGE_OUT_OF_ORDER
from application.portal.use_cases.usage_status import UsageStatus

JST = timezone(timedelta(hours=9))
TODAY = date(2026, 8, 27)

SALES_MENU_KEY = "shipment-trend-list"
GENERAL_AFFAIRS_MENU_KEY = "asset-inventory"


class FakeUsageStatusRepository:
    """`UsageStatusRepository` を満たすフェイク。受け取った集計期間を記録する。"""

    def __init__(
        self,
        *,
        overall=None,
        menus=None,
        last_used_at_by_menu=None,
        users=None,
        last_used_at_by_user_id=None,
        menu_counts_per_user=None,
        used_menu_keys=None,
        daily=None,
        exports=None,
        approved_users=None,
        grants=None,
    ) -> None:
        self._overall = overall or {"usage_count": 0, "export_count": 0, "active_user_count": 0}
        self._menus = menus or []
        self._last_used_at_by_menu = last_used_at_by_menu or {}
        self._users = users or []
        self._last_used_at_by_user_id = last_used_at_by_user_id or {}
        self._menu_counts_per_user = menu_counts_per_user or []
        self._used_menu_keys = used_menu_keys or {}
        self._daily = daily or []
        self._exports = exports or []
        self._approved_users = approved_users or []
        self._grants = grants or []
        self.calls: list[tuple[str, dict[str, object]]] = []

    def _record(self, name: str, **kwargs: object) -> None:
        self.calls.append((name, kwargs))

    def overall_counts(self, *, start_at, end_at):
        self._record("overall_counts", start_at=start_at, end_at=end_at)
        return dict(self._overall)

    def menu_counts(self, *, start_at, end_at):
        self._record("menu_counts", start_at=start_at, end_at=end_at)
        return [dict(row) for row in self._menus]

    def last_used_at_by_menu_key(self):
        self._record("last_used_at_by_menu_key")
        return dict(self._last_used_at_by_menu)

    def user_counts(self, *, start_at, end_at):
        self._record("user_counts", start_at=start_at, end_at=end_at)
        return [dict(row) for row in self._users]

    def last_used_at_by_user(self):
        self._record("last_used_at_by_user")
        return dict(self._last_used_at_by_user_id)

    def menu_counts_by_user(self, *, start_at, end_at):
        self._record("menu_counts_by_user", start_at=start_at, end_at=end_at)
        return [dict(row) for row in self._menu_counts_per_user]

    def used_menu_keys_by_user(self, *, start_at, end_at):
        self._record("used_menu_keys_by_user", start_at=start_at, end_at=end_at)
        return {user_id: set(keys) for user_id, keys in self._used_menu_keys.items()}

    def daily_counts(self, *, start_at, end_at):
        self._record("daily_counts", start_at=start_at, end_at=end_at)
        return [dict(row) for row in self._daily]

    def export_entries(self, *, start_at, end_at):
        self._record("export_entries", start_at=start_at, end_at=end_at)
        return [dict(row) for row in self._exports]

    def approved_user_entries(self):
        self._record("approved_user_entries")
        return [dict(row) for row in self._approved_users]

    def menu_group_grants(self):
        self._record("menu_group_grants")
        return [dict(row) for row in self._grants]


def sample_repository() -> FakeUsageStatusRepository:
    """test-design.md §3.1 の正常系テストデータを返すフェイク。"""
    return FakeUsageStatusRepository(
        overall={"usage_count": 6, "export_count": 2, "active_user_count": 2},
        menus=[
            {
                "menu_key": SALES_MENU_KEY,
                "view_count": 2,
                "export_count": 2,
                "user_count": 1,
            },
            {
                "menu_key": GENERAL_AFFAIRS_MENU_KEY,
                "view_count": 2,
                "export_count": 0,
                "user_count": 2,
            },
        ],
        last_used_at_by_menu={
            SALES_MENU_KEY: datetime(2026, 8, 6, 0, 0, tzinfo=JST),
            GENERAL_AFFAIRS_MENU_KEY: datetime(2026, 8, 4, 9, 0, tzinfo=JST),
        },
        users=[
            {"user_id": 10002, "usage_count": 4, "export_count": 1},
            {"user_id": 10003, "usage_count": 1, "export_count": 0},
        ],
        last_used_at_by_user_id={
            10002: datetime(2026, 8, 6, 0, 0, tzinfo=JST),
            10003: datetime(2026, 8, 4, 9, 0, tzinfo=JST),
        },
        menu_counts_per_user=[
            {"user_id": 10002, "menu_key": SALES_MENU_KEY, "count": 3},
            {"user_id": 10002, "menu_key": GENERAL_AFFAIRS_MENU_KEY, "count": 1},
            {"user_id": 10003, "menu_key": GENERAL_AFFAIRS_MENU_KEY, "count": 1},
        ],
        used_menu_keys={
            10002: {SALES_MENU_KEY, GENERAL_AFFAIRS_MENU_KEY},
            10003: {GENERAL_AFFAIRS_MENU_KEY},
        },
        daily=[
            {"on": date(2026, 8, 1), "count": 1},
            {"on": date(2026, 8, 2), "count": 3},
            {"on": date(2026, 8, 4), "count": 2},
            {"on": date(2026, 8, 5), "count": 1},
        ],
        exports=[
            {
                "used_at": datetime(2026, 8, 2, 10, 16, tzinfo=JST),
                "user_id": 10002,
                "username": "general_user",
                "display_name": "一般 太郎",
                "menu_key": SALES_MENU_KEY,
            },
            {
                "used_at": datetime(2026, 8, 5, 23, 59, 59, 999000, tzinfo=JST),
                "user_id": None,
                "username": "",
                "display_name": "",
                "menu_key": SALES_MENU_KEY,
            },
        ],
        approved_users=[
            {
                "user_id": 10001,
                "username": "admin_user",
                "display_name": "管理 太郎",
                "role": "管理者",
                "is_active": True,
                "last_login": datetime(2026, 8, 27, 8, 30, tzinfo=JST),
            },
            {
                "user_id": 10002,
                "username": "general_user",
                "display_name": "一般 太郎",
                "role": "一般",
                "is_active": True,
                "last_login": datetime(2026, 8, 26, 8, 31, tzinfo=JST),
            },
            {
                "user_id": 10003,
                "username": "dormant_user",
                "display_name": "休眠 太郎",
                "role": "一般",
                "is_active": True,
                "last_login": datetime(2026, 7, 1, 8, 0, tzinfo=JST),
            },
            {
                "user_id": 10004,
                "username": "never_login_user",
                "display_name": "未ログイン 太郎",
                "role": "一般",
                "is_active": True,
                "last_login": None,
            },
            {
                "user_id": 10005,
                "username": "inactive_user",
                "display_name": "無効 太郎",
                "role": "一般",
                "is_active": False,
                "last_login": datetime(2026, 8, 20, 8, 0, tzinfo=JST),
            },
        ],
        grants=[
            {
                "user_id": 10002,
                "username": "general_user",
                "display_name": "一般 太郎",
                "group_key": "sales",
                "granted_on": date(2026, 5, 1),
            },
            {
                "user_id": 10002,
                "username": "general_user",
                "display_name": "一般 太郎",
                "group_key": "management",
                "granted_on": date(2026, 5, 1),
            },
            {
                "user_id": 10003,
                "username": "dormant_user",
                "display_name": "休眠 太郎",
                "group_key": "sales",
                "granted_on": date(2026, 5, 1),
            },
        ],
    )


def build_usecase(repository: FakeUsageStatusRepository) -> UsageStatus:
    return UsageStatus(repository, tzinfo=JST)


# --- page_context -----------------------------------------------------------


def test_page_context_builds_all_sections():
    """TC-APP-010: 6 つの表示要素がすべて揃う。"""
    context = build_usecase(sample_repository()).page_context(today=TODAY)

    assert context["summary"].usage_count == 6
    assert context["summary"].export_count == 2
    assert context["summary"].active_user_count == 2
    assert not context["menu_usage_rows"].is_empty
    assert not context["user_usage_rows"].is_empty
    assert not context["unused_grant_rows"].is_empty
    assert not context["export_log_rows"].is_empty
    assert not context["daily_trend"].is_empty


def test_page_context_passes_aware_datetime_range():
    """TC-APP-011: リポジトリに渡す集計期間が aware な datetime である。"""
    repository = sample_repository()
    build_usecase(repository).page_context(start="2026-08-01", end="2026-08-27", today=TODAY)

    ranges = [kwargs for _, kwargs in repository.calls if "start_at" in kwargs]
    assert ranges
    for kwargs in ranges:
        assert kwargs["start_at"].tzinfo is not None
        assert kwargs["end_at"].tzinfo is not None
        assert kwargs["start_at"] == datetime(2026, 8, 1, 0, 0, tzinfo=JST)
        assert kwargs["end_at"] == datetime(2026, 8, 28, 0, 0, tzinfo=JST)


def test_page_context_returns_error_message_for_invalid_period():
    """TC-APP-012: 期間が不正ならエラー文言を返し、リポジトリを 1 度も呼ばない。"""
    repository = sample_repository()
    context = build_usecase(repository).page_context(
        start="2026-08-28", end="2026-08-27", today=TODAY
    )

    assert context["error_message"] == MESSAGE_OUT_OF_ORDER
    assert context["menu_usage_rows"].is_empty
    assert context["user_usage_rows"].is_empty
    assert context["unused_grant_rows"].is_empty
    assert context["export_log_rows"].is_empty
    assert repository.calls == []


def test_page_context_returns_zero_summary_without_logs():
    """TC-APP-013: ログが 0 件なら全体集計は 0、各一覧は「該当なし」。"""
    context = build_usecase(FakeUsageStatusRepository()).page_context(today=TODAY)

    summary = context["summary"]
    assert summary.usage_count == 0
    assert summary.export_count == 0
    assert summary.active_user_count == 0
    assert summary.unused_user_count == 0
    assert summary.dormant_user_count == 0
    assert context["user_usage_rows"].is_empty
    assert context["unused_grant_rows"].is_empty
    assert context["export_log_rows"].is_empty


def test_page_context_filters_rows_by_menu_group():
    """TC-APP-014: メニューグループで絞り込むと該当グループの行だけになる。"""
    context = build_usecase(sample_repository()).page_context(group_key="sales", today=TODAY)

    menu_rows = context["menu_usage_rows"].rows
    assert menu_rows
    assert {row.group_title for row in menu_rows} == {"営業"}

    user_rows = context["user_usage_rows"].rows
    assert {row.username for row in user_rows} == {"general_user", "dormant_user"}
    for row in user_rows:
        assert "営業" in row.menu_group_titles.split(GROUP_TITLE_SEPARATOR)

    grant_rows = context["unused_grant_rows"].rows
    assert grant_rows
    assert {row.group_title for row in grant_rows} == {"営業"}


def test_page_context_applies_sort_specs():
    """TC-APP-015: 並び替えの指定が一覧に反映される。"""
    context = build_usecase(sample_repository()).page_context(
        sort_key="usage_count", sort_direction="desc", today=TODAY
    )

    counts = [row.usage_count for row in context["user_usage_rows"].rows]
    assert counts == sorted(counts, reverse=True)
    assert counts[0] == 4


def test_page_context_uses_given_today():
    """TC-APP-016: 既定の集計期間は与えられた当日から算出する。"""
    context = build_usecase(sample_repository()).page_context(today=date(2026, 1, 15))

    period = context["period"]
    assert period.start_date == date(2025, 12, 17)
    assert period.end_date == date(2026, 1, 15)


def test_page_context_always_includes_purpose_note():
    """TC-APP-022: 利用目的の注記はエラー時も含まれる。"""
    usecase = build_usecase(sample_repository())

    normal = usecase.page_context(today=TODAY)
    invalid = usecase.page_context(start="2026-08-28", end="2026-08-27", today=TODAY)

    assert normal["purpose_note"] == USAGE_STATUS_PURPOSE_NOTE
    assert invalid["purpose_note"] == USAGE_STATUS_PURPOSE_NOTE


def _repository_with_users(count: int) -> FakeUsageStatusRepository:
    return FakeUsageStatusRepository(
        approved_users=[
            {
                "user_id": 20000 + index,
                "username": f"user{index:02d}",
                "display_name": f"利用者{index:02d}",
                "role": "一般",
                "is_active": True,
                "last_login": None,
            }
            for index in range(1, count + 1)
        ]
    )


def test_page_context_paginates_rows_with_shared_kernel():
    """TC-APP-023: 共有カーネルのページングをそのまま使う。"""
    context = build_usecase(_repository_with_users(25)).page_context(
        page=2, page_size=10, today=TODAY
    )

    page = context["user_usage_page"]
    assert [row.username for row in page.rows] == [f"user{index:02d}" for index in range(11, 21)]
    assert page.total_count == 25
    assert page.total_pages == 3
    assert page.page == 2


def test_page_context_returns_first_page_by_default():
    """TC-APP-024: 既定では 1 ページ目を返し、総ページ数を含む。"""
    context = build_usecase(_repository_with_users(25)).page_context(today=TODAY)

    page = context["user_usage_page"]
    assert page.page == 1
    assert page.total_pages == 1
    assert page.total_count == 25


def test_page_context_clamps_page_beyond_last_page():
    """TC-APP-025: 最終ページを超える指定は最終ページに丸める。"""
    context = build_usecase(_repository_with_users(5)).page_context(page=99, today=TODAY)

    page = context["user_usage_page"]
    assert page.page == page.total_pages
    assert len(page.rows) == 5


def test_page_context_exposes_sort_labels_by_section():
    """並び替えダイアログ用のラベルが区分ごとに載る（REQ-NF-007）。"""
    context = build_usecase(sample_repository()).page_context(today=TODAY)

    assert context["sort_labels"]["menus"] == MENU_USAGE_SORT_LABELS
    assert context["sort_labels"]["users"] == USER_USAGE_SORT_LABELS
    assert context["sort_labels"]["unused-grants"] == UNUSED_GRANT_SORT_LABELS
    assert context["sort_labels"]["exports"] == EXPORT_LOG_SORT_LABELS


# --- csv_payload ------------------------------------------------------------


@pytest.mark.parametrize(
    ("section", "labels"),
    [
        ("menus", MENU_USAGE_SORT_LABELS),
        ("users", USER_USAGE_SORT_LABELS),
        ("unused-grants", UNUSED_GRANT_SORT_LABELS),
        ("exports", EXPORT_LOG_SORT_LABELS),
    ],
)
def test_csv_payload_returns_rows_for_each_section(section, labels):
    """TC-APP-017: 区分ごとにヘッダ行が一致する。"""
    payload = build_usecase(sample_repository()).csv_payload(section=section, today=TODAY)

    assert payload.error_message is None
    assert payload.rows is not None
    assert payload.rows[0] == list(labels.values())


def test_csv_payload_rejects_unknown_section():
    """TC-APP-018: 未知の区分は出力せずエラー文言を返す。"""
    payload = build_usecase(sample_repository()).csv_payload(section="unknown", today=TODAY)

    assert payload.rows is None
    assert payload.error_message


def _repository_with_exports(count: int) -> FakeUsageStatusRepository:
    base = datetime(2026, 8, 1, 0, 0, tzinfo=JST)
    return FakeUsageStatusRepository(
        exports=[
            {
                "used_at": base + timedelta(seconds=index),
                "user_id": 10002,
                "username": "general_user",
                "display_name": "一般 太郎",
                "menu_key": SALES_MENU_KEY,
            }
            for index in range(count)
        ]
    )


def test_csv_payload_allows_row_limit_exactly():
    """TC-APP-019: 上限ちょうどは出力できる。"""
    repository = _repository_with_exports(USAGE_STATUS_CSV_ROW_LIMIT)
    payload = build_usecase(repository).csv_payload(section="exports", today=TODAY)

    assert payload.error_message is None
    assert payload.rows is not None
    assert len(payload.rows) == USAGE_STATUS_CSV_ROW_LIMIT + 1


def test_csv_payload_rejects_rows_over_limit():
    """TC-APP-020: 上限を 1 行超えると出力しない。"""
    repository = _repository_with_exports(USAGE_STATUS_CSV_ROW_LIMIT + 1)
    payload = build_usecase(repository).csv_payload(section="exports", today=TODAY)

    assert payload.rows is None
    assert "10 万行" in payload.error_message


def test_csv_payload_rejects_invalid_period():
    """TC-APP-021: 期間が不正なら出力せずエラー文言を返す。"""
    payload = build_usecase(sample_repository()).csv_payload(
        section="menus", start="2026-08-28", end="2026-08-27", today=TODAY
    )

    assert payload.rows is None
    assert payload.error_message == MESSAGE_OUT_OF_ORDER
