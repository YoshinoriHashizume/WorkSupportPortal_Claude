from __future__ import annotations

from apps.asset_inventory.domain.ports import MatchStatus, RowTone, TONE_LABELS
from apps.asset_inventory.domain.row_display import derive_row_tone, map_record_to_display


RECORD = {
    "資産番号": "5262",
    "資産枝番": "0001",
    "管理部門名称": "宮崎工場",
    "メーカー": "M",
    "管理者名称": "MODEL",
    "型番": "SN",
    "旧資産番号コード": "OLD",
    "使用区分": "使用",
    "摘要": "A",
    "プレート作成": "済",
    "棚卸実施者": "担当",
    "棚卸日時": "2026/01/16 18:46:01",
}


def test_TC_AIV_DOM_040_match_clean_tone():
    assert derive_row_tone(MatchStatus.MATCHED, False, False) == RowTone.MATCH_CLEAN


def test_TC_AIV_DOM_041_match_diff_tone():
    assert derive_row_tone(MatchStatus.MATCHED, True, False) == RowTone.MATCH_DIFF


def test_TC_AIV_DOM_042_factory_tone():
    assert derive_row_tone(MatchStatus.MATCHED, True, True) == RowTone.MATCH_FACTORY


def test_TC_AIV_DOM_043_unmatched_no_tone():
    assert derive_row_tone(MatchStatus.ASSET_ONLY, False, False) == RowTone.NONE


def test_TC_AIV_DOM_050_css_class_clean():
    row = map_record_to_display(
        RECORD,
        status=MatchStatus.MATCHED,
        row_tone=RowTone.MATCH_CLEAN,
        has_diff=False,
        factory_change=False,
    )
    assert row.css_class == "aiv-row-clean"
    assert row.status_label == "棚卸済み"


def test_TC_AIV_DOM_051_asset_only_empty_inventory_fields():
    row = map_record_to_display(
        RECORD,
        status=MatchStatus.ASSET_ONLY,
        row_tone=RowTone.NONE,
        has_diff=False,
        factory_change=False,
        empty_inventory_fields=True,
    )
    assert row.inventory_operator == ""
    assert row.inventory_datetime == ""
    assert row.plate_created == ""
    assert row.plate_created_code == ""
    assert row.status_label == "未棚卸"


def test_TC_AIV_DOM_052_plate_created_labels():
    row = map_record_to_display(
        {**RECORD, "プレート作成": "0"},
        status=MatchStatus.MATCHED,
        row_tone=RowTone.MATCH_CLEAN,
        has_diff=False,
        factory_change=False,
    )
    assert row.plate_created == "プレート有"
    assert row.plate_created_code == "0"


def test_TC_AIV_DOM_053_css_class_diff():
    row = map_record_to_display(
        RECORD,
        status=MatchStatus.MATCHED,
        row_tone=RowTone.MATCH_DIFF,
        has_diff=True,
        factory_change=False,
    )
    assert row.css_class == "aiv-row-diff"


def test_TC_AIV_DOM_054_css_class_factory():
    row = map_record_to_display(
        RECORD,
        status=MatchStatus.MATCHED,
        row_tone=RowTone.MATCH_FACTORY,
        has_diff=True,
        factory_change=True,
    )
    assert row.css_class == "aiv-row-factory"


def test_TC_AIV_DOM_055_tone_labels():
    assert TONE_LABELS[RowTone.MATCH_CLEAN] == "一致"
    assert TONE_LABELS[RowTone.MATCH_FACTORY] == "拠点変更"
    assert TONE_LABELS[RowTone.MATCH_DIFF] == "差異"
    assert TONE_LABELS[RowTone.NONE] == "未突合"


def test_TC_AIV_DOM_056_map_record_tone_labels():
    diff_row = map_record_to_display(
        RECORD,
        status=MatchStatus.MATCHED,
        row_tone=RowTone.MATCH_DIFF,
        has_diff=True,
        factory_change=False,
    )
    assert diff_row.tone_label == "差異"

    factory_row = map_record_to_display(
        RECORD,
        status=MatchStatus.MATCHED,
        row_tone=RowTone.MATCH_FACTORY,
        has_diff=True,
        factory_change=True,
    )
    assert factory_row.tone_label == "拠点変更"
