from __future__ import annotations

from pathlib import Path

from django.conf import settings


CSS_PATH = Path(settings.BASE_DIR) / "static" / "css" / "app.css"
IOA_TEMPLATE_PATH = Path(settings.BASE_DIR) / "templates" / "inventory_order_alert" / "list.html"
AIV_TEMPLATE_PATH = Path(settings.BASE_DIR) / "templates" / "asset_inventory" / "list.html"


def test_portal_list_filter_uses_shared_width_variables():
    source = CSS_PATH.read_text(encoding="utf-8")
    block = source.split("/* 一覧フィルタ共通（資産棚卸・在庫発注アラート） */", 1)[1].split(
        ".inventory-order-alert-page .ioa-filter-panel {",
        1,
    )[0]
    assert ".asset-inventory-page," in block
    assert ".inventory-order-alert-page {" in block
    assert "--portal-list-filter-control-width: 9.5rem;" in block


def test_portal_list_filter_labels_stack_above_controls():
    source = CSS_PATH.read_text(encoding="utf-8")
    block = source.split("/* 一覧フィルタ共通（資産棚卸・在庫発注アラート） */", 1)[1].split(
        ".inventory-order-alert-page .ioa-filter-panel {",
        1,
    )[0]
    assert "flex-direction: column;" in block
    assert ".aiv-filter-field-label," in block
    assert ".ioa-filter-field-label" in block


def test_inventory_order_alert_filter_select_width_is_narrower():
    source = CSS_PATH.read_text(encoding="utf-8")
    assert ".inventory-order-alert-page .ioa-filter-panel .ioa-filter-select {" not in source
    assert ".inventory-order-alert-page .ioa-filter-panel .ioa-filter-select" in source
    assert "width: var(--portal-list-filter-control-width);" in source


def test_inventory_order_alert_filter_template_uses_stacked_labels():
    # フィルタパネルは並び替えと同じツールバー行の中にある（表の表示領域を優先するため）。
    html = IOA_TEMPLATE_PATH.read_text(encoding="utf-8")
    toolbar_block = html.split('class="ioa-table-toolbar"', 1)[1].split("ioa-table-wrap", 1)[0]
    filter_block = toolbar_block.split('class="ioa-filter-panel"', 1)[1]
    assert 'class="ioa-filter-field"' in filter_block
    assert 'class="ioa-filter-field-label">担当者コード</span>' in filter_block
    assert 'class="ioa-filter-field-label">得意先コード</span>' in filter_block


def test_asset_inventory_filter_template_uses_stacked_labels():
    # フィルタパネルは並び替えと同じツールバー行の中にある（表の表示領域を優先するため）。
    html = AIV_TEMPLATE_PATH.read_text(encoding="utf-8")
    toolbar_block = html.split('class="aiv-table-toolbar"', 1)[1].split("aiv-table-wrap", 1)[0]
    filter_block = toolbar_block.split('class="aiv-filter-panel"', 1)[1]
    assert 'class="aiv-filter-field-label">棚卸結果</span>' in filter_block
    assert 'label="資産番号"' in filter_block
    assert "portal_prefix_filter_field.html" in filter_block
    assert 'class="aiv-filter-control' in filter_block


def test_asset_inventory_asset_number_filter_matches_select_height():
    source = CSS_PATH.read_text(encoding="utf-8")
    height_block = source.split("body.portal-app-page .portal-filter-select,", 1)[1].split("}", 1)[0]
    assert "body.portal-app-page .aiv-filter-asset-number," in height_block
    assert "var(--portal-control-height)" in height_block
