from __future__ import annotations

from datetime import date, datetime

from apps.receipt_comparison.domain.comparison_sort import normalize_sort_direction, normalize_sort_key
from apps.receipt_comparison.domain.comparison_type import comparison_type_slug


def append_query(url: str, query: str) -> str:
    if not query:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{query}"


def parse_date(value: object) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def is_fixed_digit_code(value: object, length: int) -> bool:
    text = str(value or "").strip()
    return len(text) == length and text.isdigit()


def is_results_panel_active(
    *,
    method: str,
    get_display: str | None,
    get_compared: str | None,
    post_action: str | None,
    supplier_selected: bool,
    has_pending: bool,
) -> bool:
    if not supplier_selected:
        return False
    if has_pending:
        return True
    if method == "GET":
        return get_display == "1" or get_compared == "1"
    return post_action == "compare"


def comparison_query(
    comparison_type: str,
    supplier_id: int | None,
    start_date: date,
    end_date: date,
    *,
    display: int | None = None,
    compared: int | None = None,
    sort_key: str | None = None,
    sort_direction: str | None = None,
) -> str:
    type_slug = comparison_type_slug(comparison_type)
    parts = [
        f"type={type_slug}",
        f"start_date={start_date.isoformat()}",
        f"end_date={end_date.isoformat()}",
    ]
    if supplier_id:
        parts.append(f"supplier_id={supplier_id}")
    if display == 1:
        parts.append("display=1")
    if compared == 1:
        parts.append("compared=1")
    active_sort_key = normalize_sort_key(sort_key or "")
    active_sort_direction = normalize_sort_direction(sort_direction or "asc")
    parts.append(f"sort={active_sort_key}")
    parts.append(f"dir={active_sort_direction}")
    return "&".join(parts)


def comparison_url_path(
    comparison_base_path: str,
    comparison_type: str,
    supplier_id: int,
    start_date: date,
    end_date: date,
    *,
    display: int | None = None,
    compared: int | None = None,
    sort_key: str | None = None,
    sort_direction: str | None = None,
) -> str:
    query = comparison_query(
        comparison_type,
        supplier_id,
        start_date,
        end_date,
        display=display,
        compared=compared,
        sort_key=sort_key,
        sort_direction=sort_direction,
    )
    return f"{comparison_base_path}?{query}"


def settings_redirect_path(settings_base_path: str, type_slug: str, supplier_id: object = None) -> str:
    url = f"{settings_base_path}?type={type_slug}"
    if supplier_id:
        url += f"&supplier_id={supplier_id}"
    return url
