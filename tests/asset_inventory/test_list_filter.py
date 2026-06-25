from __future__ import annotations

from apps.asset_inventory.domain.list_filter import (
    apply_filters,
    extract_site_names_from_assets,
)
from apps.asset_inventory.domain.ports import MatchStatus, ReconcileRow, RowTone


def _row(site: str, status: MatchStatus, plate_code: str = "", plate_label: str = "") -> ReconcileRow:
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
        asset_number="1",
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
