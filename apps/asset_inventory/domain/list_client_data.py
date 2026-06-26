from __future__ import annotations

from apps.asset_inventory.domain.ports import (
    DEFAULT_PAGE_SIZE,
    PAGE_SIZE_OPTIONS,
    SORTABLE_COLUMNS,
    ReconcileRow,
)
from apps.asset_inventory.domain.reconcile_cache import reconcile_row_to_dict
from apps.asset_inventory.domain.table_display import DEFAULT_SORT_SPECS, SortSpec


def _sort_specs_to_payload(specs: tuple[SortSpec, ...]) -> list[dict[str, str]]:
    return [{"column": spec.column, "direction": spec.direction} for spec in specs]


def build_list_client_payload(
    *,
    all_rows: tuple[ReconcileRow, ...],
    row_details_index: dict[str, dict[str, object]],
    management_id: str,
    site_options: tuple[str, ...],
    asset_number_options: tuple[str, ...],
    export_csv_path: str,
) -> dict[str, object]:
    return {
        "managementId": management_id,
        "rows": [reconcile_row_to_dict(row) for row in all_rows],
        "rowDetails": row_details_index,
        "siteOptions": list(site_options),
        "assetNumberOptions": list(asset_number_options),
        "pageSizeOptions": list(PAGE_SIZE_OPTIONS),
        "defaultPageSize": DEFAULT_PAGE_SIZE,
        "sortableColumns": [{"key": key, "label": label} for key, label in SORTABLE_COLUMNS],
        "defaultSortSpecs": _sort_specs_to_payload(DEFAULT_SORT_SPECS),
        "exportCsvPath": export_csv_path,
    }
