from __future__ import annotations

import pytest

from application.asset_inventory.domain.value_objects.field_compare import (
    build_site_code_map,
    has_factory_change,
    has_field_diff,
)
from application.asset_inventory.domain.repositories.ports import MatchStatus, RowTone
from application.asset_inventory.domain.value_objects.reconcile import reconcile_records
from application.asset_inventory.domain.value_objects.row_display import derive_row_tone


ASSET = {
    "資産番号": "5262",
    "資産枝番": "0001",
    "管理部門名称": "宮崎工場",
    "管理部門コード": "001",
    "メーカー": "M",
    "管理者名称": "MODEL",
    "型番": "SN1",
    "旧資産番号コード": "OLD",
    "使用区分": "使用",
    "摘要": "A",
}

INVENTORY_MATCH = {**ASSET, "棚卸日時": "2026/01/16 18:46:01", "棚卸実施者": "担当", "プレート作成": "済"}

SITES = [
    {"データID": "S1", "管理部門コード": "001", "拠点名": "宮崎工場"},
    {"データID": "S2", "管理部門コード": "002", "拠点名": "本社"},
]


def test_TC_AIV_DOM_020_asset_only():
    rows, counts = reconcile_records([ASSET], [], SITES)
    assert counts.asset_only == 1
    assert rows[0].status_label == "未棚卸"


def test_TC_AIV_DOM_021_inventory_only():
    rows, counts = reconcile_records([], [INVENTORY_MATCH], SITES)
    assert counts.inventory_only == 1
    assert rows[0].status_label == "台帳外"


def test_TC_AIV_DOM_022_matched():
    rows, counts = reconcile_records([ASSET], [INVENTORY_MATCH], SITES)
    assert counts.matched == 1
    assert rows[0].status_label == "棚卸済み"


def test_TC_AIV_DOM_023_l_prefix_match():
    asset = {**ASSET, "資産番号": "L5262"}
    inv = {**INVENTORY_MATCH, "資産番号": "5262"}
    rows, counts = reconcile_records([asset], [inv], SITES)
    assert counts.matched == 1


def test_TC_AIV_DOM_030_no_diff():
    assert not has_field_diff(ASSET, INVENTORY_MATCH)


def test_TC_AIV_DOM_031_summary_diff():
    inv = {**INVENTORY_MATCH, "摘要": "B"}
    assert has_field_diff(ASSET, inv)


def test_TC_AIV_DOM_033_factory_change():
    inv = {**INVENTORY_MATCH, "管理部門コード": "002", "管理部門名称": "本社", "摘要": "B"}
    site_map = build_site_code_map(SITES)
    assert has_factory_change(ASSET, inv, site_map)


def test_TC_AIV_DOM_038_reconcile_factory_change_without_site_master():
    inv = {**INVENTORY_MATCH, "管理部門コード": "4003", "管理部門名称": "丸栄宮崎MTV工場"}
    rows, counts = reconcile_records([ASSET], [inv], [])
    assert counts.matched == 1
    assert rows[0].row_tone == RowTone.MATCH_FACTORY
    assert rows[0].tone_label == "拠点変更"
    assert rows[0].css_class == "aiv-row-factory"


def test_TC_AIV_DOM_039_reconcile_row_photos_and_diffs():
    inv = {
        **INVENTORY_MATCH,
        "管理部門コード": "4003",
        "管理部門名称": "丸栄宮崎MTV工場",
        "摘要": "B",
        "資産写真": "https://example.com/asset.jpg",
        "資産プレート写真": "https://example.com/plate.jpg",
    }
    rows, _counts = reconcile_records([ASSET], [inv], [])
    assert rows[0].asset_photo_url == "https://example.com/asset.jpg"
    assert rows[0].plate_photo_url == "https://example.com/plate.jpg"
    assert len(rows[0].field_comparisons) == 9
    assert sum(1 for item in rows[0].field_comparisons if item.is_diff) >= 2


@pytest.mark.parametrize(
    ("status", "diff", "factory", "expected"),
    [
        (MatchStatus.ASSET_ONLY, False, False, RowTone.NONE),
        (MatchStatus.MATCHED, False, False, RowTone.MATCH_CLEAN),
        (MatchStatus.MATCHED, True, False, RowTone.MATCH_DIFF),
        (MatchStatus.MATCHED, True, True, RowTone.MATCH_FACTORY),
    ],
)
def test_TC_AIV_DOM_040_row_tone(status, diff, factory, expected):
    assert derive_row_tone(status, diff, factory) == expected
