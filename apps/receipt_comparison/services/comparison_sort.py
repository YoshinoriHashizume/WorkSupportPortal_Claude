from __future__ import annotations

from apps.receipt_comparison.services.pending_comparison import DisplayRow

VALID_SORT_DIRECTIONS = {"asc", "desc"}
DEFAULT_SORT_KEY = "receipt_flag"
DEFAULT_SORT_DIRECTION = "asc"

COMPARISON_SORT_COLUMNS: dict[str, str] = {
    "receipt_flag": "結果",
    "mari_item_cd": "品目番号(MARI)",
    "mari_date": "売上計上日(MARI)",
    "mari_qty": "売上実績数量(MARI)",
    "delivery_place": "得意先指定納品場所コード",
    "supplier_item_cd": "品番(取引先)",
    "supplier_delivery_month_day": "納入月日(取引先)",
    "supplier_qty": "納入数(取引先)",
    "supplier_cancel_qty": "キャンセル数(取引先)",
    "supplier_name": "取引先名",
    "remarks": "備考",
}


def normalize_sort_key(sort_key: str) -> str:
    normalized = (sort_key or "").strip()
    if normalized in COMPARISON_SORT_COLUMNS:
        return normalized
    return DEFAULT_SORT_KEY


def default_sort_params() -> tuple[str, str]:
    return DEFAULT_SORT_KEY, DEFAULT_SORT_DIRECTION


def resolve_sort_params(
    *,
    sort_key: str | None,
    sort_direction: str | None,
    reset_to_default: bool = False,
) -> tuple[str, str]:
    if reset_to_default or not (sort_key or "").strip():
        return default_sort_params()
    return normalize_sort_key(sort_key or ""), normalize_sort_direction(sort_direction or "asc")


def normalize_sort_direction(sort_direction: str) -> str:
    normalized = (sort_direction or "asc").strip().lower()
    if normalized in VALID_SORT_DIRECTIONS:
        return normalized
    return "asc"


def sort_display_rows(rows: list[DisplayRow], sort_key: str, sort_direction: str) -> list[DisplayRow]:
    active_key = normalize_sort_key(sort_key)
    reverse = normalize_sort_direction(sort_direction) == "desc"
    return sorted(rows, key=lambda row: sort_value(row, active_key), reverse=reverse)


def sort_value(row: DisplayRow, sort_key: str) -> object:
    value = getattr(row, sort_key, "")
    if sort_key == "receipt_flag":
        return int(value)
    if sort_key in {"mari_qty", "supplier_qty", "supplier_cancel_qty"}:
        return quantity_sort_key(value)
    return str(value or "")


def quantity_sort_key(value: object) -> tuple[int, float, str]:
    text = str(value or "").strip()
    if not text:
        return (0, 0.0, "")
    try:
        return (1, float(text), "")
    except ValueError:
        return (2, 0.0, text)


def comparison_sort_headers(sort_key: str, sort_direction: str) -> list[dict[str, object]]:
    active_key = normalize_sort_key(sort_key)
    active_direction = normalize_sort_direction(sort_direction)
    return [
        {
            "key": key,
            "label": label,
            "sort_direction": "desc" if key == active_key and active_direction == "asc" else "asc",
            "is_sorted": key == active_key,
        }
        for key, label in COMPARISON_SORT_COLUMNS.items()
    ]
