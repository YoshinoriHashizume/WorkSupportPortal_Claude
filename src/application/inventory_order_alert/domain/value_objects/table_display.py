from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urlencode

from application.inventory_order_alert.domain.value_objects.code_sort import numeric_code_sort_key
from application.inventory_order_alert.domain.value_objects.dates import parse_optional_ymd

SORTABLE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("alert_level", "アラート"),
    ("cust_chrg_psn_cd", "担当者コード"),
    ("cust_code", "得意先コード"),
    ("cust_name", "得意先名"),
    ("item_cd", "得意先品番"),
    ("level1_vend_cd", "仕入先コード"),
    ("level1_vend_name", "仕入先名"),
    ("level1_item_cd", "仕入先品番"),
    ("last_incoming_date", "最終入荷日"),
    ("last_ship_date", "最終出荷日"),
    ("post_shipment_count", "出荷回数"),
    ("post_shipment_total_qty", "出荷数合計"),
    ("stock_qty", "在庫数"),
    ("confirmation_status", "確認状態"),
)

PAGE_SIZE_OPTIONS = (20, 50, 100, 200)
DEFAULT_PAGE_SIZE = 50
DEFAULT_SORT = "alert_level"
DEFAULT_DIRECTION = "asc"
MAX_SORT_SPECS = 5
from application.inventory_order_alert.domain.value_objects.alert_level import ALERT_NONE, alert_sort_rank, normalize_alert_level
from application.inventory_order_alert.domain.value_objects.confirmation import confirmation_status_sort_key
VALID_DIRECTIONS = {"asc", "desc"}
SORTABLE_KEYS = {column for column, _label in SORTABLE_COLUMNS}
COLUMN_LABELS = dict(SORTABLE_COLUMNS)


@dataclass(frozen=True)
class SortSpec:
    column: str
    direction: str


@dataclass(frozen=True)
class TableDisplayParams:
    sort_specs: tuple[SortSpec, ...]
    page: int
    page_size: int

    @property
    def sort(self) -> str:
        return self.sort_specs[0].column if self.sort_specs else DEFAULT_SORT

    @property
    def direction(self) -> str:
        return self.sort_specs[0].direction if self.sort_specs else DEFAULT_DIRECTION

    def sort_param(self) -> str:
        return ",".join(spec.column for spec in self.sort_specs)

    def dir_param(self) -> str:
        return ",".join(spec.direction for spec in self.sort_specs)

    def query_string(self, *, page: int | None = None, sort_specs: tuple[SortSpec, ...] | None = None, page_size: int | None = None) -> str:
        specs = sort_specs if sort_specs is not None else self.sort_specs
        return build_table_query_string(
            sort_specs=specs,
            page=page if page is not None else self.page,
            page_size=page_size if page_size is not None else self.page_size,
        )


@dataclass(frozen=True)
class PaginatedRows:
    rows: list[dict[str, object]]
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


def build_table_query_string(*, sort_specs: tuple[SortSpec, ...], page: int, page_size: int) -> str:
    if not sort_specs:
        sort_specs = (SortSpec(DEFAULT_SORT, DEFAULT_DIRECTION),)
    return urlencode(
        {
            "sort": ",".join(spec.column for spec in sort_specs),
            "dir": ",".join(spec.direction for spec in sort_specs),
            "page": page,
            "page_size": page_size,
        }
    )


def default_direction_for_column(column: str) -> str:
    if column == "alert_level":
        return "asc"
    if column in {"post_shipment_count", "post_shipment_total_qty", "stock_qty"}:
        return "desc"
    return "asc"


def parse_sort_specs(params: dict[str, str]) -> tuple[SortSpec, ...]:
    sort_raw = (params.get("sort") or DEFAULT_SORT).strip()
    dir_raw = (params.get("dir") or DEFAULT_DIRECTION).strip().lower()
    columns = [column for column in sort_raw.split(",") if column.strip()]
    directions = [direction for direction in dir_raw.split(",") if direction.strip()]

    if not columns:
        columns = [DEFAULT_SORT]

    specs: list[SortSpec] = []
    seen: set[str] = set()
    fallback_direction = DEFAULT_DIRECTION
    for index, column in enumerate(columns):
        column = column.strip()
        if column not in SORTABLE_KEYS or column in seen:
            continue
        seen.add(column)
        if index < len(directions) and directions[index] in VALID_DIRECTIONS:
            direction = directions[index]
        elif directions and directions[-1] in VALID_DIRECTIONS:
            direction = directions[-1]
        else:
            direction = default_direction_for_column(column)
        fallback_direction = direction
        specs.append(SortSpec(column=column, direction=direction))
        if len(specs) >= MAX_SORT_SPECS:
            break

    if not specs:
        specs.append(SortSpec(column=DEFAULT_SORT, direction=DEFAULT_DIRECTION))
    return tuple(specs)


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
    page = max(page, 1)

    return TableDisplayParams(sort_specs=sort_specs, page=page, page_size=page_size)


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


def _date_sort_key(value: object) -> tuple[int, str]:
    text = str(value or "").strip()
    if not text:
        return (0, "")
    try:
        return (1, parse_optional_ymd(text).isoformat())
    except ValueError:
        return (1, text)


def _sort_value(row: dict[str, object], column: str) -> object:
    value = row.get(column, "")
    if column == "alert_level":
        return alert_sort_rank(normalize_alert_level(str(value or ALERT_NONE)))
    if column in {"post_shipment_count", "post_shipment_total_qty"}:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0
    if column == "stock_qty":
        text = str(value or "").replace(",", "").strip()
        if not text:
            return Decimal("-1")
        try:
            return Decimal(text)
        except Exception:
            return Decimal("-1")
    if column in {"last_incoming_date", "last_ship_date"}:
        return _date_sort_key(value)
    if column == "cust_chrg_psn_cd":
        return numeric_code_sort_key(str(value or ""))
    if column == "confirmation_status":
        return confirmation_status_sort_key(row)
    return str(value or "").lower()


def sort_rows(rows: list[dict[str, object]], *, sort_specs: tuple[SortSpec, ...]) -> list[dict[str, object]]:
    sorted_rows = list(rows)
    tiebreakers = (
        SortSpec("cust_code", "asc"),
        SortSpec("item_cd", "asc"),
    )
    active_columns = {spec.column for spec in sort_specs}
    full_specs = sort_specs + tuple(spec for spec in tiebreakers if spec.column not in active_columns)
    for spec in reversed(full_specs):
        reverse = spec.direction == "desc"
        sorted_rows.sort(key=lambda row: _sort_value(row, spec.column), reverse=reverse)
    return sorted_rows


def sort_rows_legacy(rows: list[dict[str, object]], *, sort: str, direction: str) -> list[dict[str, object]]:
    return sort_rows(rows, sort_specs=(SortSpec(column=sort, direction=direction),))


def paginate_rows(rows: list[dict[str, object]], *, page: int, page_size: int) -> PaginatedRows:
    total_count = len(rows)
    total_pages = max(1, math.ceil(total_count / page_size)) if total_count else 1
    current_page = min(max(page, 1), total_pages)
    start = (current_page - 1) * page_size
    end = start + page_size
    page_rows = rows[start:end]
    return PaginatedRows(
        rows=page_rows,
        total_count=total_count,
        page=current_page,
        page_size=page_size,
        total_pages=total_pages,
        start_index=start + 1 if page_rows else 0,
        end_index=start + len(page_rows),
    )


def apply_table_display(rows: list[dict[str, object]], params: TableDisplayParams) -> PaginatedRows:
    sorted_rows = sort_rows(rows, sort_specs=params.sort_specs)
    return paginate_rows(sorted_rows, page=params.page, page_size=params.page_size)
