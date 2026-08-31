from __future__ import annotations

from application.asset_inventory.domain.value_objects.inventory_dedup import dedupe_inventory_records


def test_TC_AIV_DOM_010_pick_latest_inventory_datetime():
    records = [
        {"資産番号": "5262", "資産枝番": "0001", "棚卸日時": "2026/01/10 10:00:00", "データID": "10"},
        {"資産番号": "5262", "資産枝番": "0001", "棚卸日時": "2026/01/16 18:46:01", "データID": "20"},
    ]
    result = dedupe_inventory_records(records)
    assert result["5262|0001"]["データID"] == "20"


def test_TC_AIV_DOM_011_tie_break_by_data_id():
    records = [
        {"資産番号": "5262", "資産枝番": "0001", "棚卸日時": "2026/01/10 10:00:00", "データID": "20"},
        {"資産番号": "5262", "資産枝番": "0001", "棚卸日時": "2026/01/10 10:00:00", "データID": "10"},
    ]
    result = dedupe_inventory_records(records)
    assert result["5262|0001"]["データID"] == "10"
