"""利用状況（画面側）の行 VO・ファーストクラスコレクション・集計関数。

design.md §4.2「画面側（`usage_status_display.py`）」に対応する。
Django には依存しない。並び替えは共有カーネルの `SortSpec` を用いる。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from application.portal.domain.value_objects.menu import (
    MENU_BY_KEY,
    MENU_GROUP_BY_KEY,
    MENU_ITEMS,
)
from application.portal.domain.value_objects.usage_period import AggregationPeriod
from application.shared.domain.value_objects.list_table import SortSpec

# --- 定数 -------------------------------------------------------------------

USAGE_STATUS_CSV_ROW_LIMIT = 100_000
"""CSV 出力の上限行数（REQ-F-014）。"""

RETIRED_MENU_SUFFIX = "（廃止）"
"""現行定義に無いメニューキーに付ける接尾辞（REQ-F-017）。"""

UNKNOWN_USER_LABEL = "（ユーザー不明）"
"""ユーザーを特定できない利用記録の表示ラベル（REQ-F-018）。"""

UNKNOWN_GROUP_LABEL = "—"
"""廃止メニューのメニューグループ表示（REQ-F-017）。"""

USAGE_STATUS_SECTIONS = ("menus", "users", "unused-grants", "exports")
"""CSV 出力の対象区分（REQ-F-014）。"""

USAGE_STATUS_PURPOSE_NOTE = (
    "この画面はメニューの改廃・定着支援・権限棚卸・データ持ち出しの確認のために用います。"
    "個人の勤務時間の把握や勤務評価には用いません。"
)
"""画面に常時表示する利用目的の注記（REQ-NF-005）。"""

GROUP_TITLE_SEPARATOR = "、"
"""1 ユーザーが使えるメニューグループ名を連結する区切り文字。"""

MENU_USAGE_SORT_LABELS = {
    "group_title": "メニューグループ",
    "menu_title": "メニュー",
    "view_count": "表示回数",
    "export_count": "出力回数",
    "user_count": "利用ユーザー数",
    "last_used_on": "最終利用日",
}

USER_USAGE_SORT_LABELS = {
    "username": "社員番号",
    "display_name": "表示名",
    "role": "権限",
    "menu_group_titles": "使えるグループ",
    "usage_count": "利用回数",
    "export_count": "出力回数",
    "most_used_menu_title": "最多利用メニュー",
    "last_used_on": "最終利用日",
    "last_login_at": "最終ログイン",
}

UNUSED_GRANT_SORT_LABELS = {
    "username": "社員番号",
    "display_name": "表示名",
    "group_title": "メニューグループ",
    "last_used_on": "最終利用日",
    "granted_on": "付与日",
}

EXPORT_LOG_SORT_LABELS = {
    "used_at": "日時",
    "username": "社員番号",
    "display_name": "表示名",
    "group_title": "メニューグループ",
    "menu_title": "メニュー",
}


# --- 表示用の書式 -----------------------------------------------------------


def _format_date(value: date | None) -> str:
    return value.strftime("%Y/%m/%d") if value else ""


def _format_datetime(value: datetime | None) -> str:
    return value.strftime("%Y/%m/%d %H:%M") if value else ""


def _as_date(value: datetime | date | None) -> date | None:
    if value is None:
        return None
    return value.date() if isinstance(value, datetime) else value


def _sort_key(value: object) -> object:
    """並び替えのキー。未設定は最小値として扱う。"""
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


# --- 行 VO ------------------------------------------------------------------


@dataclass(frozen=True)
class UsageSummary:
    """全体集計（V-609）。"""

    active_user_count: int
    usage_count: int
    export_count: int
    unused_user_count: int
    dormant_user_count: int


@dataclass(frozen=True)
class MenuUsageRow:
    """メニュー別の利用状況 1 行（REQ-F-008）。"""

    group_title: str
    menu_title: str
    view_count: int
    export_count: int
    user_count: int
    last_used_on: date | None
    is_retired: bool = False

    def csv_values(self) -> list[str]:
        return [
            self.group_title,
            self.menu_title,
            str(self.view_count),
            str(self.export_count),
            str(self.user_count),
            _format_date(self.last_used_on),
        ]


@dataclass(frozen=True)
class UserUsageRow:
    """ユーザー別の利用状況 1 行（REQ-F-009）。"""

    username: str
    display_name: str
    role: str
    menu_group_titles: str
    usage_count: int
    export_count: int
    most_used_menu_title: str
    last_used_on: date | None
    last_login_at: datetime | None

    def csv_values(self) -> list[str]:
        return [
            self.username,
            self.display_name,
            self.role,
            self.menu_group_titles,
            str(self.usage_count),
            str(self.export_count),
            self.most_used_menu_title,
            _format_date(self.last_used_on),
            _format_datetime(self.last_login_at),
        ]


@dataclass(frozen=True)
class UnusedMenuGroupGrantRow:
    """未利用のメニューグループ付与（V-612）1 行（REQ-F-010）。"""

    username: str
    display_name: str
    group_title: str
    last_used_on: date | None
    granted_on: date | None

    def csv_values(self) -> list[str]:
        return [
            self.username,
            self.display_name,
            self.group_title,
            _format_date(self.last_used_on),
            _format_date(self.granted_on),
        ]


@dataclass(frozen=True)
class ExportLogRow:
    """出力ログ 1 行（REQ-F-011）。"""

    used_at: datetime
    username: str
    display_name: str
    group_title: str
    menu_title: str

    def csv_values(self) -> list[str]:
        return [
            _format_datetime(self.used_at),
            self.username,
            self.display_name,
            self.group_title,
            self.menu_title,
        ]


@dataclass(frozen=True)
class DailyUsagePoint:
    """日別推移（V-611）の 1 点。"""

    on: date
    count: int


# --- 集計の入力となる VO ----------------------------------------------------


@dataclass(frozen=True)
class UserAggregationEntry:
    """未利用ユーザー数・休眠ユーザー数の集計対象となるユーザー 1 件。"""

    user_id: int
    is_approved: bool
    is_active: bool
    last_login_at: datetime | None

    @property
    def is_aggregation_target(self) -> bool:
        """母集団は利用申請が許可済み（core S-001）かつ有効（S-604）なユーザー。"""
        return self.is_approved and self.is_active


@dataclass(frozen=True)
class MenuGroupGrantEntry:
    """メニューグループの付与 1 件（未利用のメニューグループ付与の集計入力）。"""

    user_id: int
    username: str
    display_name: str
    group_key: str
    granted_on: date | None


# --- ファーストクラスコレクション -------------------------------------------


class _RowCollection:
    """行 VO のファーストクラスコレクションに共通する振る舞い。"""

    LABELS: dict[str, str] = {}

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", self._normalize(list(self.rows)))

    @staticmethod
    def _normalize(rows: list) -> list:
        return rows

    def _with_rows(self, rows: list) -> "_RowCollection":
        return type(self)(rows)

    @property
    def is_empty(self) -> bool:
        """「該当なし」表示の判定（REQ-F-016）。"""
        return not self.rows

    def sorted_by(self, specs: Sequence[SortSpec]) -> "_RowCollection":
        """共有カーネルの `SortSpec` で並び替えた新しいコレクションを返す（REQ-NF-007）。"""
        rows = list(self.rows)
        for spec in reversed(tuple(specs)):
            if spec.column not in self.LABELS:
                continue
            rows.sort(
                key=lambda row, column=spec.column: _sort_key(getattr(row, column)),
                reverse=spec.direction == "desc",
            )
        return self._with_rows(rows)

    def filtered_by_group(self, group_key: str) -> "_RowCollection":
        """メニューグループで絞り込んだ新しいコレクションを返す（REQ-F-013）。"""
        key = (group_key or "").strip()
        if not key:
            return self._with_rows(list(self.rows))
        title = menu_group_title_by_key(key)
        return self._with_rows([row for row in self.rows if self._matches_group(row, title)])

    @staticmethod
    def _matches_group(row, title: str) -> bool:
        return getattr(row, "group_title", "") == title

    def csv_rows(self) -> list[list[str]]:
        """ヘッダ行＋データ行（REQ-F-014）。"""
        return [list(self.LABELS.values())] + [row.csv_values() for row in self.rows]


@dataclass(frozen=True)
class MenuUsageRows(_RowCollection):
    """メニュー別の利用状況一覧（REQ-F-008）。"""

    LABELS = MENU_USAGE_SORT_LABELS

    rows: list[MenuUsageRow] = field(default_factory=list)


@dataclass(frozen=True)
class UserUsageRows(_RowCollection):
    """ユーザー別の利用状況一覧（REQ-F-009）。"""

    LABELS = USER_USAGE_SORT_LABELS

    rows: list[UserUsageRow] = field(default_factory=list)

    @staticmethod
    def _matches_group(row, title: str) -> bool:
        titles = [part.strip() for part in row.menu_group_titles.split(GROUP_TITLE_SEPARATOR)]
        return title in titles


@dataclass(frozen=True)
class UnusedMenuGroupGrantRows(_RowCollection):
    """未利用のメニューグループ付与の一覧（REQ-F-010）。"""

    LABELS = UNUSED_GRANT_SORT_LABELS

    rows: list[UnusedMenuGroupGrantRow] = field(default_factory=list)


@dataclass(frozen=True)
class ExportLogRows(_RowCollection):
    """出力ログの一覧（REQ-F-011）。既定は日時の降順。"""

    LABELS = EXPORT_LOG_SORT_LABELS

    rows: list[ExportLogRow] = field(default_factory=list)

    @staticmethod
    def _normalize(rows: list[ExportLogRow]) -> list[ExportLogRow]:
        return sorted(rows, key=lambda row: row.used_at, reverse=True)

    @staticmethod
    def _matches_group(row, title: str) -> bool:
        return row.group_title == title


@dataclass(frozen=True)
class DailyUsageTrend:
    """日別推移（V-611）。"""

    points: list[DailyUsagePoint] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "points", list(self.points))

    @property
    def is_empty(self) -> bool:
        return not self.points

    @property
    def max_count(self) -> int:
        return max((point.count for point in self.points), default=0)


# --- メニューの表示 ---------------------------------------------------------


def is_retired_menu(menu_key: str) -> bool:
    """現行定義に無い（廃止された）メニューキーかどうか（REQ-F-017）。"""
    return menu_key not in MENU_BY_KEY


def menu_display_title(menu_key: str) -> str:
    """現行定義にあれば表示名、無ければ廃止として表示する（REQ-F-017）。"""
    item = MENU_BY_KEY.get(menu_key)
    if item is None:
        return f"{menu_key}{RETIRED_MENU_SUFFIX}"
    return item.title


def menu_group_title_by_key(group_key: str) -> str:
    """メニューグループキーに対応するメニューグループ名。"""
    group = MENU_GROUP_BY_KEY.get(group_key)
    return group.title if group else group_key


def menu_group_title(menu_key: str) -> str:
    """メニューキーに対応するメニューグループ名（廃止メニューは `UNKNOWN_GROUP_LABEL`）。"""
    item = MENU_BY_KEY.get(menu_key)
    if item is None:
        return UNKNOWN_GROUP_LABEL
    return menu_group_title_by_key(item.group_key)


def aggregation_target_menu_keys() -> tuple[str, ...]:
    """行として並べるメニューキー（遷移先を持たない親メニューを除外。REQ-F-008）。"""
    return tuple(item.key for item in MENU_ITEMS if item.href)


# --- 集計関数 ---------------------------------------------------------------


def most_used_menu_key(entries: Iterable[tuple[str, int]]) -> str | None:
    """最多利用メニュー（V-610）。同数の場合はメニューキーの昇順で先頭を採る。"""
    best_key: str | None = None
    best_count = 0
    for menu_key, count in entries:
        if best_key is None or count > best_count or (count == best_count and menu_key < best_key):
            best_key, best_count = menu_key, count
    return best_key


def build_daily_trend(counts: Mapping[date, int], period: AggregationPeriod) -> DailyUsageTrend:
    """集計期間の全日を並べ、実績のない日を 0 で埋める（REQ-F-012）。"""
    points: list[DailyUsagePoint] = []
    current = period.start_date
    while current <= period.end_date:
        points.append(DailyUsagePoint(on=current, count=int(counts.get(current, 0))))
        current += timedelta(days=1)
    return DailyUsageTrend(points)


def unused_user_count(
    entries: Iterable[UserAggregationEntry],
    used_user_ids: Iterable[int] | None = None,
) -> int:
    """未利用ユーザー数（S-602）。集計期間内の利用回数が 0 の対象ユーザー数。"""
    used = set(used_user_ids or ())
    return sum(1 for entry in entries if entry.is_aggregation_target and entry.user_id not in used)


def dormant_user_count(
    entries: Iterable[UserAggregationEntry],
    period: AggregationPeriod,
) -> int:
    """休眠ユーザー数（S-605）。最終ログイン（V-606）が集計期間の開始日より前。"""
    count = 0
    for entry in entries:
        if not entry.is_aggregation_target:
            continue
        last_login_on = _as_date(entry.last_login_at)
        if last_login_on is None or last_login_on < period.start_date:
            count += 1
    return count


def unused_menu_group_grant_rows(
    grants: Iterable[MenuGroupGrantEntry],
    *,
    used_group_keys_by_user: Mapping[int, set[str]] | None = None,
    last_used_on_by_user: Mapping[int, date | None] | None = None,
) -> UnusedMenuGroupGrantRows:
    """付与済みメニューグループ − 期間内に利用したメニューグループ の差分（REQ-F-010）。"""
    used_by_user = used_group_keys_by_user or {}
    last_used = last_used_on_by_user or {}
    rows: list[UnusedMenuGroupGrantRow] = []
    for grant in grants:
        if grant.group_key in used_by_user.get(grant.user_id, set()):
            continue
        rows.append(
            UnusedMenuGroupGrantRow(
                username=grant.username,
                display_name=grant.display_name,
                group_title=menu_group_title_by_key(grant.group_key),
                last_used_on=last_used.get(grant.user_id),
                granted_on=grant.granted_on,
            )
        )
    rows.sort(key=lambda row: (row.username, row.group_title))
    return UnusedMenuGroupGrantRows(rows)
