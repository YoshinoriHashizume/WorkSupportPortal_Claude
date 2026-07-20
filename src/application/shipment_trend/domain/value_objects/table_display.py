from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from application.portal.domain.value_objects.list_table import (
    DEFAULT_PAGE_SIZE,
    PAGE_SIZE_OPTIONS,
    PaginatedRows,
    SortSpec,
    build_table_query_string,
    paginate_rows,
    parse_sort_specs,
    sort_spec_label,
)

SORTABLE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("cust_chrg_psn_cd", "担当者コード"),
    ("cust_code", "得意先コード"),
    ("cust_name", "得意先名"),
    ("item_cd", "得意先品番"),
    ("first_fiscal_year", "初年度"),
    ("first_fy_total", "初年度出荷合計"),
    ("prev_fy_total", "前年度出荷合計"),
    ("current_fy_with_forecast_total", "今年度出荷+予測"),
    ("change_rate_pct", "変動率"),
    ("change_qty", "変動数"),
)

QUANTITY_COLUMNS = frozenset(
    {
        "first_fy_total",
        "prev_fy_total",
        "current_fy_with_forecast_total",
        "change_qty",
    }
)

DEFAULT_SORT = "change_rate_pct"
DEFAULT_DIRECTION = "asc"  # 変動率昇順 = マイナス幅が大きい順（例: -50% → -10% → 0% → +10%）
DEFAULT_SORT_SPECS: tuple[SortSpec, ...] = (
    SortSpec(DEFAULT_SORT, DEFAULT_DIRECTION),
    SortSpec("change_qty", "asc"),
)
SORTABLE_KEYS = {column for column, _label in SORTABLE_COLUMNS}
COLUMN_LABELS = dict(SORTABLE_COLUMNS)


def default_direction_for_column(column: str) -> str:
    if column in {"change_rate_pct", "change_qty"} or column in QUANTITY_COLUMNS:
        return "asc"
    return "asc"


def parse_table_display_params(params: dict[str, str]) -> tuple[SortSpec, ...]:
    return parse_sort_specs(
        params,
        sortable_keys=SORTABLE_KEYS,
        default_specs=DEFAULT_SORT_SPECS,
        default_direction_for_column=default_direction_for_column,
        default_sort=DEFAULT_SORT,
        default_direction=DEFAULT_DIRECTION,
    )


def _sort_key_for_column(column: str) -> Callable[[dict[str, object]], object]:
    if column == "first_fiscal_year":

        def year_key(row: dict[str, object]) -> tuple[int, int]:
            value = row.get("first_fiscal_year")
            if value is None:
                return (1, 0)
            return (0, int(value))

        return year_key

    if column == "change_rate_pct":

        def rate_key(row: dict[str, object]) -> tuple[int, float]:
            value = row.get("change_rate_pct")
            if value is None:
                return (1, 0.0)
            return (0, float(value))

        return rate_key

    if column in QUANTITY_COLUMNS:

        def qty_key(row: dict[str, object]) -> int:
            return int(row.get(column) or 0)

        return qty_key

    def text_key(row: dict[str, object]) -> str:
        return str(row.get(column) or "").strip().lower()

    return text_key


def sort_rows(rows: list[dict[str, object]], sort_specs: tuple[SortSpec, ...]) -> list[dict[str, object]]:
    sorted_rows = list(rows)
    for spec in reversed(sort_specs):
        key_fn = _sort_key_for_column(spec.column)
        sorted_rows.sort(key=key_fn, reverse=spec.direction == "desc")
    return sorted_rows


def apply_table_display(
    rows: list[dict[str, object]],
    *,
    sort_specs: tuple[SortSpec, ...],
    page: int,
    page_size: int,
) -> PaginatedRows:
    sorted_rows = sort_rows(rows, sort_specs)
    return paginate_rows(sorted_rows, page=page, page_size=page_size)


def parse_page_params(params: dict[str, str]) -> tuple[int, int]:
    try:
        page = int(params.get("page") or "1")
    except ValueError:
        page = 1
    try:
        page_size = int(params.get("page_size") or str(DEFAULT_PAGE_SIZE))
    except ValueError:
        page_size = DEFAULT_PAGE_SIZE
    if page_size not in PAGE_SIZE_OPTIONS:
        page_size = DEFAULT_PAGE_SIZE
    return max(page, 1), page_size


def format_fiscal_year(value: object) -> str:
    if value is None:
        return "—"
    return str(int(value))


def format_change_rate(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, Decimal):
        number = float(value)
    else:
        number = float(value)
    sign = "+" if number > 0 else ""
    return f"{sign}{number:.2f}%"


def format_change_qty(value: object) -> str:
    return format_quantity(value)


def format_quantity(value: object) -> str:
    return f"{int(value or 0):,}"


def build_sort_links(
    *,
    base_path: str,
    sort_specs: tuple[SortSpec, ...],
    page: int,
    page_size: int,
    filter_query: str,
) -> list[dict[str, object]]:
    headers: list[dict[str, object]] = []
    for column, label in SORTABLE_COLUMNS:
        current_index = next((index for index, spec in enumerate(sort_specs) if spec.column == column), None)
        direction = sort_specs[current_index].direction if current_index is not None else default_direction_for_column(column)
        next_direction = "desc" if direction == "asc" else "asc"
        next_specs = (SortSpec(column, next_direction),)
        extra_query = filter_query
        query = build_table_query_string(
            sort_specs=next_specs,
            page=page,
            page_size=page_size,
        )
        href = f"{base_path}?{query}"
        if extra_query:
            href = f"{href}&{extra_query}"
        headers.append(
            {
                "key": column,
                "label": label,
                "sorted": current_index is not None,
                "sort_index": current_index,
                "direction": direction if current_index is not None else "",
                "href": href,
            }
        )
    return headers


def sort_spec_labels(sort_specs: tuple[SortSpec, ...]) -> list[str]:
    return [sort_spec_label(spec, column_labels=COLUMN_LABELS) for spec in sort_specs]
