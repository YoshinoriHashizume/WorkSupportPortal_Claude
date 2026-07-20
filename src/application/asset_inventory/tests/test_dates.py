from __future__ import annotations

from datetime import date

from application.asset_inventory.domain.value_objects.dates import (
    format_asset_acquisition_date_display,
    parse_asset_acquisition_date,
)


def test_TC_AIV_DOM_07I_parse_asset_acquisition_date_formats():
    assert parse_asset_acquisition_date("2026-03-01") == date(2026, 3, 1)
    assert parse_asset_acquisition_date("2026/03/01") == date(2026, 3, 1)
    assert parse_asset_acquisition_date("") is None
    assert parse_asset_acquisition_date("   ") is None


def test_TC_AIV_DOM_07A_format_asset_acquisition_date_display():
    assert format_asset_acquisition_date_display("2026-03-01") == "2026/03/01"
    assert format_asset_acquisition_date_display("2026/03/01") == "2026/03/01"
    assert format_asset_acquisition_date_display("") == ""
    assert format_asset_acquisition_date_display("令和8年1月1日") == "令和8年1月1日"
