from __future__ import annotations

from application.asset_inventory.domain.value_objects.field_compare import (
    field_values_equal,
    has_factory_change,
    has_field_diff,
)
from application.asset_inventory.domain.repositories.ports import MatchStatus, RowTone, Record


ASSET = {
    "管理部門名称": "宮崎工場",
    "管理部門コード": "001",
    "メーカー": "M",
    "管理者名称": "MODEL",
    "型番": "SN",
    "旧資産番号コード": "OLD",
    "使用区分": "使用",
    "摘要": "A",
}

INVENTORY_SAME = dict(ASSET)

INVENTORY_DIFF = {**ASSET, "メーカー": "OTHER"}

SITES = [
    {"データID": "S1", "管理部門コード": "001", "拠点名": "宮崎工場"},
    {"データID": "S2", "管理部門コード": "002", "拠点名": "本社"},
]


def test_field_values_equal_trims():
    assert field_values_equal(" A ", "A") is True
    assert field_values_equal("A", "B") is False


def test_TC_AIV_DOM_030_no_diff():
    assert has_field_diff(ASSET, INVENTORY_SAME) is False


def test_TC_AIV_DOM_031_has_diff():
    assert has_field_diff(ASSET, INVENTORY_DIFF) is True


def test_TC_AIV_DOM_034_factory_change():
    inventory = {**ASSET, "管理部門コード": "002", "管理部門名称": "本社"}
    site_map = {"001": "S1", "002": "S2"}
    assert has_factory_change(ASSET, inventory, site_map) is True


def test_TC_AIV_DOM_033_no_factory_change_same_site():
    site_map = {"001": "S1"}
    assert has_factory_change(ASSET, INVENTORY_SAME, site_map) is False


def test_TC_AIV_DOM_035_factory_change_fallback_without_site_master():
    inventory = {**ASSET, "管理部門コード": "002", "管理部門名称": "本社"}
    assert has_factory_change(ASSET, inventory, {}) is True


def test_TC_AIV_DOM_036_factory_change_same_code_different_name():
    inventory = {**ASSET, "管理部門名称": "別拠点名"}
    assert has_factory_change(ASSET, inventory, {}) is False


def test_TC_AIV_DOM_037_factory_change_prefers_site_master_when_resolved():
    inventory = {**ASSET, "管理部門コード": "002", "管理部門名称": "本社"}
    site_map = {"001": "S1", "002": "S1"}
    assert has_factory_change(ASSET, inventory, site_map) is False
