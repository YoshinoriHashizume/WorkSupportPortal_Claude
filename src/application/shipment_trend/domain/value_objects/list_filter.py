from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from application.portal.domain.value_objects.code_sort import numeric_code_sort_key
from application.portal.domain.value_objects.dependent_cust_filter import (
    build_cust_chrg_cust_index,
    cust_options_for_chrg_psn,
    sanitize_cust_code,
)
from application.portal.domain.value_objects.prefix_filter import (
    extract_distinct_values_from_rows,
    filter_prefix_options,
    matches_prefix_filter,
)


@dataclass(frozen=True)
class FilterOption:
    value: str
    label: str


@dataclass(frozen=True)
class ListFilterOptions:
    cust_options: tuple[FilterOption, ...]
    cust_chrg_psn_options: tuple[FilterOption, ...]
    item_cd_options: tuple[str, ...]
    cust_chrg_cust_index: dict[str, dict[str, str]]

    @classmethod
    def empty(cls) -> ListFilterOptions:
        return cls(cust_options=(), cust_chrg_psn_options=(), item_cd_options=(), cust_chrg_cust_index={})


@dataclass(frozen=True)
class ListFilterParams:
    cust_code: str = ""
    cust_chrg_psn_cd: str = ""
    item_cd: str = ""


def normalize_item_cd_filter(value: str) -> str:
    return value.strip()


def filter_item_cd_options(options: tuple[str, ...], query: str) -> tuple[str, ...]:
    return filter_prefix_options(options, query)


def matches_item_cd_filter(item_cd: str, item_cd_filter: str) -> bool:
    return matches_prefix_filter(item_cd, item_cd_filter)


def build_filter_options(rows: list[dict[str, object]]) -> ListFilterOptions:
    cust_codes: dict[str, str] = {}
    chrg_codes: set[str] = set()
    for row in rows:
        cust_code = str(row.get("cust_code") or "").strip()
        cust_name = str(row.get("cust_name") or "").strip()
        chrg_code = str(row.get("cust_chrg_psn_cd") or "").strip()
        if cust_code:
            cust_codes[cust_code] = cust_name
        if chrg_code:
            chrg_codes.add(chrg_code)

    cust_options = tuple(
        FilterOption(value=code, label=f"{code} - {name}" if name else code)
        for code, name in sorted(cust_codes.items())
    )
    cust_chrg_psn_options = tuple(
        FilterOption(value=code, label=code)
        for code in sorted(chrg_codes, key=numeric_code_sort_key)
    )
    item_cd_options = extract_distinct_values_from_rows(rows, "item_cd")
    return ListFilterOptions(
        cust_options=cust_options,
        cust_chrg_psn_options=cust_chrg_psn_options,
        item_cd_options=item_cd_options,
        cust_chrg_cust_index=build_cust_chrg_cust_index(rows),
    )


def visible_cust_options(
    options: ListFilterOptions,
    cust_chrg_psn_cd: str,
) -> tuple[FilterOption, ...]:
    filtered = cust_options_for_chrg_psn(
        options.cust_options,
        options.cust_chrg_cust_index,
        cust_chrg_psn_cd,
    )
    return tuple(FilterOption(value=option.value, label=option.label) for option in filtered)


def parse_list_filter_params(
    params: dict[str, str],
    options: ListFilterOptions,
) -> ListFilterParams:
    valid_chrg = {option.value for option in options.cust_chrg_psn_options}
    cust_code = (params.get("cust_code") or "").strip()
    cust_chrg_psn_cd = (params.get("cust_chrg_psn_cd") or "").strip()
    if cust_chrg_psn_cd and cust_chrg_psn_cd not in valid_chrg:
        cust_chrg_psn_cd = ""
    visible_cust = visible_cust_options(options, cust_chrg_psn_cd)
    cust_code = sanitize_cust_code(cust_code, visible_cust)
    item_cd = (params.get("item_cd") or "").strip()
    return ListFilterParams(cust_code=cust_code, cust_chrg_psn_cd=cust_chrg_psn_cd, item_cd=item_cd)


def apply_list_filters(rows: list[dict[str, object]], params: ListFilterParams) -> list[dict[str, object]]:
    filtered = rows
    if params.cust_code:
        filtered = [
            row for row in filtered if str(row.get("cust_code") or "").strip() == params.cust_code
        ]
    if params.cust_chrg_psn_cd:
        filtered = [
            row
            for row in filtered
            if str(row.get("cust_chrg_psn_cd") or "").strip() == params.cust_chrg_psn_cd
        ]
    if params.item_cd:
        filtered = [
            row
            for row in filtered
            if matches_item_cd_filter(str(row.get("item_cd") or ""), params.item_cd)
        ]
    return filtered


def build_display_query_string(
    *,
    filter_params: ListFilterParams,
    sort_query: str,
) -> str:
    query: dict[str, str] = {}
    if filter_params.cust_code:
        query["cust_code"] = filter_params.cust_code
    if filter_params.cust_chrg_psn_cd:
        query["cust_chrg_psn_cd"] = filter_params.cust_chrg_psn_cd
    if filter_params.item_cd:
        query["item_cd"] = filter_params.item_cd
    if sort_query:
        for part in sort_query.split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                query[key] = value
    return urlencode(query)
