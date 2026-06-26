from __future__ import annotations

from urllib.parse import urlencode

from apps.asset_inventory.domain.table_display import DEFAULT_SORT_SPECS, SortSpec


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
