from __future__ import annotations

from apps.asset_inventory.domain.list_client_data import build_list_client_payload
from apps.asset_inventory.domain.ports import MatchStatus, ReconcileRow, RowTone


def _row(asset_number: str = "1") -> ReconcileRow:
    return ReconcileRow(
        match_status=MatchStatus.MATCHED,
        row_tone=RowTone.MATCH_CLEAN,
        status_label="棚卸済み",
        tone_label="一致",
        asset_number=asset_number,
        branch_number="0",
        site_name="宮崎工場",
        manufacturer="",
        model_name="",
        serial_number="",
        old_asset_number="",
        usage_category="",
        summary="",
        plate_created="",
        inventory_operator="",
        inventory_datetime="",
    )


def test_TC_AIV_DOM_07G_build_list_client_payload():
    row = _row()
    payload = build_list_client_payload(
        all_rows=(row,),
        row_details_index={"1|0": {"photos": [], "field_comparisons": []}},
        management_id="1",
        site_options=("宮崎工場",),
        asset_number_options=("1",),
        export_csv_path="/api/asset-inventory/export.csv",
    )
    assert payload["managementId"] == "1"
    assert len(payload["rows"]) == 1
    assert payload["rows"][0]["asset_number"] == "1"
    assert "1|0" in payload["rowDetails"]
    assert payload["exportCsvPath"] == "/api/asset-inventory/export.csv"
