from __future__ import annotations

from application.asset_inventory.domain.value_objects.inventory_dedup import dedupe_inventory_records
from application.asset_inventory.domain.value_objects.field_compare import (
    build_site_code_map,
    has_factory_change,
    has_field_diff,
)
from application.asset_inventory.domain.value_objects.row_display import derive_row_tone, map_record_to_display
from application.asset_inventory.domain.value_objects.match_key import build_match_key
from application.asset_inventory.domain.repositories.ports import (
    MatchStatus,
    ReconcileCounts,
    ReconcileRow,
    Record,
    RowTone,
)


def reconcile_records(
    asset_records: list[Record],
    inventory_records: list[Record],
    site_records: list[Record],
) -> tuple[tuple[ReconcileRow, ...], ReconcileCounts]:
    site_code_map = build_site_code_map(site_records)
    assets_by_key = {build_match_key(r.get("資産番号", ""), r.get("資産枝番", "")): r for r in asset_records}
    inventory_by_key = dedupe_inventory_records(inventory_records)

    all_keys = sorted(set(assets_by_key) | set(inventory_by_key))
    rows: list[ReconcileRow] = []
    counts = ReconcileCounts()

    for key in all_keys:
        asset_row = assets_by_key.get(key)
        inventory_row = inventory_by_key.get(key)

        if asset_row and inventory_row:
            status = MatchStatus.MATCHED
            counts.matched += 1
            diff = has_field_diff(asset_row, inventory_row)
            factory = diff and has_factory_change(asset_row, inventory_row, site_code_map)
            tone = derive_row_tone(status, diff, factory)
            display_source = inventory_row
            row = map_record_to_display(
                display_source,
                status=status,
                row_tone=tone,
                has_diff=diff,
                factory_change=factory,
                asset_row=asset_row,
                inventory_row=inventory_row,
                photo_source=inventory_row,
            )
        elif asset_row:
            status = MatchStatus.ASSET_ONLY
            counts.asset_only += 1
            tone = derive_row_tone(status, False, False)
            row = map_record_to_display(
                asset_row,
                status=status,
                row_tone=tone,
                has_diff=False,
                factory_change=False,
                empty_inventory_fields=True,
                asset_row=asset_row,
            )
        else:
            status = MatchStatus.INVENTORY_ONLY
            counts.inventory_only += 1
            tone = derive_row_tone(status, False, False)
            display_source = inventory_row or {}
            row = map_record_to_display(
                display_source,
                status=status,
                row_tone=tone,
                has_diff=False,
                factory_change=False,
                inventory_row=display_source,
                photo_source=display_source,
            )

        rows.append(row)

    return tuple(rows), counts
