from __future__ import annotations

from applications.asset_inventory.domain.ports import (
    ASSET_INVENTORY_TARGET_CODE,
    ASSET_INVENTORY_TARGET_FIELD,
    Record,
)


def is_inventory_target_asset(record: Record) -> bool:
    return (record.get(ASSET_INVENTORY_TARGET_FIELD) or "").strip() == ASSET_INVENTORY_TARGET_CODE


def filter_inventory_target_assets(records: list[Record]) -> list[Record]:
    return [record for record in records if is_inventory_target_asset(record)]
