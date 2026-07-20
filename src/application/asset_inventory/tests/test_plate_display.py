from __future__ import annotations

from application.asset_inventory.domain.value_objects.plate_display import format_plate_created


def test_TC_AIV_DOM_090_plate_zero():
    assert format_plate_created("0") == ("0", "プレート有")


def test_TC_AIV_DOM_091_plate_one():
    assert format_plate_created("1") == ("1", "プレート作成")


def test_TC_AIV_DOM_092_plate_empty():
    assert format_plate_created("") == ("", "")
