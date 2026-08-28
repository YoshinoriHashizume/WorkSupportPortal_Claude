from __future__ import annotations

from application.asset_inventory.domain.repositories.ports import (
    ASSET_ACQUISITION_DATE_FIELD,
    ASSET_FIELDS,
    INVENTORY_FIELDS,
)


def test_asset_fields_include_acquisition_date():
    assert ASSET_ACQUISITION_DATE_FIELD in ASSET_FIELDS
    assert ASSET_FIELDS.index(ASSET_ACQUISITION_DATE_FIELD) == ASSET_FIELDS.index("型番") + 1


def test_inventory_fields_do_not_request_asset_only_acquisition_date():
    assert ASSET_ACQUISITION_DATE_FIELD not in INVENTORY_FIELDS


# --- REQ-F-003 / DD-08 判定は名称・出力はコード（ASP 取り込み用データの 44・59・64 列目） ---

ADDED_CODE_FIELDS = ("管理者コード", "使用区分コード", "メーカーコード")


def test_TC_AIV_DOM_060_both_field_lists_include_added_code_parts():
    """資産データ・棚卸データの双方に追加コード 3 件を要求すること（対応 REQ-F-003・DD-08）。"""
    for field in ADDED_CODE_FIELDS:
        assert field in ASSET_FIELDS
        assert field in INVENTORY_FIELDS
