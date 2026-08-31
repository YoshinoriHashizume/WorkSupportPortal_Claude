from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlencode

MAX_SORT_SPECS = 5
VALID_DIRECTIONS = frozenset({"asc", "desc"})
PAGE_SIZE_OPTIONS = (20, 50, 100, 200)
DEFAULT_PAGE_SIZE = 50


@dataclass(frozen=True)
class SortSpec:
    column: str
    direction: str


@dataclass(frozen=True)
class PaginatedRows:
    rows: list[object]
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


def paginate_rows(rows: list[object], *, page: int, page_size: int) -> PaginatedRows:
    total_count = len(rows)
    total_pages = max(1, math.ceil(total_count / page_size)) if total_count else 1
    current_page = min(max(page, 1), total_pages)
    start = (current_page - 1) * page_size
    page_rows = rows[start : start + page_size]
    return PaginatedRows(
        rows=page_rows,
        total_count=total_count,
        page=current_page,
        page_size=page_size,
        total_pages=total_pages,
        start_index=start + 1 if page_rows else 0,
        end_index=start + len(page_rows),
    )


def parse_sort_specs(
    params: dict[str, str],
    *,
    sortable_keys: set[str],
    default_specs: tuple[SortSpec, ...],
    default_direction_for_column: Callable[[str], str],
    default_sort: str | None = None,
    default_direction: str = "asc",
) -> tuple[SortSpec, ...]:
    sort_raw = (params.get("sort") or default_sort or "").strip()
    dir_raw = (params.get("dir") or default_direction).strip().lower()
    columns = [column for column in sort_raw.split(",") if column.strip()]
    directions = [direction for direction in dir_raw.split(",") if direction.strip()]

    if not columns:
        columns = [default_specs[0].column] if default_specs else [default_sort or ""]

    specs: list[SortSpec] = []
    seen: set[str] = set()
    for index, column in enumerate(columns):
        column = column.strip()
        if column not in sortable_keys or column in seen:
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

    if not specs:
        if default_specs:
            return default_specs
        fallback_column = (default_sort or "").strip()
        if fallback_column:
            return (SortSpec(fallback_column, default_direction),)
    return tuple(specs)


def build_table_query_string(
    *,
    sort_specs: tuple[SortSpec, ...],
    page: int,
    page_size: int,
    extra: dict[str, str | int] | None = None,
) -> str:
    query: dict[str, str | int] = {
        "sort": ",".join(spec.column for spec in sort_specs),
        "dir": ",".join(spec.direction for spec in sort_specs),
        "page": page,
        "page_size": page_size,
    }
    if extra:
        query.update(extra)
    return urlencode(query)


def sort_spec_label(spec: SortSpec, *, column_labels: dict[str, str]) -> str:
    label = column_labels.get(spec.column, spec.column)
    direction_label = "昇順" if spec.direction == "asc" else "降順"
    return f"{label}（{direction_label}）"
