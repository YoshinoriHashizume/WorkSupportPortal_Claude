from __future__ import annotations

from application.asset_inventory.domain.value_objects.asset_filter import filter_inventory_target_assets
from application.asset_inventory.domain.repositories.ports import (
    ASSET_FIELDS,
    INVENTORY_FIELDS,
    MANAGEMENT_APP_ID,
    MANAGEMENT_FIELDS,
    SITE_FIELDS,
    ListAllRecordsFn,
    ManagementRow,
    Record,
)
from application.asset_inventory.domain.value_objects.errors import (
    DesknetAccessKeyMissingError,
    DesknetApiError,
)

# 拠点マスタのみ取得に失敗した場合に一覧上部へ併記する警告（機能仕様書 §7.4.1）
SITE_MASTER_UNAVAILABLE_MESSAGE = "拠点マスタを取得できませんでした。工場変化の判定は管理部門コードの直接比較で行います。"


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
) -> tuple[list[Record], list[Record], list[Record], str]:
    """資産・棚卸・拠点マスタを取得する。

    戻り値の 4 要素目は拠点マスタの取得に失敗した場合の警告文（成功時は空文字）。
    拠点マスタのみの失敗では突合を止めず、§5.5 のフォールバック（管理部門コードの
    直接比較）で工場変化を判定する（機能仕様書 §7.4.1）。
    """
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
    sites: list[Record] = []
    site_warning = ""
    if management_row.site_app_id:
        try:
            sites = list_all(access_key, management_row.site_app_id, SITE_FIELDS)
        except DesknetAccessKeyMissingError:
            # アクセスキー欠落・期限切れは縮退させず 503 として扱う（§7.4）
            raise
        except DesknetApiError:
            site_warning = SITE_MASTER_UNAVAILABLE_MESSAGE
    return assets, inventory, sites, site_warning
