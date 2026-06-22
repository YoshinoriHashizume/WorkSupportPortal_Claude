from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from apps.inventory_order_alert.application.table_display import SortSpec, TableDisplayParams
from apps.inventory_order_alert.domain.code_sort import numeric_code_sort_key


@dataclass(frozen=True)
class FilterOption:
    value: str
    label: str


@dataclass(frozen=True)
class ListFilterOptions:
    cust_options: tuple[FilterOption, ...]
    cust_chrg_psn_options: tuple[FilterOption, ...]

    @classmethod
    def empty(cls) -> ListFilterOptions:
        return cls(cust_options=(), cust_chrg_psn_options=())


@dataclass(frozen=True)
class ListFilterParams:
    cust_code: str = ""
    cust_chrg_psn_cd: str = ""


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
    return ListFilterOptions(
        cust_options=cust_options,
        cust_chrg_psn_options=cust_chrg_psn_options,
    )


def parse_list_filter_params(
    params: dict[str, str],
    options: ListFilterOptions,
) -> ListFilterParams:
    valid_cust = {option.value for option in options.cust_options}
    valid_chrg = {option.value for option in options.cust_chrg_psn_options}
    cust_code = (params.get("cust_code") or "").strip()
    cust_chrg_psn_cd = (params.get("cust_chrg_psn_cd") or "").strip()
    if cust_code and cust_code not in valid_cust:
        cust_code = ""
    if cust_chrg_psn_cd and cust_chrg_psn_cd not in valid_chrg:
        cust_chrg_psn_cd = ""
    return ListFilterParams(cust_code=cust_code, cust_chrg_psn_cd=cust_chrg_psn_cd)


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
    return urlencode(query)
