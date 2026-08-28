"""利用状況（画面側）のユースケース。

design.md §6.7 に対応する。Django には依存しない。
集計期間の変換に使うタイムゾーンは `wiring` から `tzinfo` として受け取る。
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from application.portal.domain.repositories.ports import UsageStatusRepository
from application.portal.domain.value_objects.menu import MENU_BY_KEY
from application.portal.domain.value_objects.usage_period import (
    AggregationPeriod,
    AggregationPeriodError,
    parse_aggregation_period,
)
from application.portal.domain.value_objects.usage_status_display import (
    EXPORT_LOG_SORT_LABELS,
    MENU_USAGE_SORT_LABELS,
    UNKNOWN_USER_LABEL,
    UNUSED_GRANT_SORT_LABELS,
    USAGE_STATUS_CSV_ROW_LIMIT,
    USAGE_STATUS_PURPOSE_NOTE,
    USAGE_STATUS_SECTIONS,
    USER_USAGE_SORT_LABELS,
    DailyUsageTrend,
    ExportLogRow,
    ExportLogRows,
    GROUP_TITLE_SEPARATOR,
    MenuGroupGrantEntry,
    MenuUsageRow,
    MenuUsageRows,
    UnusedMenuGroupGrantRows,
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
    menu_group_title_by_key,
    most_used_menu_key,
    unused_menu_group_grant_rows,
    unused_user_count,
)
from application.shared.domain.value_objects.list_table import (
    DEFAULT_PAGE_SIZE,
    SortSpec,
    paginate_rows,
)

MESSAGE_UNKNOWN_SECTION = "出力対象の区分が正しくありません。"
MESSAGE_ROW_LIMIT_EXCEEDED = (
    "出力対象が 10 万行を超えました。集計期間または絞り込みを狭めてください。"
)

SORT_LABELS_BY_SECTION: dict[str, dict[str, str]] = {
    "menus": MENU_USAGE_SORT_LABELS,
    "users": USER_USAGE_SORT_LABELS,
    "unused-grants": UNUSED_GRANT_SORT_LABELS,
    "exports": EXPORT_LOG_SORT_LABELS,
}

VALID_SORT_DIRECTIONS = ("asc", "desc")


@dataclass(frozen=True)
class CsvPayload:
    """CSV 出力の結果。`rows` の 1 行目はヘッダ。出力できない場合は `rows` が None。"""

    rows: list[list[str]] | None
    error_message: str | None


@dataclass(frozen=True)
class _Sections:
    """集計期間から組み立てた表示要素一式。"""

    summary: UsageSummary
    daily_trend: DailyUsageTrend
    menu_usage_rows: MenuUsageRows
    user_usage_rows: UserUsageRows
    unused_grant_rows: UnusedMenuGroupGrantRows
    export_log_rows: ExportLogRows


def _as_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _empty_sections(period: AggregationPeriod | None) -> _Sections:
    return _Sections(
        summary=UsageSummary(
            active_user_count=0,
            usage_count=0,
            export_count=0,
            unused_user_count=0,
            dormant_user_count=0,
        ),
        daily_trend=build_daily_trend({}, period) if period else DailyUsageTrend([]),
        menu_usage_rows=MenuUsageRows([]),
        user_usage_rows=UserUsageRows([]),
        unused_grant_rows=UnusedMenuGroupGrantRows([]),
        export_log_rows=ExportLogRows([]),
    )


class UsageStatus:
    """利用状況画面と CSV 出力を組み立てる。"""

    def __init__(self, repository: UsageStatusRepository, *, tzinfo: dt.tzinfo) -> None:
        self._repository = repository
        self._tzinfo = tzinfo

    # --- 公開メソッド -------------------------------------------------------

    def page_context(
        self,
        *,
        today: date,
        start: str = "",
        end: str = "",
        group_key: str = "",
        sort_key: str = "",
        sort_direction: str = "asc",
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> dict[str, object]:
        direction = sort_direction if sort_direction in VALID_SORT_DIRECTIONS else "asc"
        try:
            period = parse_aggregation_period(start, end, today=today)
            error_message: str | None = None
        except AggregationPeriodError as error:
            period = None
            error_message = error.message

        sections = self._build_sections(period) if period else _empty_sections(None)
        sections = self._filtered_and_sorted(sections, group_key=group_key, spec_key=sort_key, direction=direction)

        context: dict[str, object] = {
            "purpose_note": USAGE_STATUS_PURPOSE_NOTE,
            "error_message": error_message,
            "period": period,
            "start": start or (period.start_date.isoformat() if period else ""),
            "end": end or (period.end_date.isoformat() if period else ""),
            "group_key": group_key,
            "sort_key": sort_key,
            "sort_direction": direction,
            "summary": sections.summary,
            "daily_trend": sections.daily_trend,
            "menu_usage_rows": sections.menu_usage_rows,
            "user_usage_rows": sections.user_usage_rows,
            "unused_grant_rows": sections.unused_grant_rows,
            "export_log_rows": sections.export_log_rows,
            "menu_usage_page": paginate_rows(
                list(sections.menu_usage_rows.rows), page=page, page_size=page_size
            ),
            "user_usage_page": paginate_rows(
                list(sections.user_usage_rows.rows), page=page, page_size=page_size
            ),
            "unused_grant_page": paginate_rows(
                list(sections.unused_grant_rows.rows), page=page, page_size=page_size
            ),
            "export_log_page": paginate_rows(
                list(sections.export_log_rows.rows), page=page, page_size=page_size
            ),
            "sort_labels": SORT_LABELS_BY_SECTION,
        }
        return context

    def csv_payload(
        self,
        *,
        section: str,
        today: date,
        start: str = "",
        end: str = "",
        group_key: str = "",
        sort_key: str = "",
        sort_direction: str = "asc",
    ) -> CsvPayload:
        if section not in USAGE_STATUS_SECTIONS:
            return CsvPayload(rows=None, error_message=MESSAGE_UNKNOWN_SECTION)

        direction = sort_direction if sort_direction in VALID_SORT_DIRECTIONS else "asc"
        try:
            period = parse_aggregation_period(start, end, today=today)
        except AggregationPeriodError as error:
            return CsvPayload(rows=None, error_message=error.message)

        sections = self._filtered_and_sorted(
            self._build_sections(period),
            group_key=group_key,
            spec_key=sort_key,
            direction=direction,
        )
        collection = {
            "menus": sections.menu_usage_rows,
            "users": sections.user_usage_rows,
            "unused-grants": sections.unused_grant_rows,
            "exports": sections.export_log_rows,
        }[section]

        if len(collection.rows) > USAGE_STATUS_CSV_ROW_LIMIT:
            return CsvPayload(rows=None, error_message=MESSAGE_ROW_LIMIT_EXCEEDED)
        return CsvPayload(rows=collection.csv_rows(), error_message=None)

    # --- 組み立て -----------------------------------------------------------

    def _filtered_and_sorted(
        self,
        sections: _Sections,
        *,
        group_key: str,
        spec_key: str,
        direction: str,
    ) -> _Sections:
        specs = (SortSpec(column=spec_key, direction=direction),) if spec_key else ()

        def refine(collection):
            filtered = collection.filtered_by_group(group_key)
            return filtered.sorted_by(specs) if specs else filtered

        return _Sections(
            summary=sections.summary,
            daily_trend=sections.daily_trend,
            menu_usage_rows=refine(sections.menu_usage_rows),
            user_usage_rows=refine(sections.user_usage_rows),
            unused_grant_rows=refine(sections.unused_grant_rows),
            export_log_rows=refine(sections.export_log_rows),
        )

    def _build_sections(self, period: AggregationPeriod) -> _Sections:
        start_at, end_at = self._range(period)
        repository = self._repository

        overall = repository.overall_counts(start_at=start_at, end_at=end_at)
        menu_counts = repository.menu_counts(start_at=start_at, end_at=end_at)
        last_used_at_by_menu_key = repository.last_used_at_by_menu_key()
        user_counts = repository.user_counts(start_at=start_at, end_at=end_at)
        last_used_at_by_user = repository.last_used_at_by_user()
        menu_counts_by_user = repository.menu_counts_by_user(start_at=start_at, end_at=end_at)
        used_menu_keys_by_user = repository.used_menu_keys_by_user(start_at=start_at, end_at=end_at)
        daily_counts = repository.daily_counts(start_at=start_at, end_at=end_at)
        export_entries = repository.export_entries(start_at=start_at, end_at=end_at)
        approved_user_entries = repository.approved_user_entries()
        menu_group_grants = repository.menu_group_grants()

        active_users = [entry for entry in approved_user_entries if entry.get("is_active")]
        active_user_ids = {int(entry["user_id"]) for entry in active_users}

        aggregation_entries = [
            UserAggregationEntry(
                user_id=int(entry["user_id"]),
                is_approved=True,
                is_active=bool(entry.get("is_active")),
                last_login_at=entry.get("last_login"),
            )
            for entry in approved_user_entries
        ]

        return _Sections(
            summary=UsageSummary(
                active_user_count=int(overall.get("active_user_count", 0)),
                usage_count=int(overall.get("usage_count", 0)),
                export_count=int(overall.get("export_count", 0)),
                unused_user_count=unused_user_count(
                    aggregation_entries, used_menu_keys_by_user.keys()
                ),
                dormant_user_count=dormant_user_count(aggregation_entries, period),
            ),
            daily_trend=build_daily_trend(
                {row["on"]: int(row["count"]) for row in daily_counts}, period
            ),
            menu_usage_rows=self._menu_usage_rows(menu_counts, last_used_at_by_menu_key),
            user_usage_rows=self._user_usage_rows(
                active_users,
                user_counts=user_counts,
                menu_counts_by_user=menu_counts_by_user,
                last_used_at_by_user=last_used_at_by_user,
                menu_group_grants=menu_group_grants,
            ),
            unused_grant_rows=self._unused_grant_rows(
                menu_group_grants,
                active_user_ids=active_user_ids,
                used_menu_keys_by_user=used_menu_keys_by_user,
                last_used_at_by_user=last_used_at_by_user,
            ),
            export_log_rows=self._export_log_rows(export_entries),
        )

    def _range(self, period: AggregationPeriod) -> tuple[datetime, datetime]:
        """半開区間 [開始日 00:00, 終了日翌日 00:00) の aware な datetime。"""
        start_at = datetime.combine(period.start_date, dt.time.min, tzinfo=self._tzinfo)
        end_at = datetime.combine(period.end_date + timedelta(days=1), dt.time.min, tzinfo=self._tzinfo)
        return start_at, end_at

    @staticmethod
    def _menu_usage_rows(
        menu_counts: list[dict[str, object]],
        last_used_at_by_menu_key: dict[str, object],
    ) -> MenuUsageRows:
        counts_by_key = {str(row["menu_key"]): row for row in menu_counts}
        keys = list(aggregation_target_menu_keys())
        keys += sorted(key for key in counts_by_key if key not in keys)

        rows = []
        for key in keys:
            counts = counts_by_key.get(key, {})
            rows.append(
                MenuUsageRow(
                    group_title=menu_group_title(key),
                    menu_title=menu_display_title(key),
                    view_count=int(counts.get("view_count", 0)),
                    export_count=int(counts.get("export_count", 0)),
                    user_count=int(counts.get("user_count", 0)),
                    last_used_on=_as_date(last_used_at_by_menu_key.get(key)),
                    is_retired=is_retired_menu(key),
                )
            )
        return MenuUsageRows(rows)

    @staticmethod
    def _user_usage_rows(
        active_users: list[dict[str, object]],
        *,
        user_counts: list[dict[str, object]],
        menu_counts_by_user: list[dict[str, object]],
        last_used_at_by_user: dict[int, object],
        menu_group_grants: list[dict[str, object]],
    ) -> UserUsageRows:
        counts_by_user: dict[int, dict[str, object]] = {
            int(row["user_id"]): row for row in user_counts
        }
        group_keys_by_user: dict[int, list[str]] = {}
        for grant in menu_group_grants:
            group_keys_by_user.setdefault(int(grant["user_id"]), []).append(str(grant["group_key"]))
        menu_entries_by_user: dict[int, list[tuple[str, int]]] = {}
        for row in menu_counts_by_user:
            menu_entries_by_user.setdefault(int(row["user_id"]), []).append(
                (str(row["menu_key"]), int(row["count"]))
            )

        rows = []
        for entry in active_users:
            user_id = int(entry["user_id"])
            counts = counts_by_user.get(user_id, {})
            most_used_key = most_used_menu_key(menu_entries_by_user.get(user_id, ()))
            rows.append(
                UserUsageRow(
                    username=str(entry.get("username", "")),
                    display_name=str(entry.get("display_name", "")),
                    role=str(entry.get("role", "")),
                    menu_group_titles=GROUP_TITLE_SEPARATOR.join(
                        menu_group_title_by_key(key)
                        for key in group_keys_by_user.get(user_id, ())
                    ),
                    usage_count=int(counts.get("usage_count", 0)),
                    export_count=int(counts.get("export_count", 0)),
                    most_used_menu_title=(
                        menu_display_title(most_used_key) if most_used_key else ""
                    ),
                    last_used_on=_as_date(last_used_at_by_user.get(user_id)),
                    last_login_at=entry.get("last_login"),
                )
            )
        return UserUsageRows(rows)

    @staticmethod
    def _unused_grant_rows(
        menu_group_grants: list[dict[str, object]],
        *,
        active_user_ids: set[int],
        used_menu_keys_by_user: dict[int, set[str]],
        last_used_at_by_user: dict[int, object],
    ) -> UnusedMenuGroupGrantRows:
        grants = [
            MenuGroupGrantEntry(
                user_id=int(grant["user_id"]),
                username=str(grant.get("username", "")),
                display_name=str(grant.get("display_name", "")),
                group_key=str(grant["group_key"]),
                granted_on=_as_date(grant.get("granted_on")),
            )
            for grant in menu_group_grants
            if int(grant["user_id"]) in active_user_ids
        ]
        used_group_keys_by_user = {
            user_id: {
                MENU_BY_KEY[menu_key].group_key
                for menu_key in menu_keys
                if menu_key in MENU_BY_KEY
            }
            for user_id, menu_keys in used_menu_keys_by_user.items()
        }
        return unused_menu_group_grant_rows(
            grants,
            used_group_keys_by_user=used_group_keys_by_user,
            last_used_on_by_user={
                user_id: _as_date(value) for user_id, value in last_used_at_by_user.items()
            },
        )

    @staticmethod
    def _export_log_rows(export_entries: list[dict[str, object]]) -> ExportLogRows:
        rows = []
        for entry in export_entries:
            menu_key = str(entry["menu_key"])
            has_user = entry.get("user_id") is not None
            rows.append(
                ExportLogRow(
                    used_at=entry["used_at"],
                    username=str(entry.get("username") or ""),
                    display_name=(
                        str(entry.get("display_name") or "") if has_user else UNKNOWN_USER_LABEL
                    ),
                    group_title=menu_group_title(menu_key),
                    menu_title=menu_display_title(menu_key),
                )
            )
        return ExportLogRows(rows)
