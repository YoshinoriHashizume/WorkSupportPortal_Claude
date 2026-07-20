from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from application.asset_inventory.domain.repositories.ports import (
    DEFAULT_PAGE_SIZE,
    PLATE_FILTER_OPTIONS,
    ListPageResult,
    ManagementRow,
    ReconcileCounts,
)
from application.asset_inventory.domain.value_objects.table_display import (
    DEFAULT_SORT_SPECS,
    SortSpec,
    TableDisplayParams,
    parse_table_display_params,
)


@dataclass(frozen=True)
class ListPageQuery:
    management_id: str
    status: str
    site_filter: str
    plate_filter: str
    asset_number_filter: str
    table_params: TableDisplayParams


def parse_list_page_query(params: dict[str, str], sites: list[str] | None = None) -> ListPageQuery:
    plate_filter = (params.get("plate") or "all").strip() or "all"
    if plate_filter not in {value for value, _label in PLATE_FILTER_OPTIONS}:
        plate_filter = "all"
    site_filter = (params.get("site") or "").strip()
    if not site_filter or site_filter == "all":
        cleaned_sites = [site.strip() for site in (sites or []) if site.strip()]
        site_filter = cleaned_sites[0] if len(cleaned_sites) == 1 else "all"
    return ListPageQuery(
        management_id=(params.get("managementId") or "").strip(),
        status=(params.get("status") or "all").strip() or "all",
        site_filter=site_filter,
        plate_filter=plate_filter,
        asset_number_filter=(params.get("assetNumber") or "").strip(),
        table_params=parse_table_display_params(params),
    )


def empty_list_page_result(
    *,
    management_rows: tuple[ManagementRow, ...] = (),
    error_message: str | None = None,
) -> ListPageResult:
    return ListPageResult(
        management_rows=management_rows,
        selected_management_id="",
        rows=(),
        all_rows=(),
        filtered_rows=(),
        counts=ReconcileCounts(),
        filtered_counts=ReconcileCounts(),
        site_options=(),
        asset_number_options=(),
        site_filter="all",
        status_filter="all",
        plate_filter="all",
        asset_number_filter="",
        page=1,
        page_size=DEFAULT_PAGE_SIZE,
        total_pages=1,
        sort_specs=DEFAULT_SORT_SPECS,
        error_message=error_message,
    )


def build_list_page_query_string(
    *,
    management_id: str,
    status: str,
    site_filter: str,
    plate_filter: str,
    asset_number_filter: str = "",
    sort_specs: tuple[SortSpec, ...],
    page: int,
    page_size: int,
) -> str:
    if not sort_specs:
        sort_specs = DEFAULT_SORT_SPECS
    params: list[tuple[str, str]] = [
        ("managementId", management_id),
        ("status", status),
        ("plate", plate_filter),
        ("sort", ",".join(spec.column for spec in sort_specs)),
        ("dir", ",".join(spec.direction for spec in sort_specs)),
        ("page", str(page)),
        ("page_size", str(page_size)),
    ]
    if site_filter and site_filter != "all":
        params.append(("site", site_filter))
    asset_number = (asset_number_filter or "").strip()
    if asset_number:
        params.append(("assetNumber", asset_number))
    return urlencode(params)
