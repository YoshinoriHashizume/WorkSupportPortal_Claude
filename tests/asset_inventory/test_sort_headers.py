from __future__ import annotations

from apps.asset_inventory.domain.sort_headers import TableHeader, build_table_headers
from apps.asset_inventory.domain.table_display import SortSpec, TableDisplayParams


def test_TC_AIV_DOM_085_build_table_headers():
    table_params = TableDisplayParams(
        sort_specs=(SortSpec("asset_number", "asc"),),
        page=1,
        page_size=50,
    )
    headers = build_table_headers(
        table_params=table_params,
        management_id="1",
        status="all",
        site_filter="all",
        plate_filter="all",
    )
    assert len(headers) == 15
    asset_header = next(header for header in headers if header.key == "asset_number")
    assert isinstance(asset_header, TableHeader)
    assert asset_header.sorted is True
    assert asset_header.sort_index == 1
    assert asset_header.direction == "asc"
    assert "sort=asset_number" in asset_header.href
    assert "dir=desc" in asset_header.href


def test_TC_AIV_DOM_093_build_table_headers_multi_sort_index():
    table_params = TableDisplayParams(
        sort_specs=(
            SortSpec("status_label", "asc"),
            SortSpec("asset_number", "desc"),
        ),
        page=1,
        page_size=50,
    )
    headers = build_table_headers(
        table_params=table_params,
        management_id="1",
        status="all",
        site_filter="all",
        plate_filter="all",
    )
    status_header = next(header for header in headers if header.key == "status_label")
    asset_header = next(header for header in headers if header.key == "asset_number")
    assert status_header.sort_index == 1
    assert asset_header.sort_index == 2
