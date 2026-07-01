from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from applications.inventory_order_alert.domain.code_sort import numeric_code_sort_key
from applications.inventory_order_alert.domain.table_display import SortSpec, TableDisplayParams
from applications.portal.domain.dependent_cust_filter import (
    build_cust_chrg_cust_index,
    cust_options_for_chrg_psn,
    sanitize_cust_code,
)
from applications.portal.domain.prefix_filter import (
    extract_distinct_values_from_rows,
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
    level1_item_cd_options: tuple[str, ...]
    cust_chrg_cust_index: dict[str, dict[str, str]]

    @classmethod
    def empty(cls) -> ListFilterOptions:
        return cls(
            cust_options=(),
            cust_chrg_psn_options=(),
            item_cd_options=(),
            level1_item_cd_options=(),
            cust_chrg_cust_index={},
        )


@dataclass(frozen=True)
class ListFilterParams:
    cust_code: str = ""
    cust_chrg_psn_cd: str = ""
    item_cd: str = ""
    level1_item_cd: str = ""


def matches_item_cd_filter(item_cd: str, item_cd_filter: str) -> bool:
    return matches_prefix_filter(item_cd, item_cd_filter)


def matches_level1_item_cd_filter(level1_item_cd: str, level1_item_cd_filter: str) -> bool:
    return matches_prefix_filter(level1_item_cd, level1_item_cd_filter)


def build_filter_options(rows: list[dict[str, object]]) -> ListFilterOptions:
    cust_labels: dict[str, str] = {}
    chrg_codes: set[str] = set()
    for row in rows:
        cust_code = str(row.get("cust_code") or "").strip()
        cust_name = str(row.get("cust_name") or "").strip()
        if cust_code:
            cust_labels.setdefault(cust_code, cust_name)
        chrg_code = str(row.get("cust_chrg_psn_cd") or "").strip()
        if chrg_code:
            chrg_codes.add(chrg_code)

    cust_options = tuple(
        FilterOption(
            value=code,
            label=f"{code} - {name}" if name else code,
        )
        for code, name in sorted(cust_labels.items(), key=lambda item: item[0])
    )
    cust_chrg_psn_options = tuple(
        FilterOption(value=code, label=code)
        for code in sorted(chrg_codes, key=numeric_code_sort_key)
    )
    item_cd_options = extract_distinct_values_from_rows(rows, "item_cd")
    level1_item_cd_options = extract_distinct_values_from_rows(rows, "level1_item_cd")
    return ListFilterOptions(
        cust_options=cust_options,
        cust_chrg_psn_options=cust_chrg_psn_options,
        item_cd_options=item_cd_options,
        level1_item_cd_options=level1_item_cd_options,
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
    level1_item_cd = (params.get("level1_item_cd") or "").strip()
    return ListFilterParams(
        cust_code=cust_code,
        cust_chrg_psn_cd=cust_chrg_psn_cd,
        item_cd=item_cd,
        level1_item_cd=level1_item_cd,
    )


def list_filter_params_from_client_payload(payload: dict[str, object]) -> ListFilterParams:
    return ListFilterParams(
        cust_code=str(payload.get("custCodeFilter") or "").strip(),
        cust_chrg_psn_cd=str(payload.get("custChrgPsnCdFilter") or "").strip(),
        item_cd=str(payload.get("itemCdFilter") or "").strip(),
        level1_item_cd=str(payload.get("level1ItemCdFilter") or "").strip(),
    )


def apply_list_filters(rows: list[dict[str, object]], params: ListFilterParams) -> list[dict[str, object]]:
    filtered = rows
    if params.cust_code:
        filtered = [row for row in filtered if str(row.get("cust_code") or "").strip() == params.cust_code]
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
    if params.level1_item_cd:
        filtered = [
            row
            for row in filtered
            if matches_level1_item_cd_filter(str(row.get("level1_item_cd") or ""), params.level1_item_cd)
        ]
    return filtered


def build_display_query_string(
    *,
    table_params: TableDisplayParams,
    filter_params: ListFilterParams,
    page: int | None = None,
    sort_specs: tuple[SortSpec, ...] | None = None,
    page_size: int | None = None,
) -> str:
    specs = sort_specs if sort_specs is not None else table_params.sort_specs
    query: dict[str, str | int] = {
        "sort": ",".join(spec.column for spec in specs),
        "dir": ",".join(spec.direction for spec in specs),
        "page": page if page is not None else table_params.page,
        "page_size": page_size if page_size is not None else table_params.page_size,
    }
    if filter_params.cust_code:
        query["cust_code"] = filter_params.cust_code
    if filter_params.cust_chrg_psn_cd:
        query["cust_chrg_psn_cd"] = filter_params.cust_chrg_psn_cd
    if filter_params.item_cd:
        query["item_cd"] = filter_params.item_cd
    if filter_params.level1_item_cd:
        query["level1_item_cd"] = filter_params.level1_item_cd
    return urlencode(query)
