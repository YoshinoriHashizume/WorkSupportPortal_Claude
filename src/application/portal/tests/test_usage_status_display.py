"""利用状況の行 VO・集計関数（画面側 domain）のテスト。

対応: test-design.md TC-DOM-070〜082・TC-DOM-090〜104
"""

from __future__ import annotations

import dataclasses
from datetime import date, datetime

import pytest

from application.portal.domain.value_objects.usage_period import AggregationPeriod
from application.portal.domain.value_objects.usage_status_display import (
    EXPORT_LOG_SORT_LABELS,
    MENU_USAGE_SORT_LABELS,
    USAGE_STATUS_CSV_ROW_LIMIT,
    USAGE_STATUS_PURPOSE_NOTE,
    DailyUsageTrend,
    ExportLogRow,
    ExportLogRows,
    MenuGroupGrantEntry,
    MenuUsageRow,
    MenuUsageRows,
    UsageSummary,
    UserAggregationEntry,
    UserUsageRow,
    UserUsageRows,
    aggregation_target_menu_keys,
    build_daily_trend,
    dormant_user_count,
    is_retired_menu,
    menu_display_title,
    menu_group_title,
    most_used_menu_key,
    unused_menu_group_grant_rows,
    unused_user_count,
)
from application.shared.domain.value_objects.list_table import SortSpec


def _menu_usage_row(
    *,
    group_title: str = "管理",
    menu_title: str = "お知らせ",
    view_count: int = 1,
    export_count: int = 0,
    user_count: int = 1,
    last_used_on: date | None = date(2026, 8, 20),
    is_retired: bool = False,
) -> MenuUsageRow:
    return MenuUsageRow(
        group_title=group_title,
        menu_title=menu_title,
        view_count=view_count,
        export_count=export_count,
        user_count=user_count,
        last_used_on=last_used_on,
        is_retired=is_retired,
    )


def _user_usage_row(
    *,
    username: str = "1001",
    display_name: str = "山田 太郎",
    role: str = "一般ユーザー",
    menu_group_titles: str = "管理",
    usage_count: int = 3,
    export_count: int = 1,
    most_used_menu_title: str = "お知らせ",
    last_used_on: date | None = date(2026, 8, 26),
    last_login_at: datetime | None = None,
) -> UserUsageRow:
    return UserUsageRow(
        username=username,
        display_name=display_name,
        role=role,
        menu_group_titles=menu_group_titles,
        usage_count=usage_count,
        export_count=export_count,
        most_used_menu_title=most_used_menu_title,
        last_used_on=last_used_on,
        last_login_at=last_login_at,
    )


def _approved_active_entry(user_id: int, last_login_at: datetime | None = None) -> UserAggregationEntry:
    return UserAggregationEntry(
        user_id=user_id,
        is_approved=True,
        is_active=True,
        last_login_at=last_login_at,
    )


# --- TC-DOM-070〜082: 行 VO とファーストクラスコレクション -------------------


def test_usage_summary_keeps_given_counts():
    """TC-DOM-070: 全体集計の 5 つの数がそのまま保持される。"""
    summary = UsageSummary(
        active_user_count=3,
        usage_count=120,
        export_count=5,
        unused_user_count=2,
        dormant_user_count=1,
    )

    assert summary.active_user_count == 3
    assert summary.usage_count == 120
    assert summary.export_count == 5
    assert summary.unused_user_count == 2
    assert summary.dormant_user_count == 1


def test_usage_summary_is_immutable():
    """TC-DOM-071: 全体集計は生成後に変更できない。"""
    summary = UsageSummary(
        active_user_count=3,
        usage_count=120,
        export_count=5,
        unused_user_count=2,
        dormant_user_count=1,
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        summary.usage_count = 999


def test_menu_usage_rows_is_empty_without_row():
    """TC-DOM-072: 0 行のメニュー別一覧は「該当なし」。"""
    assert MenuUsageRows([]).is_empty is True


def test_menu_usage_rows_is_not_empty_with_one_row():
    """TC-DOM-073: 1 行あれば「該当なし」ではない。"""
    assert MenuUsageRows([_menu_usage_row()]).is_empty is False


def test_menu_usage_rows_sorted_by_returns_new_collection():
    """TC-DOM-074: 並び替えは新しいコレクションを返し、元は変化しない。"""
    rows = MenuUsageRows(
        [
            _menu_usage_row(menu_title="お知らせ", view_count=2),
            _menu_usage_row(menu_title="ユーザー管理", view_count=9),
            _menu_usage_row(menu_title="データベース", view_count=5),
        ]
    )

    sorted_rows = rows.sorted_by((SortSpec(column="view_count", direction="desc"),))

    assert [row.view_count for row in sorted_rows.rows] == [9, 5, 2]
    assert [row.view_count for row in rows.rows] == [2, 9, 5]
    assert sorted_rows is not rows


def test_menu_usage_rows_filtered_by_group_keeps_matching_rows():
    """TC-DOM-075: メニューグループでの絞り込みは一致する行だけを残す。"""
    rows = MenuUsageRows(
        [
            _menu_usage_row(group_title="管理", menu_title="お知らせ"),
            _menu_usage_row(group_title="営業", menu_title="出荷トレンド一覧"),
            _menu_usage_row(group_title="管理", menu_title="ユーザー管理"),
            _menu_usage_row(group_title="営業", menu_title="出荷トレンド一覧（旧）"),
        ]
    )

    filtered = rows.filtered_by_group("sales")

    assert [row.menu_title for row in filtered.rows] == ["出荷トレンド一覧", "出荷トレンド一覧（旧）"]
    assert len(rows.rows) == 4


def test_menu_usage_rows_filtered_by_blank_group_keeps_all_rows():
    """TC-DOM-076: メニューグループを指定しなければ全行を残す。"""
    rows = MenuUsageRows(
        [
            _menu_usage_row(group_title="管理", menu_title="お知らせ"),
            _menu_usage_row(group_title="営業", menu_title="出荷トレンド一覧"),
            _menu_usage_row(group_title="管理", menu_title="ユーザー管理"),
            _menu_usage_row(group_title="営業", menu_title="出荷トレンド一覧（旧）"),
        ]
    )

    assert len(rows.filtered_by_group("").rows) == 4


def test_menu_usage_rows_csv_rows_start_with_header():
    """TC-DOM-077: CSV 行はヘッダ行で始まり、すべて文字列である。"""
    rows = MenuUsageRows(
        [
            _menu_usage_row(menu_title="お知らせ", view_count=2),
            _menu_usage_row(menu_title="ユーザー管理", view_count=9),
        ]
    )

    csv_rows = rows.csv_rows()

    assert csv_rows[0] == list(MENU_USAGE_SORT_LABELS.values())
    assert len(csv_rows) == 3
    assert all(isinstance(value, str) for row in csv_rows for value in row)


def test_user_usage_rows_csv_rows_format_last_login_at():
    """TC-DOM-078: 最終ログイン日時は yyyy/mm/dd hh:mm で出力される。"""
    rows = UserUsageRows([_user_usage_row(last_login_at=datetime(2026, 8, 26, 8, 31))])

    assert "2026/08/26 08:31" in rows.csv_rows()[1]


def test_export_log_rows_are_sorted_by_used_at_desc():
    """TC-DOM-079: 出力ログは既定で日時の降順に並ぶ。"""
    rows = ExportLogRows(
        [
            ExportLogRow(
                used_at=datetime(2026, 8, 20, 10, 0),
                username="1001",
                display_name="山田 太郎",
                group_title="営業",
                menu_title="出荷トレンド一覧",
            ),
            ExportLogRow(
                used_at=datetime(2026, 8, 27, 9, 5),
                username="1002",
                display_name="鈴木 花子",
                group_title="総務",
                menu_title="資産棚卸結果",
            ),
            ExportLogRow(
                used_at=datetime(2026, 8, 25, 18, 42),
                username="1003",
                display_name="佐藤 次郎",
                group_title="生産管理",
                menu_title="在庫発注アラート",
            ),
        ]
    )

    assert [row.used_at for row in rows.rows] == [
        datetime(2026, 8, 27, 9, 5),
        datetime(2026, 8, 25, 18, 42),
        datetime(2026, 8, 20, 10, 0),
    ]
    csv_rows = rows.csv_rows()
    assert csv_rows[0] == list(EXPORT_LOG_SORT_LABELS.values())
    assert csv_rows[1][0] == "2026/08/27 09:05"


def test_unused_grant_rows_subtract_used_groups():
    """TC-DOM-080: 未利用のメニューグループ付与は付与から利用を差し引いた差分。"""
    grants = [
        MenuGroupGrantEntry(
            user_id=1,
            username="1001",
            display_name="山田 太郎",
            group_key="management",
            granted_on=date(2026, 5, 1),
        ),
        MenuGroupGrantEntry(
            user_id=1,
            username="1001",
            display_name="山田 太郎",
            group_key="sales",
            granted_on=date(2026, 5, 1),
        ),
        MenuGroupGrantEntry(
            user_id=2,
            username="1002",
            display_name="鈴木 花子",
            group_key="sales",
            granted_on=date(2026, 6, 1),
        ),
    ]

    rows = unused_menu_group_grant_rows(grants, used_group_keys_by_user={1: {"sales"}})

    assert [(row.username, row.group_title) for row in rows.rows] == [
        ("1001", "管理"),
        ("1002", "営業"),
    ]


def test_unused_grant_rows_is_empty_when_all_used():
    """TC-DOM-081: 付与されたメニューグループをすべて利用していれば行はない。"""
    grants = [
        MenuGroupGrantEntry(
            user_id=1,
            username="1001",
            display_name="山田 太郎",
            group_key="management",
            granted_on=date(2026, 5, 1),
        ),
        MenuGroupGrantEntry(
            user_id=2,
            username="1002",
            display_name="鈴木 花子",
            group_key="sales",
            granted_on=date(2026, 6, 1),
        ),
    ]

    rows = unused_menu_group_grant_rows(
        grants,
        used_group_keys_by_user={1: {"management"}, 2: {"sales"}},
    )

    assert rows.is_empty is True


def test_unused_grant_rows_keep_granted_on():
    """TC-DOM-082: 付与日はそのまま行に保持される。"""
    grants = [
        MenuGroupGrantEntry(
            user_id=1,
            username="1001",
            display_name="山田 太郎",
            group_key="management",
            granted_on=date(2026, 5, 1),
        )
    ]

    rows = unused_menu_group_grant_rows(grants, used_group_keys_by_user={})

    assert rows.rows[0].granted_on == date(2026, 5, 1)


# --- TC-DOM-090〜104: 集計関数と定数 ----------------------------------------


def test_most_used_menu_key_returns_top_menu():
    """TC-DOM-090: 最多利用メニューは利用回数が最も多いメニュー。"""
    assert most_used_menu_key([("a", 3), ("b", 5), ("c", 1)]) == "b"


def test_most_used_menu_key_breaks_tie_by_menu_key_asc():
    """TC-DOM-091: 同数の場合はメニューキーの昇順で先頭を採る。"""
    assert most_used_menu_key([("shipment-trend-list", 4), ("asset-inventory", 4)]) == "asset-inventory"


def test_most_used_menu_key_returns_none_without_usage():
    """TC-DOM-092: 利用がなければ最多利用メニューは None。"""
    assert most_used_menu_key([]) is None


def test_build_daily_trend_fills_missing_days_with_zero():
    """TC-DOM-093: 日別推移は実績のない日を 0 で埋める。"""
    period = AggregationPeriod(start_date=date(2026, 8, 1), end_date=date(2026, 8, 5))

    trend = build_daily_trend({date(2026, 8, 2): 3}, period)

    assert [(point.on, point.count) for point in trend.points] == [
        (date(2026, 8, 1), 0),
        (date(2026, 8, 2), 3),
        (date(2026, 8, 3), 0),
        (date(2026, 8, 4), 0),
        (date(2026, 8, 5), 0),
    ]


def test_build_daily_trend_returns_all_zero_without_usage():
    """TC-DOM-094: 実績が 0 件でも期間日数ぶんの点を返す。"""
    period = AggregationPeriod(start_date=date(2026, 8, 1), end_date=date(2026, 8, 5))

    trend = build_daily_trend({}, period)

    assert isinstance(trend, DailyUsageTrend)
    assert len(trend.points) == 5
    assert all(point.count == 0 for point in trend.points)


def test_build_daily_trend_returns_single_point_for_one_day_period():
    """TC-DOM-095: 1 日の期間なら点は 1 つ。"""
    period = AggregationPeriod(start_date=date(2026, 8, 5), end_date=date(2026, 8, 5))

    trend = build_daily_trend({date(2026, 8, 5): 7}, period)

    assert [(point.on, point.count) for point in trend.points] == [(date(2026, 8, 5), 7)]


def test_build_daily_trend_excludes_counts_outside_period():
    """TC-DOM-096: 集計期間外の実績は日別推移に含めない。"""
    period = AggregationPeriod(start_date=date(2026, 8, 1), end_date=date(2026, 8, 5))

    trend = build_daily_trend(
        {
            date(2026, 7, 31): 4,
            date(2026, 8, 3): 2,
            date(2026, 8, 6): 6,
        },
        period,
    )

    assert len(trend.points) == 5
    assert [point.count for point in trend.points] == [0, 0, 2, 0, 0]


def test_unused_user_count_counts_approved_active_users_only():
    """TC-DOM-097: 未利用ユーザー数の母集団は許可済みかつ有効なユーザー。"""
    entries = [_approved_active_entry(user_id) for user_id in (1, 2, 3, 4, 5)]
    entries += [
        UserAggregationEntry(user_id=user_id, is_approved=True, is_active=False, last_login_at=None)
        for user_id in (6, 7)
    ]
    entries += [
        UserAggregationEntry(user_id=user_id, is_approved=False, is_active=True, last_login_at=None)
        for user_id in (8, 9, 10)
    ]

    assert unused_user_count(entries, used_user_ids={1, 2}) == 3


def test_dormant_user_count_counts_last_login_before_start_date():
    """TC-DOM-098: 休眠ユーザーは最終ログインが集計期間の開始日より前のユーザー。"""
    period = AggregationPeriod(start_date=date(2026, 8, 1), end_date=date(2026, 8, 27))
    entries = [
        _approved_active_entry(1, datetime(2026, 7, 31, 17, 0)),
        _approved_active_entry(2, datetime(2026, 8, 1, 9, 0)),
        _approved_active_entry(3, datetime(2026, 8, 15, 13, 0)),
    ]

    assert dormant_user_count(entries, period) == 1


def test_dormant_user_count_includes_never_logged_in_user():
    """TC-DOM-099: 一度もログインしていないユーザーも休眠に含める。"""
    period = AggregationPeriod(start_date=date(2026, 8, 1), end_date=date(2026, 8, 27))

    assert dormant_user_count([_approved_active_entry(1, None)], period) == 1


def test_menu_display_title_returns_title_for_known_key():
    """TC-DOM-100: 現行定義にあるメニューキーは表示名を返す。"""
    assert menu_display_title("shipment-trend-list") == "出荷トレンド一覧"
    assert is_retired_menu("shipment-trend-list") is False
    assert menu_group_title("shipment-trend-list") == "営業"


def test_menu_display_title_marks_retired_for_unknown_key():
    """TC-DOM-101: 現行定義に無いメニューキーは廃止として表示する。"""
    assert menu_display_title("legacy-report") == "legacy-report（廃止）"
    assert is_retired_menu("legacy-report") is True
    assert menu_group_title("legacy-report") == "—"


def test_aggregation_target_menu_keys_exclude_parent_without_href():
    """TC-DOM-102: 遷移先を持たない親メニューは集計対象に含めない。"""
    keys = aggregation_target_menu_keys()

    assert "receipt-comparison" not in keys
    assert "usage-status" in keys
    assert "receipt-comparison-finished-product" in keys


def test_usage_status_csv_row_limit_is_100000():
    """TC-DOM-103: CSV 出力の上限行数は 100,000 行。"""
    assert USAGE_STATUS_CSV_ROW_LIMIT == 100_000


def test_usage_status_purpose_note_denies_performance_review():
    """TC-DOM-104: 利用目的の注記は勤務評価に用いないことを明示する。"""
    assert "勤務評価には用いません" in USAGE_STATUS_PURPOSE_NOTE
