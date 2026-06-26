from __future__ import annotations

from apps.asset_inventory.domain.asset_filter import filter_inventory_target_assets
from apps.asset_inventory.domain.ports import (
    ASSET_FIELDS,
    INVENTORY_FIELDS,
    MANAGEMENT_APP_ID,
    MANAGEMENT_FIELDS,
    SITE_FIELDS,
    ListAllRecordsFn,
    ManagementRow,
    Record,
)


def parse_management_row(record: Record) -> ManagementRow:
    return ManagementRow(
        data_id=record.get("データID", ""),
        inventory_name=record.get("棚卸項目", ""),
        fiscal_year=record.get("年度", ""),
        company_app_id=record.get("会社マスタ", ""),
        site_app_id=record.get("拠点マスタ", ""),
        asset_app_id=record.get("資産データ", ""),
        inventory_app_id=record.get("棚卸データ", ""),
    )


def list_management_rows(
    list_all: ListAllRecordsFn,
    access_key: str,
) -> list[ManagementRow]:
    records = list_all(access_key, MANAGEMENT_APP_ID, MANAGEMENT_FIELDS)
    rows = [parse_management_row(record) for record in records]
    return sorted(rows, key=lambda row: (row.inventory_name, row.data_id))


def fetch_reconcile_source_data(
    list_all: ListAllRecordsFn,
    access_key: str,
    management_row: ManagementRow,
) -> tuple[list[Record], list[Record], list[Record]]:
    assets = (
        filter_inventory_target_assets(
            list_all(access_key, management_row.asset_app_id, ASSET_FIELDS),
        )
        if management_row.asset_app_id
        else []
    )
    inventory = (
        list_all(access_key, management_row.inventory_app_id, INVENTORY_FIELDS)
        if management_row.inventory_app_id
        else []
    )
    sites = list_all(access_key, management_row.site_app_id, SITE_FIELDS) if management_row.site_app_id else []
    return assets, inventory, sites
