from __future__ import annotations

from dataclasses import replace

from application.asset_inventory.domain.value_objects.reconcile import reconcile_records
from application.asset_inventory.domain.value_objects.reconcile_cache import (
    SESSION_KEY,
    load_amendment_snapshot,
    load_reconcile_cache,
    reconcile_cache_from_session_payload,
    reconcile_cache_to_session_payload,
    reconcile_row_from_dict,
    reconcile_row_to_dict,
    save_reconcile_cache,
    ReconcileCache,
)
from .test_usecase_list_page import ASSETS, INVENTORY, SITES


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


# --- REQ-F-009 / DD-02 拠点マスタ縮退フラグとスナップショットの読み出し ---


def _cache(management_id: str = "M1", *, site_warning: bool = False) -> ReconcileCache:
    """テスト用の突合結果スナップショットを組み立てる。"""
    rows, counts = reconcile_records(ASSETS, INVENTORY, SITES)
    return ReconcileCache(
        management_id=management_id,
        rows=rows,
        counts=counts,
        site_options=(),
        asset_number_options=(),
        site_warning=site_warning,
    )


SESSION_NO_SITE_WARNING_KEY = {
    "management_id": "M1",
    "rows": [],
    "counts": {"matched": 0, "asset_only": 0, "inventory_only": 0},
    "site_options": [],
    "asset_number_options": [],
}

SESSION_BROKEN = {"management_id": "M1", "rows": "壊れたデータ"}

SESSION_OTHER_MANAGEMENT = {
    "management_id": "M1",
    "rows": [],
    "counts": {"matched": 0, "asset_only": 0, "inventory_only": 0},
    "site_options": [],
    "asset_number_options": [],
    "site_warning": False,
}


def test_TC_AIV_DOM_07G_site_warning_survives_a_session_roundtrip():
    """拠点マスタ縮退フラグがセッションと往復すること（対応 DD-02）。"""
    payload = reconcile_cache_to_session_payload(_cache(site_warning=True))
    restored = reconcile_cache_from_session_payload(payload)
    assert restored is not None
    assert restored.site_warning is True


def test_TC_AIV_DOM_07H_missing_site_warning_key_is_read_as_false():
    """`site_warning` キーの無い旧形式のセッションが偽として読めること（対応 DD-02）。"""
    restored = reconcile_cache_from_session_payload(SESSION_NO_SITE_WARNING_KEY)
    assert restored is not None
    assert restored.site_warning is False


def test_TC_AIV_DOM_07I_load_amendment_snapshot_returns_snapshot_for_the_same_inventory():
    """棚卸が一致するときスナップショットを返すこと（対応 REQ-NF-003）。"""
    session: dict = {}
    save_reconcile_cache(session, _cache("M1"))
    snapshot = load_amendment_snapshot(session, "M1")
    assert snapshot is not None
    assert snapshot.management_id == "M1"


def test_TC_AIV_DOM_07J_load_amendment_snapshot_returns_none_for_another_inventory():
    """棚卸が一致しないとき `None` を返すこと（対応 REQ-F-009）。"""
    session = {SESSION_KEY: SESSION_OTHER_MANAGEMENT}
    assert load_amendment_snapshot(session, "M2") is None


def test_TC_AIV_DOM_07K_load_amendment_snapshot_does_not_raise_for_a_broken_session():
    """セッションが壊れていても例外を送出せず `None` を返すこと（対応 REQ-F-009）。"""
    assert load_amendment_snapshot({SESSION_KEY: SESSION_BROKEN}, "M1") is None
    assert load_amendment_snapshot({SESSION_KEY: "壊れたデータ"}, "M1") is None
    assert load_amendment_snapshot(None, "M1") is None


# --- REQ-F-003 / DD-08 追加コード部品（判定は名称・出力はコード）の往復 ---

ADDED_CODE_PARTS = ("manager_code", "usage_category_code", "manufacturer_code")


def test_TC_AIV_DOM_07M_added_code_parts_survive_a_session_roundtrip():
    """追加コード部品 3 件がセッションと往復すること（対応 REQ-F-003・DD-08）。"""
    row = replace(
        reconcile_records(ASSETS, INVENTORY, SITES)[0][0],
        manager_code="MGR1",
        usage_category_code="U1",
        manufacturer_code="MK1",
    )
    restored = reconcile_row_from_dict(reconcile_row_to_dict(row))
    assert restored.manager_code == "MGR1"
    assert restored.usage_category_code == "U1"
    assert restored.manufacturer_code == "MK1"


def test_TC_AIV_DOM_07N_missing_added_code_parts_are_read_as_empty():
    """3 件のキーが無い旧形式のセッションが空文字として読めること（対応 REQ-F-003）。"""
    payload = reconcile_row_to_dict(reconcile_records(ASSETS, INVENTORY, SITES)[0][0])
    for key in ADDED_CODE_PARTS:
        payload.pop(key)

    restored = reconcile_row_from_dict(payload)

    for key in ADDED_CODE_PARTS:
        assert getattr(restored, key) == ""
