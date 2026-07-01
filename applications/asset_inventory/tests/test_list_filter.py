from __future__ import annotations

from applications.asset_inventory.domain.list_filter import (
    apply_filters,
    extract_asset_numbers_from_rows,
    extract_site_names_from_assets,
    filter_asset_number_options,
    matches_asset_number_filter,
)
from applications.asset_inventory.domain.ports import MatchStatus, ReconcileRow, RowTone


def _row(
    site: str,
    status: MatchStatus,
    plate_code: str = "",
    plate_label: str = "",
    asset_number: str = "1",
) -> ReconcileRow:
    labels = {
        MatchStatus.MATCHED: "棚卸済み",
        MatchStatus.ASSET_ONLY: "未棚卸",
        MatchStatus.INVENTORY_ONLY: "台帳外",
    }
    return ReconcileRow(
        match_status=status,
        row_tone=RowTone.NONE,
        status_label=labels[status],
        tone_label="未突合",
        asset_number=asset_number,
        branch_number="0",
        site_name=site,
        manufacturer="",
        model_name="",
        serial_number="",
        old_asset_number="",
        usage_category="",
        summary="",
        plate_created=plate_label,
        plate_created_code=plate_code,
        inventory_operator="",
        inventory_datetime="",
    )


def test_TC_AIV_DOM_056_site_filter():
    rows = (_row("宮崎工場", MatchStatus.MATCHED), _row("本社", MatchStatus.MATCHED))
    filtered = apply_filters(rows, status_filter="all", site_filter="宮崎工場", plate_filter="all")
    assert len(filtered) == 1
    assert filtered[0].site_name == "宮崎工場"


def test_TC_AIV_DOM_058_status_and_site_and():
    rows = (
        _row("宮崎工場", MatchStatus.MATCHED),
        _row("本社", MatchStatus.ASSET_ONLY),
        _row("本社", MatchStatus.MATCHED),
    )
    filtered = apply_filters(rows, status_filter="matched", site_filter="本社", plate_filter="all")
    assert len(filtered) == 1
    assert filtered[0].match_status == MatchStatus.MATCHED


def test_TC_AIV_DOM_059_empty_site_hidden_when_filtered():
    rows = (_row("", MatchStatus.MATCHED), _row("宮崎工場", MatchStatus.MATCHED))
    filtered = apply_filters(rows, status_filter="all", site_filter="宮崎工場", plate_filter="all")
    assert len(filtered) == 1


def test_TC_AIV_DOM_074_extract_site_names_from_assets():
    assets = [
        {"管理部門名称": "本社"},
        {"管理部門名称": "宮崎工場"},
        {"管理部門名称": "本社"},
        {"管理部門名称": ""},
    ]
    assert extract_site_names_from_assets(assets) == ("宮崎工場", "本社")


def test_TC_AIV_DOM_075_plate_filter():
    rows = (
        _row("宮崎工場", MatchStatus.MATCHED, "0", "プレート有"),
        _row("本社", MatchStatus.MATCHED, "1", "プレート作成"),
    )
    filtered = apply_filters(rows, status_filter="all", site_filter="all", plate_filter="1")
    assert len(filtered) == 1
    assert filtered[0].plate_created_code == "1"


def test_TC_AIV_DOM_076_asset_number_filter_prefix_match():
    rows = (
        _row("宮崎工場", MatchStatus.MATCHED, asset_number="5262"),
        _row("本社", MatchStatus.MATCHED, asset_number="3043"),
    )
    filtered = apply_filters(rows, status_filter="all", site_filter="all", plate_filter="all", asset_number_filter="52")
    assert len(filtered) == 1
    assert filtered[0].asset_number == "5262"

    filtered_middle = apply_filters(
        rows, status_filter="all", site_filter="all", plate_filter="all", asset_number_filter="26"
    )
    assert len(filtered_middle) == 0


def test_TC_AIV_DOM_077_asset_number_filter_l_prefix_normalized():
    rows = (_row("宮崎工場", MatchStatus.MATCHED, asset_number="L5262"),)
    assert matches_asset_number_filter("L5262", "5262") is True
    assert matches_asset_number_filter("L5262", "52") is True
    filtered = apply_filters(rows, status_filter="all", site_filter="all", plate_filter="all", asset_number_filter="5262")
    assert len(filtered) == 1


def test_TC_AIV_DOM_078_extract_asset_numbers_from_rows():
    rows = (
        _row("宮崎工場", MatchStatus.MATCHED, asset_number="2"),
        _row("本社", MatchStatus.MATCHED, asset_number="1"),
        _row("本社", MatchStatus.MATCHED, asset_number="1"),
    )
    assert extract_asset_numbers_from_rows(rows) == ("1", "2")


def test_TC_AIV_DOM_078a_extract_asset_numbers_normalizes_l_prefix():
    rows = (
        _row("宮崎工場", MatchStatus.MATCHED, asset_number="L5262"),
        _row("本社", MatchStatus.MATCHED, asset_number="5262"),
        _row("本社", MatchStatus.INVENTORY_ONLY, asset_number="L9999"),
    )
    assert extract_asset_numbers_from_rows(rows) == ("5262", "9999")


def test_TC_AIV_DOM_078b_filter_asset_number_options_prefix_l_normalized():
    options = ("1", "5262", "9999")
    assert filter_asset_number_options(options, "52") == ("5262",)
    assert filter_asset_number_options(options, "L52") == ("5262",)
    assert filter_asset_number_options(options, "") == options
