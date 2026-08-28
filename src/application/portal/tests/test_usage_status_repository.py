"""メニュー利用ログの記録リポジトリ・集計リポジトリのテスト。"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import DataError, transaction
from django.utils import timezone

from application.portal.domain.value_objects.constants import (
    ADMIN_GROUP_NAME,
    GENERAL_USER_GROUP_NAME,
)
from application.portal.infrastructure.persistence.menu_usage_log_repository import (
    DjangoMenuUsageLogRepository,
)
from application.portal.infrastructure.persistence.usage_status_repository import (
    DjangoUsageStatusRepository,
)
from application.portal.models import MenuUsageLog, PortalMenuGroupAccess, UserAccessRequest


@pytest.fixture
def repository():
    return DjangoMenuUsageLogRepository()


@pytest.fixture
def user():
    return get_user_model().objects.create_user(username="10001", password="pass-10001")


@pytest.mark.django_db
def test_record_saves_single_row(repository, user):
    """1 回の記録で 1 行だけ保存され、利用日時に現在時刻が入る。"""
    before = timezone.now()

    repository.record(user=user, menu_key="shipment-trend-list", usage_type="VIEW")

    logs = list(MenuUsageLog.objects.all())
    assert len(logs) == 1
    log = logs[0]
    assert log.user_id == user.pk
    assert log.menu_key == "shipment-trend-list"
    assert log.usage_type == "VIEW"
    assert log.used_at.utcoffset() is not None
    assert before <= log.used_at <= timezone.now() + timedelta(seconds=1)


@pytest.mark.django_db
def test_record_stores_only_four_columns(repository, user):
    """保存する項目は利用者・メニューキー・利用種別・利用日時の4つに限られる。"""
    repository.record(user=user, menu_key="asset-inventory", usage_type="EXPORT")

    field_names = {field.name for field in MenuUsageLog._meta.get_fields()}

    assert field_names == {"id", "user", "menu_key", "usage_type", "used_at"}


@pytest.mark.django_db
def test_record_keeps_log_with_null_user_after_user_delete(repository, user):
    """利用者を削除してもメニュー利用ログは残り、利用者は空になる。"""
    repository.record(user=user, menu_key="usage-status", usage_type="VIEW")

    user.delete()

    logs = list(MenuUsageLog.objects.all())
    assert len(logs) == 1
    assert logs[0].user_id is None


@pytest.mark.django_db
def test_record_allows_repeated_rows_for_same_user(repository, user):
    """同じ利用者が同じメニューを繰り返し利用しても、その都度記録される。"""
    for _ in range(3):
        repository.record(user=user, menu_key="usage-status", usage_type="VIEW")

    assert MenuUsageLog.objects.count() == 3


def test_menu_usage_log_repository_has_no_update_or_delete():
    """記録リポジトリは更新・削除の手段を公開しない。"""
    prefixes = ("update", "delete", "remove", "set_")
    public = [name for name in dir(DjangoMenuUsageLogRepository) if not name.startswith("_")]

    assert public == ["record"]
    assert [name for name in public if name.startswith(prefixes)] == []


@pytest.mark.django_db
def test_record_stores_menu_key_up_to_max_length(repository, user):
    """メニューキーは80文字まで保存でき、81文字と空文字は保存しない。"""
    repository.record(user=user, menu_key="a" * 80, usage_type="VIEW")
    assert MenuUsageLog.objects.filter(menu_key="a" * 80).count() == 1

    # DataError でトランザクションが壊れるため、独立したブロックに閉じる
    with pytest.raises(DataError), transaction.atomic():
        repository.record(user=user, menu_key="a" * 81, usage_type="VIEW")

    repository.record(user=user, menu_key="", usage_type="VIEW")
    assert MenuUsageLog.objects.filter(menu_key="").count() == 0


# ---------------------------------------------------------------------------
# 集計リポジトリ（DjangoUsageStatusRepository）: TC-INF-010〜028
# test-design.md §3.1 の正常系テストデータを 1 セットの fixture として用意する。
# ---------------------------------------------------------------------------

JST = ZoneInfo("Asia/Tokyo")

# 集計期間 2026-08-01 〜 2026-08-05（design.md §5.3 の半開区間）
PERIOD_START_AT = datetime(2026, 8, 1, 0, 0, 0, tzinfo=JST)
PERIOD_END_AT = datetime(2026, 8, 6, 0, 0, 0, tzinfo=JST)


def _jst(year, month, day, hour=0, minute=0, second=0, microsecond=0):
    return datetime(year, month, day, hour, minute, second, microsecond, tzinfo=JST)


@pytest.fixture
def usage_repository():
    return DjangoUsageStatusRepository()


def _create_user(
    username,
    *,
    role=GENERAL_USER_GROUP_NAME,
    access_status=UserAccessRequest.Status.APPROVED,
    is_active=True,
    last_login=None,
    last_name="",
    first_name="",
):
    """利用申請・役割・有効／無効・最終ログイン日時を備えたユーザーを作る。"""
    user = get_user_model().objects.create_user(
        username=username,
        password=f"pass-{username}",
        last_name=last_name,
        first_name=first_name,
        is_active=is_active,
    )
    user.last_login = last_login
    user.save(update_fields=["last_login"])
    group, _ = Group.objects.get_or_create(name=role)
    user.groups.add(group)
    UserAccessRequest.objects.create(user=user, status=access_status)
    return user


def _grant(user, group_key, granted_at):
    """メニューグループの付与を、付与日を指定して作る（created_at は auto_now_add のため更新する）。"""
    access = PortalMenuGroupAccess.objects.create(user=user, group_key=group_key)
    PortalMenuGroupAccess.objects.filter(pk=access.pk).update(created_at=granted_at)
    return access


def _log(*, user, menu_key, usage_type, used_at):
    return MenuUsageLog.objects.create(
        user=user, menu_key=menu_key, usage_type=usage_type, used_at=used_at
    )


@pytest.fixture
def usage_dataset():
    """test-design.md §3.1 のユーザー・メニューグループ付与・メニュー利用ログ 8 件。"""
    admin_user = _create_user(
        "10001",
        role=ADMIN_GROUP_NAME,
        last_login=_jst(2026, 8, 27, 8, 30),
        last_name="管理",
        first_name="太郎",
    )
    general_user = _create_user(
        "10002",
        last_login=_jst(2026, 8, 26, 8, 31),
        last_name="一般",
        first_name="花子",
    )
    dormant_user = _create_user(
        "10003",
        last_login=_jst(2026, 7, 1, 8, 0),
        last_name="休眠",
        first_name="次郎",
    )
    never_login_user = _create_user("10004", last_name="未login", first_name="三郎")
    inactive_user = _create_user(
        "10005",
        is_active=False,
        last_login=_jst(2026, 8, 20, 8, 0),
        last_name="無効",
        first_name="四郎",
    )
    pending_user = _create_user(
        "10006",
        access_status=UserAccessRequest.Status.PENDING,
        last_name="申請",
        first_name="五郎",
    )

    _grant(general_user, "sales", _jst(2026, 5, 1, 9, 0))
    _grant(general_user, "management", _jst(2026, 5, 1, 9, 0))
    _grant(dormant_user, "sales", _jst(2026, 5, 1, 9, 0))

    _log(
        user=general_user,
        menu_key="shipment-trend-list",
        usage_type="VIEW",
        used_at=_jst(2026, 8, 1, 0, 0, 0),
    )
    _log(
        user=general_user,
        menu_key="shipment-trend-list",
        usage_type="VIEW",
        used_at=_jst(2026, 8, 2, 10, 15),
    )
    _log(
        user=general_user,
        menu_key="shipment-trend-list",
        usage_type="EXPORT",
        used_at=_jst(2026, 8, 2, 10, 16),
    )
    _log(
        user=general_user,
        menu_key="asset-inventory",
        usage_type="VIEW",
        used_at=_jst(2026, 8, 2, 11, 0),
    )
    _log(
        user=dormant_user,
        menu_key="asset-inventory",
        usage_type="VIEW",
        used_at=_jst(2026, 8, 4, 9, 0),
    )
    _log(
        user=None,
        menu_key="shipment-trend-list",
        usage_type="EXPORT",
        used_at=_jst(2026, 8, 5, 23, 59, 59, 999000),
    )
    _log(
        user=general_user,
        menu_key="shipment-trend-list",
        usage_type="VIEW",
        used_at=_jst(2026, 7, 31, 23, 59, 59),
    )
    _log(
        user=general_user,
        menu_key="shipment-trend-list",
        usage_type="VIEW",
        used_at=_jst(2026, 8, 6, 0, 0, 0),
    )

    return {
        "admin_user": admin_user,
        "general_user": general_user,
        "dormant_user": dormant_user,
        "never_login_user": never_login_user,
        "inactive_user": inactive_user,
        "pending_user": pending_user,
    }


@pytest.mark.django_db
def test_overall_counts_include_logs_in_period_only(usage_repository, usage_dataset):
    """全体集計は集計期間内のログだけを数える（TC-INF-010）。"""
    counts = usage_repository.overall_counts(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT)

    assert counts["usage_count"] == 6
    assert counts["export_count"] == 2
    # 利用ユーザー数（V-604）はログを持つユーザーの実数。user_id が NULL の行は数えない
    assert counts["active_user_count"] == 2


@pytest.mark.django_db
def test_period_includes_start_date_midnight(usage_repository, usage_dataset):
    """開始日の 00:00:00 ちょうどのログは集計期間に含まれる（TC-INF-011）。"""
    counts = usage_repository.overall_counts(
        start_at=PERIOD_START_AT, end_at=_jst(2026, 8, 2, 0, 0, 0)
    )

    assert counts["usage_count"] == 1


@pytest.mark.django_db
def test_period_includes_end_date_last_moment(usage_repository, usage_dataset):
    """終了日 23:59:59.999 のログは集計期間に含まれる（TC-INF-012）。"""
    counts = usage_repository.overall_counts(
        start_at=_jst(2026, 8, 5, 0, 0, 0), end_at=PERIOD_END_AT
    )

    assert counts["usage_count"] == 1
    assert counts["export_count"] == 1


@pytest.mark.django_db
def test_period_excludes_moment_before_start_date(usage_repository, usage_dataset):
    """開始日の前日 23:59:59 のログは集計期間に含まれない（TC-INF-013）。"""
    counts = usage_repository.overall_counts(
        start_at=PERIOD_START_AT, end_at=_jst(2026, 8, 2, 0, 0, 0)
    )
    all_counts = usage_repository.overall_counts(
        start_at=_jst(2026, 7, 31, 0, 0, 0), end_at=_jst(2026, 8, 2, 0, 0, 0)
    )

    assert counts["usage_count"] == 1
    assert all_counts["usage_count"] == 2


@pytest.mark.django_db
def test_period_excludes_next_day_midnight(usage_repository, usage_dataset):
    """終了日の翌日 00:00:00 のログは集計期間に含まれない（TC-INF-014）。"""
    counts = usage_repository.overall_counts(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT)
    extended = usage_repository.overall_counts(
        start_at=PERIOD_START_AT, end_at=_jst(2026, 8, 7, 0, 0, 0)
    )

    assert counts["usage_count"] == 6
    assert extended["usage_count"] == 7


@pytest.mark.django_db
def test_period_uses_asia_tokyo_date_for_utc_rows(usage_repository):
    """UTC で保存された行も Asia/Tokyo の日付で集計期間に含まれる（TC-INF-015）。"""
    user = _create_user("10002")
    _log(
        user=user,
        menu_key="shipment-trend-list",
        usage_type="VIEW",
        used_at=datetime(2026, 8, 4, 16, 0, 0, tzinfo=dt_timezone.utc),
    )

    counts = usage_repository.overall_counts(
        start_at=_jst(2026, 8, 5, 0, 0, 0), end_at=_jst(2026, 8, 6, 0, 0, 0)
    )
    daily = usage_repository.daily_counts(
        start_at=_jst(2026, 8, 5, 0, 0, 0), end_at=_jst(2026, 8, 6, 0, 0, 0)
    )

    assert counts["usage_count"] == 1
    assert [row["on"] for row in daily] == [date(2026, 8, 5)]


@pytest.mark.django_db
def test_menu_counts_split_view_and_export(usage_repository):
    """メニュー別集計は表示回数と出力回数を分けて数え、ユーザー数は重複を除く（TC-INF-016）。"""
    general_user = _create_user("10002")
    dormant_user = _create_user("10003")
    for used_at in (_jst(2026, 8, 2, 10, 0), _jst(2026, 8, 2, 11, 0)):
        _log(
            user=general_user, menu_key="shipment-trend-list", usage_type="VIEW", used_at=used_at
        )
    _log(
        user=dormant_user,
        menu_key="shipment-trend-list",
        usage_type="EXPORT",
        used_at=_jst(2026, 8, 3, 9, 0),
    )

    rows = usage_repository.menu_counts(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT)

    assert len(rows) == 1
    row = rows[0]
    assert row["menu_key"] == "shipment-trend-list"
    assert row["view_count"] == 2
    assert row["export_count"] == 1
    assert row["user_count"] == 2


@pytest.mark.django_db
def test_last_used_at_by_menu_key_returns_latest_of_all_time(usage_repository, usage_dataset):
    """メニューごとの最終利用日時は集計期間外も含めた全期間から求める（TC-INF-017）。"""
    last_used = usage_repository.last_used_at_by_menu_key()

    assert last_used["shipment-trend-list"] == _jst(2026, 8, 6, 0, 0, 0)
    assert last_used["asset-inventory"] == _jst(2026, 8, 4, 9, 0)


@pytest.mark.django_db
def test_last_used_at_by_user_returns_latest_of_all_time(usage_repository, usage_dataset):
    """ユーザーごとの最終利用日時は集計期間外も含めた全期間から求める（TC-INF-018）。"""
    general_user = usage_dataset["general_user"]
    dormant_user = usage_dataset["dormant_user"]

    last_used = usage_repository.last_used_at_by_user()

    assert last_used[general_user.pk] == _jst(2026, 8, 6, 0, 0, 0)
    assert last_used[dormant_user.pk] == _jst(2026, 8, 4, 9, 0)


@pytest.mark.django_db
def test_menu_counts_by_user_returns_counts_per_pair(usage_repository):
    """ユーザー×メニューごとの利用回数を返す。最多の判定は行わない（TC-INF-019）。"""
    user = _create_user("10002")
    for hour in (9, 10, 11):
        _log(
            user=user,
            menu_key="shipment-trend-list",
            usage_type="VIEW",
            used_at=_jst(2026, 8, 2, hour),
        )
    _log(
        user=user, menu_key="asset-inventory", usage_type="VIEW", used_at=_jst(2026, 8, 3, 9, 0)
    )

    rows = usage_repository.menu_counts_by_user(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT)

    counts = {(row["user_id"], row["menu_key"]): row["count"] for row in rows}
    assert counts == {
        (user.pk, "shipment-trend-list"): 3,
        (user.pk, "asset-inventory"): 1,
    }


@pytest.mark.django_db
def test_daily_counts_return_count_per_date(usage_repository):
    """日別の利用回数を返し、0 件の日は返さない（TC-INF-020）。"""
    user = _create_user("10002")
    for hour in (9, 10, 11):
        _log(
            user=user,
            menu_key="shipment-trend-list",
            usage_type="VIEW",
            used_at=_jst(2026, 8, 2, hour),
        )
    _log(
        user=user, menu_key="asset-inventory", usage_type="VIEW", used_at=_jst(2026, 8, 4, 9, 0)
    )

    rows = usage_repository.daily_counts(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT)

    assert [(row["on"], row["count"]) for row in rows] == [
        (date(2026, 8, 2), 3),
        (date(2026, 8, 4), 1),
    ]


@pytest.mark.django_db
def test_export_entries_return_export_rows_only(usage_repository, usage_dataset):
    """出力操作の記録は利用種別 EXPORT のみを利用日時の降順で返す（TC-INF-021）。"""
    general_user = usage_dataset["general_user"]

    rows = usage_repository.export_entries(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT)

    assert len(rows) == 2
    assert [row["used_at"] for row in rows] == [
        _jst(2026, 8, 5, 23, 59, 59, 999000),
        _jst(2026, 8, 2, 10, 16),
    ]
    assert rows[0]["user_id"] is None
    assert rows[1]["user_id"] == general_user.pk
    assert rows[1]["username"] == "10002"
    assert rows[1]["display_name"] == "一般 花子"
    assert rows[1]["menu_key"] == "shipment-trend-list"


@pytest.mark.django_db
def test_approved_user_entries_return_six_fields(usage_repository, usage_dataset):
    """利用申請が許可済みのユーザーだけを 6 項目で返す（TC-INF-022）。"""
    entries = usage_repository.approved_user_entries()

    usernames = sorted(entry["username"] for entry in entries)
    assert usernames == ["10001", "10002", "10003", "10004", "10005"]

    by_username = {entry["username"]: entry for entry in entries}
    assert set(by_username["10002"]) == {
        "user_id",
        "username",
        "display_name",
        "role",
        "is_active",
        "last_login",
    }
    assert by_username["10001"]["role"] == ADMIN_GROUP_NAME
    assert by_username["10002"]["role"] == GENERAL_USER_GROUP_NAME
    assert by_username["10002"]["display_name"] == "一般 花子"
    assert by_username["10002"]["last_login"] == _jst(2026, 8, 26, 8, 31)
    assert by_username["10004"]["last_login"] is None


@pytest.mark.django_db
def test_approved_user_entries_include_inactive_user(usage_repository, usage_dataset):
    """無効化されたユーザーも許可済みなら行に含め、is_active で示す（TC-INF-023）。"""
    entries = {entry["username"]: entry for entry in usage_repository.approved_user_entries()}

    assert entries["10005"]["is_active"] is False
    assert entries["10002"]["is_active"] is True


@pytest.mark.django_db
def test_menu_group_grants_include_granted_on(usage_repository, usage_dataset):
    """メニューグループの付与は付与日つきで返す（TC-INF-024）。"""
    general_user = usage_dataset["general_user"]

    grants = usage_repository.menu_group_grants()

    rows = {(grant["user_id"], grant["group_key"]): grant for grant in grants}
    assert set(rows) == {
        (general_user.pk, "sales"),
        (general_user.pk, "management"),
        (usage_dataset["dormant_user"].pk, "sales"),
    }
    grant = rows[(general_user.pk, "sales")]
    assert grant["granted_on"] == date(2026, 5, 1)
    assert grant["username"] == "10002"
    assert grant["display_name"] == "一般 花子"


@pytest.mark.django_db
def test_counts_include_logs_with_null_user(usage_repository, usage_dataset):
    """物理削除されたユーザーのログも全体・メニュー別・日別・出力記録には含める（TC-INF-025）。"""
    counts = usage_repository.overall_counts(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT)
    menu_rows = {
        row["menu_key"]: row
        for row in usage_repository.menu_counts(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT)
    }
    daily = {
        row["on"]: row["count"]
        for row in usage_repository.daily_counts(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT)
    }
    exports = usage_repository.export_entries(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT)
    user_rows = usage_repository.user_counts(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT)
    pairs = usage_repository.menu_counts_by_user(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT)
    used_keys = usage_repository.used_menu_keys_by_user(
        start_at=PERIOD_START_AT, end_at=PERIOD_END_AT
    )

    assert counts["export_count"] == 2
    assert menu_rows["shipment-trend-list"]["export_count"] == 2
    assert daily[date(2026, 8, 5)] == 1
    assert any(row["user_id"] is None for row in exports)
    # ユーザー別の集計には含めない（design.md §6.7）
    assert all(row["user_id"] is not None for row in user_rows)
    assert all(row["user_id"] is not None for row in pairs)
    assert None not in used_keys


@pytest.mark.django_db
def test_menu_counts_include_unknown_menu_key(usage_repository):
    """現行のメニュー定義に無いメニューキーもメニュー別集計に現れる（TC-INF-026）。"""
    user = _create_user("10002")
    _log(
        user=user, menu_key="legacy-report", usage_type="VIEW", used_at=_jst(2026, 8, 2, 10, 0)
    )

    rows = usage_repository.menu_counts(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT)

    assert [row["menu_key"] for row in rows] == ["legacy-report"]
    assert rows[0]["view_count"] == 1


@pytest.mark.django_db
def test_counts_return_empty_without_logs(usage_repository):
    """メニュー利用ログが 1 件も無くても例外にならず、件数 0・一覧は空を返す（TC-INF-027）。"""
    counts = usage_repository.overall_counts(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT)

    assert counts == {"usage_count": 0, "export_count": 0, "active_user_count": 0}
    assert usage_repository.menu_counts(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT) == []
    assert usage_repository.user_counts(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT) == []
    assert (
        usage_repository.menu_counts_by_user(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT) == []
    )
    assert (
        usage_repository.used_menu_keys_by_user(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT)
        == {}
    )
    assert usage_repository.daily_counts(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT) == []
    assert usage_repository.export_entries(start_at=PERIOD_START_AT, end_at=PERIOD_END_AT) == []
    assert usage_repository.last_used_at_by_menu_key() == {}
    assert usage_repository.last_used_at_by_user() == {}
    assert usage_repository.approved_user_entries() == []
    assert usage_repository.menu_group_grants() == []


def test_menu_usage_log_defines_four_indexes():
    """メニュー利用ログには design.md §5.2 の索引 4 本が定義されている（TC-INF-028）。"""
    indexes = {index.name: list(index.fields) for index in MenuUsageLog._meta.indexes}

    assert indexes == {
        "menu_usage_used_at_idx": ["used_at"],
        "menu_usage_menu_key_idx": ["menu_key", "-used_at"],
        "menu_usage_user_idx": ["user", "-used_at"],
        "menu_usage_type_idx": ["usage_type", "-used_at"],
    }
