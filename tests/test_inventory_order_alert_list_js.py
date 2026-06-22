from __future__ import annotations

from pathlib import Path


JS_PATH = Path(__file__).resolve().parents[1] / "static" / "js" / "inventory-order-alert-list.js"


def test_inventory_order_alert_list_js_exists():
    assert JS_PATH.is_file()


def test_inventory_order_alert_list_js_submits_import_on_file_select():
    source = JS_PATH.read_text(encoding="utf-8")
    assert "initSlimsImport" in source
    assert "showImportLoading" in source
    assert "ioa-import-overlay" in source
    assert "form.submit()" in source
    assert "input.files" in source
    import_block = source.split("function initSlimsImport()", 1)[1].split("function refreshSortRowOrders", 1)[0]
    assert "input.disabled" not in import_block


def test_inventory_order_alert_list_js_initializes_sort_dialog():
    source = JS_PATH.read_text(encoding="utf-8")
    assert "initSortDialog" in source
    assert "showModal" in source
    assert "ioa-sort-add" in source
    assert 'input[name="sort"]' in source


def test_inventory_order_alert_list_js_supports_sort_row_drag_and_drop():
    source = JS_PATH.read_text(encoding="utf-8")
    assert "bindSortRowDrag" in source
    assert "draggable" in source
    assert "ioa-sort-row-order" in source
    assert "insertBefore" in source


def test_inventory_order_alert_list_js_initializes_alert_rules_dialog():
    source = JS_PATH.read_text(encoding="utf-8")
    assert "initAlertRulesDialog" in source
    assert "ioa-alert-rules-open" in source
    assert "ioa-alert-rules-dialog" in source
    assert "/api/inventory-order-alert/alert-settings" in source


def test_inventory_order_alert_list_js_saves_confirmation_on_select_change():
    source = JS_PATH.read_text(encoding="utf-8")
    assert "initConfirmationStatusSelects" in source
    assert "ioa-confirmation-status" in source
    assert "/api/inventory-order-alert/confirmation" in source
    assert "saveConfirmationStatus" in source


def test_inventory_order_alert_list_js_preserves_table_scroll_on_confirmation_reload():
    source = JS_PATH.read_text(encoding="utf-8")
    assert "saveTableScrollPosition" in source
    assert "restoreTableScrollPosition" in source
    assert "reloadInventoryOrderAlertPage" in source


def test_inventory_order_alert_list_js_updates_table_counts_label():
    source = JS_PATH.read_text(encoding="utf-8")
    assert "ioa-table-counts-left" in source
    assert "ioa-table-counts-right" in source
    assert "重点" in source
    assert "全件数:" not in source
    assert "確認済み" in source
    assert "ioa-confirmation-reset" in source
    assert "confirmation/reset" in source


def test_inventory_order_alert_list_js_initializes_location_dialog():
    source = JS_PATH.read_text(encoding="utf-8")
    assert "initLocationDialog" in source
    assert "ioa-location-dialog" in source
    assert "ioa-detail-memo-table" in source
    assert "CONFIRMATION_MEMO_API" in source
    assert "loadMemoEntries" in source
    assert "renderMemoEntries" in source
    assert "stockLocationDetail" in source
    assert "parseLocationDetail" in source
    assert "formatIncomingDate" in source
    assert "incomingDate" in source
    assert "localeCompare" in source


def test_inventory_order_alert_list_js_import_overlay_has_spinner_css():
    css = (Path(__file__).resolve().parents[1] / "static" / "css" / "app.css").read_text(encoding="utf-8")
    assert ".ioa-import-overlay" in css
    assert ".ioa-import-spinner" in css
    assert "ioa-import-spin" in css


    css = (Path(__file__).resolve().parents[1] / "static" / "css" / "app.css").read_text(encoding="utf-8")
    assert "body.inventory-order-alert-page .ioa-alert-rules-dialog {\n  width: min(480px" in css
    assert "body.inventory-order-alert-page .ioa-location-dialog {\n  width: min(960px" in css
    assert "body.inventory-order-alert-page .ioa-detail-memo-col-at {\n  width: 140px" in css
    assert "body.inventory-order-alert-page .ioa-detail-memo-col-by {\n  width: 100px" in css
    assert "body.inventory-order-alert-page .ioa-detail-memo-col-content" not in css
    table_rule = css.split("body.inventory-order-alert-page .ioa-alert-rules-table,")[1].split("}")[0]
    assert "ioa-location-table" in table_rule


def test_inventory_order_alert_list_js_updates_confirmation_without_reload():
    source = JS_PATH.read_text(encoding="utf-8")
    assert "updateRowConfirmationState" in source
    assert "updateTableCounts" in source
    assert "getListFilterParams" in source
    save_block = source.split("async function saveConfirmationStatus", 1)[1].split("function initConfirmationStatusSelects", 1)[0]
    assert "reloadInventoryOrderAlertPage" not in save_block
    assert "saveConfirmation(row," in save_block
