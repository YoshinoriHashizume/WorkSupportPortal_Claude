from __future__ import annotations

from apps.asset_inventory.domain.row_detail import (
    build_attachment_proxy_path,
    build_field_comparisons,
    build_field_diffs,
    build_row_detail_payload,
)
from apps.asset_inventory.domain.ports import MatchStatus, ReconcileRow, RowTone


def test_TC_AIV_DOM_067_build_field_comparisons():
    asset = {
        "資産番号": "4527",
        "資産枝番": "0000",
        "管理部門名称": "丸栄宮崎LUNA工場",
        "メーカー": "M",
        "摘要": "A",
    }
    inventory = {
        "資産番号": "4527",
        "資産枝番": "0000",
        "管理部門名称": "丸栄宮崎MTV工場",
        "メーカー": "M",
        "摘要": "B",
    }
    comparisons = build_field_comparisons(asset, inventory)
    assert len(comparisons) == 9
    labels = [item.label for item in comparisons]
    assert labels[0] == "資産番号"
    assert labels[2] == "拠点名"
    diff_labels = [item.label for item in comparisons if item.is_diff]
    assert "拠点名" in diff_labels
    assert "摘要" in diff_labels
    assert "メーカー名" not in diff_labels


def test_TC_AIV_DOM_067a_build_field_diffs_subset():
    asset = {"管理部門名称": "A", "メーカー": "M", "摘要": "1"}
    inventory = {"管理部門名称": "B", "メーカー": "M", "摘要": "2"}
    diffs = build_field_diffs(asset, inventory)
    assert all(item.is_diff for item in diffs)
    assert len(diffs) == 2


def test_TC_AIV_DOM_068_build_row_detail_payload():
    comparisons = build_field_comparisons(
        {
            "資産番号": "4527",
            "資産枝番": "0000",
            "管理部門名称": "LUNA",
            "メーカー": "",
            "管理者名称": "",
            "型番": "",
            "旧資産番号コード": "",
            "使用区分": "",
            "摘要": "",
        },
        {
            "資産番号": "4527",
            "資産枝番": "0000",
            "管理部門名称": "MTV",
            "メーカー": "",
            "管理者名称": "",
            "型番": "",
            "旧資産番号コード": "",
            "使用区分": "",
            "摘要": "",
        },
    )
    row = ReconcileRow(
        match_status=MatchStatus.MATCHED,
        row_tone=RowTone.MATCH_FACTORY,
        status_label="棚卸済み",
        tone_label="拠点変更",
        asset_number="4527",
        branch_number="0000",
        site_name="MTV",
        manufacturer="",
        model_name="",
        serial_number="",
        old_asset_number="",
        usage_category="",
        summary="",
        plate_created="",
        inventory_operator="",
        inventory_datetime="",
        asset_photo_url="https://example.com/a.jpg",
        plate_photo_url="",
        field_comparisons=comparisons,
    )
    payload = build_row_detail_payload(row, attachment_proxy_base_path="/api/asset-inventory/attachment")
    assert payload["title"] == "4527 / 0000"
    assert payload["photos"][0]["href"].startswith("/api/asset-inventory/attachment?src=")
    assert len(payload["field_comparisons"]) == 9
    assert payload["field_comparisons"][2]["is_diff"] is True


def test_TC_AIV_DOM_069_build_attachment_proxy_path():
    href = build_attachment_proxy_path(
        "https://maruei01.dn-cloud.com/a?action=download_data_file&id=1",
        proxy_base_path="/api/asset-inventory/attachment",
    )
    assert href.startswith("/api/asset-inventory/attachment?src=")
