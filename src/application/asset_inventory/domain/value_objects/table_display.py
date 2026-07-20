from __future__ import annotations

import math
from dataclasses import dataclass
from urllib.parse import urlencode

from application.asset_inventory.domain.value_objects.dates import parse_asset_acquisition_date
from application.asset_inventory.domain.repositories.ports import (
    DEFAULT_PAGE_SIZE,
    MatchStatus,
    PAGE_SIZE_OPTIONS,
    ReconcileRow,
    RowTone,
    SORTABLE_COLUMNS,
    SORTABLE_KEYS,
)

MAX_SORT_SPECS = 5
VALID_DIRECTIONS = frozenset({"asc", "desc"})
COLUMN_LABELS = dict(SORTABLE_COLUMNS)

STATUS_SORT_ORDER = {
    MatchStatus.MATCHED: 0,
    MatchStatus.ASSET_ONLY: 1,
    MatchStatus.INVENTORY_ONLY: 2,
}

TONE_SORT_ORDER = {
    RowTone.MATCH_CLEAN: 0,
    RowTone.MATCH_FACTORY: 1,
    RowTone.MATCH_DIFF: 2,
    RowTone.NONE: 3,
}


@dataclass(frozen=True)
class SortSpec:
    column: str
    direction: str


DEFAULT_SORT_SPECS: tuple[SortSpec, ...] = (
    SortSpec("asset_number", "asc"),
    SortSpec("branch_number", "asc"),
)


@dataclass(frozen=True)
class TableDisplayParams:
    sort_specs: tuple[SortSpec, ...]
    page: int
    page_size: int

    @property
    def sort(self) -> str:
        return self.sort_specs[0].column if self.sort_specs else DEFAULT_SORT_SPECS[0].column

    @property
    def direction(self) -> str:
        return self.sort_specs[0].direction if self.sort_specs else DEFAULT_SORT_SPECS[0].direction

    def sort_param(self) -> str:
        return ",".join(spec.column for spec in self.sort_specs)

    def dir_param(self) -> str:
        return ",".join(spec.direction for spec in self.sort_specs)


@dataclass(frozen=True)
class PaginatedRows:
    rows: tuple[ReconcileRow, ...]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    start_index: int
    end_index: int

    @property
    def has_previous(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages


def default_direction_for_column(column: str) -> str:
    if column in {"inventory_datetime"}:
        return "desc"
    return "asc"


def parse_sort_specs(params: dict[str, str]) -> tuple[SortSpec, ...]:
    sort_raw = (params.get("sort") or "").strip()
    dir_raw = (params.get("dir") or "").strip().lower()
    if not sort_raw or sort_raw == "default":
        return DEFAULT_SORT_SPECS

    columns = [column.strip() for column in sort_raw.split(",") if column.strip()]
    directions = [direction.strip() for direction in dir_raw.split(",") if direction.strip()]
    if not columns:
        return DEFAULT_SORT_SPECS

    specs: list[SortSpec] = []
    seen: set[str] = set()
    for index, column in enumerate(columns):
        if column not in SORTABLE_KEYS or column in seen:
            continue
        seen.add(column)
        if index < len(directions) and directions[index] in VALID_DIRECTIONS:
            direction = directions[index]
        elif directions and directions[-1] in VALID_DIRECTIONS:
            direction = directions[-1]
        else:
            direction = default_direction_for_column(column)
        specs.append(SortSpec(column=column, direction=direction))
        if len(specs) >= MAX_SORT_SPECS:
            break

    return tuple(specs) if specs else DEFAULT_SORT_SPECS


def parse_table_display_params(params: dict[str, str]) -> TableDisplayParams:
    sort_specs = parse_sort_specs(params)
    try:
        page_size = int(params.get("page_size") or DEFAULT_PAGE_SIZE)
    except ValueError:
        page_size = DEFAULT_PAGE_SIZE
    if page_size not in PAGE_SIZE_OPTIONS:
        page_size = DEFAULT_PAGE_SIZE

    try:
        page = int(params.get("page") or "1")
    except ValueError:
        page = 1

    return TableDisplayParams(sort_specs=sort_specs, page=max(page, 1), page_size=page_size)


def toggle_sort_direction(params: TableDisplayParams, column: str) -> str:
    for spec in params.sort_specs:
        if spec.column == column:
            return "desc" if spec.direction == "asc" else "asc"
    return default_direction_for_column(column)


def single_column_sort_specs(params: TableDisplayParams, column: str) -> tuple[SortSpec, ...]:
    return (SortSpec(column=column, direction=toggle_sort_direction(params, column)),)


def sort_spec_label(spec: SortSpec) -> str:
    label = COLUMN_LABELS.get(spec.column, spec.column)
    direction_label = "昇順" if spec.direction == "asc" else "降順"
    return f"{label}（{direction_label}）"


def build_table_query_string(*, sort_specs: tuple[SortSpec, ...], page: int, page_size: int) -> str:
    if not sort_specs:
        sort_specs = DEFAULT_SORT_SPECS
    return urlencode(
        {
            "sort": ",".join(spec.column for spec in sort_specs),
            "dir": ",".join(spec.direction for spec in sort_specs),
            "page": page,
            "page_size": page_size,
        }
    )


def _sort_value(row: ReconcileRow, column: str) -> object:
    if column == "status_label":
        return (STATUS_SORT_ORDER.get(row.match_status, 99), row.status_label.lower())
    if column == "tone_label":
        return (TONE_SORT_ORDER.get(row.row_tone, 99), row.tone_label.lower())
    value = getattr(row, column, "")
    if column in {"asset_number", "branch_number", "site_name", "inventory_datetime", "plate_created"}:
        return (value == "", str(value).lower())
    return (value == "", str(value).lower())


def _sort_rows_by_acquisition_date(
    rows: list[ReconcileRow],
    *,
    reverse: bool,
) -> list[ReconcileRow]:
    dated_rows = [row for row in rows if parse_asset_acquisition_date(row.asset_acquisition_date)]
    empty_rows = [row for row in rows if not parse_asset_acquisition_date(row.asset_acquisition_date)]
    dated_rows.sort(
        key=lambda row: parse_asset_acquisition_date(row.asset_acquisition_date) or "",
        reverse=reverse,
    )
    return dated_rows + empty_rows


def sort_rows(
    rows: tuple[ReconcileRow, ...],
    sort_specs: tuple[SortSpec, ...],
) -> tuple[ReconcileRow, ...]:
    if not sort_specs:
        sort_specs = DEFAULT_SORT_SPECS
    sorted_rows = list(rows)
    for spec in reversed(sort_specs):
        reverse = spec.direction == "desc"
        if spec.column == "asset_acquisition_date":
            sorted_rows = _sort_rows_by_acquisition_date(sorted_rows, reverse=reverse)
            continue
        sorted_rows.sort(key=lambda row: _sort_value(row, spec.column), reverse=reverse)
    return tuple(sorted_rows)


def paginate_rows(
    rows: tuple[ReconcileRow, ...],
    page: int,
    page_size: int,
) -> PaginatedRows:
    total_count = len(rows)
    if total_count == 0:
        return PaginatedRows(
            rows=(),
            total_count=0,
            page=1,
            page_size=page_size,
            total_pages=1,
            start_index=0,
            end_index=0,
        )

    total_pages = max(1, math.ceil(total_count / page_size))
    current_page = min(max(page, 1), total_pages)
    start = (current_page - 1) * page_size
    end = start + page_size
    page_rows = rows[start:end]
    return PaginatedRows(
        rows=tuple(page_rows),
        total_count=total_count,
        page=current_page,
        page_size=page_size,
        total_pages=total_pages,
        start_index=start + 1,
        end_index=start + len(page_rows),
    )


def parse_page_size(raw_value: str | None, *, options: tuple[int, ...], default: int) -> int:
    try:
        page_size = int(raw_value or default)
    except ValueError:
        return default
    if page_size in options:
        return page_size
    return default
