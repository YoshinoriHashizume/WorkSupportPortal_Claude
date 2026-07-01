from __future__ import annotations

from collections.abc import Callable, Iterable

NormalizeFn = Callable[[str], str]


def default_normalize_prefix_value(value: str) -> str:
    return value.strip()


def filter_prefix_options(
    options: tuple[str, ...],
    query: str,
    *,
    normalize: NormalizeFn | None = None,
) -> tuple[str, ...]:
    normalize_fn = normalize or default_normalize_prefix_value
    query_norm = normalize_fn(query)
    if not query_norm:
        return options
    return tuple(
        option
        for option in options
        if normalize_fn(option).startswith(query_norm)
    )


def matches_prefix_filter(
    target_value: str,
    filter_value: str,
    *,
    normalize: NormalizeFn | None = None,
) -> bool:
    normalize_fn = normalize or default_normalize_prefix_value
    query = normalize_fn(filter_value)
    if not query:
        return True
    row_value = normalize_fn(str(target_value or ""))
    if not row_value:
        return False
    return row_value.startswith(query)


def extract_distinct_values(
    raw_values: Iterable[str],
    *,
    normalize: NormalizeFn | None = None,
) -> tuple[str, ...]:
    normalize_fn = normalize or default_normalize_prefix_value
    seen: set[str] = set()
    collected: list[str] = []
    for raw in raw_values:
        display = str(raw or "").strip()
        if not display:
            continue
        value = normalize_fn(display)
        if value and value not in seen:
            seen.add(value)
            collected.append(value)
    return tuple(sorted(collected))


def extract_distinct_values_from_rows(
    rows: list[dict[str, object]],
    column_key: str,
    *,
    normalize: NormalizeFn | None = None,
) -> tuple[str, ...]:
    return extract_distinct_values(
        (str(row.get(column_key) or "") for row in rows),
        normalize=normalize,
    )
