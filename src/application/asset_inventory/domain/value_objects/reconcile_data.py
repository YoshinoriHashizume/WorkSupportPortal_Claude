from __future__ import annotations

from application.asset_inventory.domain.value_objects.desknet_data import fetch_reconcile_source_data
from application.asset_inventory.domain.value_objects.list_filter import extract_asset_numbers_from_rows, extract_site_names_from_assets
from application.asset_inventory.domain.repositories.ports import ListAllRecordsFn, ManagementRow, ReconcileCounts
from application.asset_inventory.domain.value_objects.reconcile import reconcile_records
from application.asset_inventory.domain.value_objects.reconcile_cache import ReconcileCache, save_reconcile_cache


def load_reconciled_data(
    list_all: ListAllRecordsFn,
    access_key: str,
    selected: ManagementRow,
    *,
    session: dict | None,
) -> ReconcileCache:
    from application.asset_inventory.domain.value_objects.reconcile_cache import load_reconcile_cache

    if session is not None:
        cached = load_reconcile_cache(session)
        if cached is not None and cached.management_id == selected.data_id:
            return cached

    assets, inventory, sites = fetch_reconcile_source_data(list_all, access_key, selected)
    all_rows, counts = reconcile_records(assets, inventory, sites)
    cache = ReconcileCache(
        management_id=selected.data_id,
        rows=all_rows,
        counts=counts,
        site_options=extract_site_names_from_assets(assets),
        asset_number_options=extract_asset_numbers_from_rows(all_rows),
    )
    if session is not None:
        save_reconcile_cache(session, cache)
    return cache
