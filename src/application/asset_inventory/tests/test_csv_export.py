from __future__ import annotations

from application.asset_inventory.domain.value_objects.csv_export import render_export_csv
from application.asset_inventory.domain.repositories.ports import MatchStatus, ReconcileRow, RowTone


def _sample_row() -> ReconcileRow:
    return ReconcileRow(
        match_status=MatchStatus.MATCHED,
        row_tone=RowTone.MATCH_CLEAN,
        status_label="棚卸済み",
        tone_label="一致",
        asset_number="5262",
        branch_number="0001",
        site_name="宮崎工場",
        manufacturer="M",
        model_name="MODEL",
        serial_number="SN",
        old_asset_number="OLD",
        usage_category="使用",
        summary="摘要",
        plate_created="プレート有",
        plate_created_code="0",
        inventory_operator="担当",
        inventory_datetime="2026/01/16 18:46:01",
        css_class="aiv-row-clean",
    )


def test_TC_AIV_DOM_060_utf8_bom():
    content = render_export_csv((_sample_row(),))
    assert content.startswith(b"\xef\xbb\xbf")


def test_TC_AIV_DOM_061_csv_headers():
    content = render_export_csv((_sample_row(),)).decode("utf-8-sig")
    first_line = content.splitlines()[0]
    assert "棚卸結果" in first_line
    assert "変化状況" in first_line
    assert "行色区分" not in first_line
    assert "資産番号" in first_line
