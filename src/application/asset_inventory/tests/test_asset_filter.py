from __future__ import annotations

from application.asset_inventory.domain.value_objects.asset_filter import (
    filter_inventory_target_assets,
    is_inventory_target_asset,
)


def test_TC_AIV_DOM_070_target_code_one():
    assert is_inventory_target_asset({"生産品番⑧コード": "1"}) is True


def test_TC_AIV_DOM_071_target_code_trim():
    assert is_inventory_target_asset({"生産品番⑧コード": " 1 "}) is True


def test_TC_AIV_DOM_072_non_target_codes():
    assert is_inventory_target_asset({"生産品番⑧コード": "0"}) is False
    assert is_inventory_target_asset({"生産品番⑧コード": ""}) is False
    assert is_inventory_target_asset({}) is False


def test_TC_AIV_DOM_073_filter_inventory_target_assets():
    records = [
        {"データID": "A1", "生産品番⑧コード": "1"},
        {"データID": "A2", "生産品番⑧コード": "0"},
        {"データID": "A3", "生産品番⑧コード": ""},
        {"データID": "A4", "生産品番⑧コード": "1"},
    ]
    filtered = filter_inventory_target_assets(records)
    assert [row["データID"] for row in filtered] == ["A1", "A4"]
