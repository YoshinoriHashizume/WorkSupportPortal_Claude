from __future__ import annotations

from apps.asset_inventory.domain.ports import (
    ASSET_ACQUISITION_DATE_FIELD,
    ASSET_FIELDS,
    INVENTORY_FIELDS,
)


def test_asset_fields_include_acquisition_date():
    assert ASSET_ACQUISITION_DATE_FIELD in ASSET_FIELDS
    assert ASSET_FIELDS.index(ASSET_ACQUISITION_DATE_FIELD) == ASSET_FIELDS.index("型番") + 1


def test_inventory_fields_do_not_request_asset_only_acquisition_date():
    assert ASSET_ACQUISITION_DATE_FIELD not in INVENTORY_FIELDS
