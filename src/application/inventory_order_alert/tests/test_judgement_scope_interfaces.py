"""判定材料の絞り込み（spec/11）の配信・画面・設定のテスト（TC-JS-X-*・TC-JS-A-007）。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from application.inventory_order_alert.domain.value_objects.list_client_data import row_to_client_dict

SRC = Path(__file__).resolve().parents[3]
LIST_JS = SRC / "static" / "js" / "inventory-order-alert-list.js"
LIST_CLIENT_JS = SRC / "static" / "js" / "inventory-order-alert-list-client.js"
LIST_HTML = SRC / "templates" / "inventory_order_alert" / "list.html"
SETTINGS_HTML = SRC / "templates" / "inventory_order_alert" / "settings.html"


# --- TC-JS-X-002: 配信ペイロード ---


def test_js_x002_payload_carries_stale_order_fields():
    row = {
        "cust_code": "110",
        "item_cd": "094ME-41490",
        "stale_order_qty": 87,
        "stale_order_count": 5,
    }

    client_row = row_to_client_dict(row, as_of_date=date(2026, 10, 27))

    assert client_row["staleOrderQty"] == 87
    assert client_row["staleOrderCount"] == 5


def test_js_x002_payload_defaults_stale_order_fields_to_zero():
    """旧スナップショットの行でも例外にせず 0 を配信する（REQ-JS-F-007）。"""
    client_row = row_to_client_dict({"cust_code": "110", "item_cd": "X"}, as_of_date=date(2026, 10, 27))

    assert client_row["staleOrderQty"] == 0
    assert client_row["staleOrderCount"] == 0


# --- TC-JS-X-001: 詳細ダイアログ ---


def test_js_x001_detail_dialog_has_stale_order_row():
    html = LIST_HTML.read_text(encoding="utf-8")
    dialog = html.split('<dialog id="ioa-location-dialog"', 1)[1].split("</dialog>", 1)[0]

    assert "ioa-detail-stale-orders" in dialog
    assert "ioa-detail-stale-orders-label" in dialog
    # 在庫切れ日・発注期限・安全在庫は従来どおり残す（REQ-JS-F-004）
    assert "ioa-detail-safety-stock" in dialog
    assert "ioa-detail-overdue-orders" in dialog


def test_js_x001_js_hides_the_stale_row_when_empty():
    source = LIST_JS.read_text(encoding="utf-8")
    block = source.split("function renderStockAndOrders(", 1)[1].split("\n    function ", 1)[0]

    assert "staleOrderQty" in block
    assert "staleOrdersLabel" in block
    # 0 件なら dt/dd ごと隠す（REQ-JS-F-005）
    assert "hidden = !hasStale" in block
    # 推定であることが伝わる文言
    assert "納期切れのまま更新がないため入荷見込みに数えていません" in block


def test_js_x002_list_client_passes_stale_fields_through():
    source = LIST_CLIENT_JS.read_text(encoding="utf-8")

    assert "staleOrderQty: row.staleOrderQty" in source
    assert "staleOrderCount: row.staleOrderCount" in source


# --- TC-JS-X-006: JS に判定を持ち込まない（REQ-JS-NF-002） ---


def test_js_x006_judgement_is_not_reimplemented_in_js():
    source = LIST_JS.read_text(encoding="utf-8")

    # ホライズン・滞留のしきい値計算を JS でやっていない
    for term in ("judgementHorizonDays", "staleOrderDays", "stale_after_days"):
        assert term not in source, f"{term} が JS に現れている（判定は domain に置く）"


# --- TC-JS-A-007: 設定画面 ---


def test_js_a007_settings_page_has_both_inputs():
    html = SETTINGS_HTML.read_text(encoding="utf-8")

    assert 'id="ioa-setting-judgement-horizon-days"' in html
    assert 'name="judgementHorizonDays"' in html
    assert 'min="1" max="365"' in html
    assert 'id="ioa-setting-stale-order-days"' in html
    assert 'name="staleOrderDays"' in html
    assert 'min="1" max="730"' in html
    # 取込時に判定するため、変更が即時に反映されないことを明記する（REQ-JS-F-008）
    assert html.count("変更は次回の SLIMS 在庫 CSV 取込から反映されます。") == 2
    # 推定であることを画面に残す（REQ-JS-NF-003）
    assert "基幹に発注停止のフラグがないため、最終更新日による推定です。" in html


def test_js_a007_settings_page_sends_both_values():
    html = SETTINGS_HTML.read_text(encoding="utf-8")

    assert 'judgementHorizonDays: Number(document.getElementById("ioa-setting-judgement-horizon-days").value)' in html
    assert 'staleOrderDays: Number(document.getElementById("ioa-setting-stale-order-days").value)' in html


@pytest.mark.django_db
def test_js_a007_settings_page_renders_current_values(client, admin_user):
    from application.inventory_order_alert.infrastructure.persistence.settings_repository import save_app_settings

    save_app_settings(
        warning_days=365,
        stock_stale_days=7,
        judgement_horizon_days=45,
        stale_order_days=120,
    )
    client.force_login(admin_user)

    html = client.get("/app/production/inventory-order-alert/settings").content.decode("utf-8")

    assert 'value="45"' in html
    assert 'value="120"' in html
