from __future__ import annotations

from application.asset_inventory.domain.value_objects.desknet_data import fetch_reconcile_source_data
from application.asset_inventory.domain.repositories.ports import ASSET_FIELDS, INVENTORY_FIELDS, ManagementRow, SITE_FIELDS


def test_TC_AIV_DOM_07B_fetch_reconcile_source_data_requests_acquisition_date_in_asset_fields():
    calls: list[tuple[str, ...] | None] = []

    def list_all(_access_key: str, app_id: str, fields: tuple[str, ...] | None) -> list[dict[str, str]]:
        calls.append(fields)
        if app_id == "415":
            return [{"生産品番⑧コード": "1", "資産番号": "1", "取得日付": "2026-03-01"}]
        return []

    management_row = ManagementRow(
        data_id="1",
        inventory_name="2025年",
        fiscal_year="2025",
        company_app_id="",
        site_app_id="site",
        asset_app_id="415",
        inventory_app_id="inv",
    )
    assets, inventory, sites = fetch_reconcile_source_data(list_all, "key", management_row)

    assert calls[0] == ASSET_FIELDS
    assert calls[1] == INVENTORY_FIELDS
    assert calls[2] == SITE_FIELDS
    assert assets[0]["取得日付"] == "2026-03-01"
    assert inventory == []
    assert sites == []
