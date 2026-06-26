from __future__ import annotations

from dataclasses import dataclass

from apps.asset_inventory.domain.list_query import build_list_page_query_string
from apps.asset_inventory.domain.ports import SORTABLE_COLUMNS
from apps.asset_inventory.domain.table_display import (
    SortSpec,
    TableDisplayParams,
    single_column_sort_specs,
)


@dataclass(frozen=True)
class TableHeader:
    key: str
    label: str
    sorted: bool
    sort_index: int | None
    direction: str
    href: str


def build_table_headers(
    *,
    table_params: TableDisplayParams,
    management_id: str,
    status: str,
    site_filter: str,
    plate_filter: str,
    asset_number_filter: str = "",
) -> tuple[TableHeader, ...]:
    sort_index_map = {spec.column: index + 1 for index, spec in enumerate(table_params.sort_specs)}
    headers: list[TableHeader] = []
    for column, label in SORTABLE_COLUMNS:
        headers.append(
            TableHeader(
                key=column,
                label=label,
                sorted=column in sort_index_map,
                sort_index=sort_index_map.get(column),
                direction=next(spec.direction for spec in table_params.sort_specs if spec.column == column)
                if column in sort_index_map
                else "",
                href="?"
                + build_list_page_query_string(
                    management_id=management_id,
                    status=status,
                    site_filter=site_filter,
                    plate_filter=plate_filter,
                    asset_number_filter=asset_number_filter,
                    sort_specs=single_column_sort_specs(table_params, column),
                    page=1,
                    page_size=table_params.page_size,
                ),
            )
        )
    return tuple(headers)
