from __future__ import annotations

from apps.asset_inventory.domain.reconcile import reconcile_records
from apps.asset_inventory.domain.reconcile_cache import (
    SESSION_KEY,
    load_reconcile_cache,
    reconcile_cache_from_session_payload,
    reconcile_cache_to_session_payload,
    reconcile_row_from_dict,
    reconcile_row_to_dict,
    save_reconcile_cache,
    ReconcileCache,
)
from tests.asset_inventory.test_usecase_list_page import ASSETS, INVENTORY, SITES


def test_TC_AIV_DOM_07C_reconcile_row_serialize_roundtrip():
    rows, counts = reconcile_records(ASSETS, INVENTORY, SITES)
    row = rows[0]
    restored = reconcile_row_from_dict(reconcile_row_to_dict(row))
    assert restored.asset_number == row.asset_number
    assert restored.match_status == row.match_status
    assert len(restored.field_comparisons) == len(row.field_comparisons)


def test_TC_AIV_DOM_07D_reconcile_cache_session_roundtrip():
    rows, counts = reconcile_records(ASSETS, INVENTORY, SITES)
    cache = ReconcileCache(
        management_id="1",
        rows=rows,
        counts=counts,
        site_options=("宮崎工場", "本社"),
        asset_number_options=("1", "5262", "9999"),
    )
    payload = reconcile_cache_to_session_payload(cache)
    restored = reconcile_cache_from_session_payload(payload)
    assert restored is not None
    assert restored.management_id == "1"
    assert len(restored.rows) == len(rows)
    assert restored.counts.matched == counts.matched


def test_TC_AIV_DOM_07E_field_comparisons_serialize():
    row = reconcile_records(ASSETS, INVENTORY, SITES)[0][0]
    payload = reconcile_row_to_dict(row)
    comparisons = payload["field_comparisons"]
    assert isinstance(comparisons, list)
    assert comparisons
    assert "label" in comparisons[0]


def test_TC_AIV_DOM_07F_save_and_load_session():
    rows, counts = reconcile_records(ASSETS, INVENTORY, SITES)
    cache = ReconcileCache(
        management_id="1",
        rows=rows,
        counts=counts,
        site_options=(),
        asset_number_options=(),
    )
    session: dict = {}
    save_reconcile_cache(session, cache)
    assert SESSION_KEY in session
    loaded = load_reconcile_cache(session)
    assert loaded is not None
    assert loaded.management_id == "1"
