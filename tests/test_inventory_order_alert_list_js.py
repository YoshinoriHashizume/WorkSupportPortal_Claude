from __future__ import annotations

from pathlib import Path


JS_PATH = Path(__file__).resolve().parents[1] / "static" / "js" / "inventory-order-alert-list.js"
CLIENT_JS_PATH = Path(__file__).resolve().parents[1] / "static" / "js" / "inventory-order-alert-list-client.js"


def test_inventory_order_alert_list_client_js_renders_sort_headers_as_links():
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    assert "window.PortalListCore" in source
    assert "Core.renderTableHeaders" in source
    assert 'headerMode: "link"' in source
    assert 'sortColumnDataAttr: "data-ioa-sort-column"' in source
    assert "function renderTableHeaders()" not in source


def test_inventory_order_alert_list_js_init_location_dialog_has_no_duplicate_table_body():
    source = JS_PATH.read_text(encoding="utf-8")
    block = source.split("function initLocationDialog()", 1)[1].split("function initConfirmationReset", 1)[0]
    assert "const tableBody" not in block
    assert "const listTableBody" in block
    assert "const locationTableBody" in block


def test_inventory_order_alert_list_js_initializes_on_dom_content_loaded():
    source = JS_PATH.read_text(encoding="utf-8")
    assert 'document.addEventListener("DOMContentLoaded", initInventoryOrderAlertPage)' in source
    assert "IoaListClient?.init" in source


def test_inventory_order_alert_list_js_submits_import_on_file_select():
    source = JS_PATH.read_text(encoding="utf-8")
    assert "initSlimsImport" in source
    assert "showImportLoading" in source
    assert "ioa-import-overlay" in source
    assert "form.submit()" in source
    assert "input.files" in source
    import_block = source.split("function initSlimsImport()", 1)[1].split("function initSortDialog", 1)[0]
    assert "input.disabled" not in import_block


def test_inventory_order_alert_list_js_initializes_sort_dialog():
    source = JS_PATH.read_text(encoding="utf-8")
    assert "initSortDialog" in source
    assert "PortalListSortDialog" in source
    assert "ioa-sort-add" in source
    assert "ioa-sort-row-order" in source


def test_inventory_order_alert_list_js_sort_dialog_is_shared_module():
    sort_dialog_source = (
        Path(__file__).resolve().parents[1] / "static" / "js" / "portal-list-sort-dialog.js"
    ).read_text(encoding="utf-8")
    assert "bindSortRowDrag" not in source
    assert "draggable" in sort_dialog_source
    assert "insertBefore" in sort_dialog_source


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
    assert "ioa-alert-rules-color-swatch" in css
    assert "td:last-child" not in css.split("ioa-alert-rules-row--critical")[1].split("ioa-alert-rules-actions", 1)[0]
    shared_block = css.split("/* ポータル共通: 一覧・警告条件ダイアログの行背景色 */", 1)[1]
    assert "body.inventory-order-alert-page .ioa-alert-rules-row--critical" in shared_block
    assert ".shipment-trend-page .st-row-decrease-strong," in shared_block


def test_inventory_order_alert_list_js_updates_confirmation_without_reload():
    source = JS_PATH.read_text(encoding="utf-8")
    assert "updateRowConfirmationState" in source
    assert "updateTableCounts" in source
    assert "getListFilterParams" in source
    assert "IoaListClient" in source
    save_block = source.split("async function saveConfirmationStatus", 1)[1].split("function initConfirmationStatusSelects", 1)[0]
    assert "itemCdFilter" in save_block or "getListFilterParams" in save_block
    assert "reloadInventoryOrderAlertPage" not in save_block
    assert "saveConfirmation(row," in save_block
    assert "updateRowFromConfirmation" in source


def test_inventory_order_alert_list_client_js_exists():
    client_path = Path(__file__).resolve().parents[1] / "static" / "js" / "inventory-order-alert-list-client.js"
    assert client_path.is_file()
    source = client_path.read_text(encoding="utf-8")
    assert "window.IoaListClient" in source
    assert "createPrefixColumnFilter" in source or "matchesPrefixFilter" in source
    assert "ioa-filter-item-cd" in source
    assert "ioa-filter-level1-item-cd" in source
    assert "level1ItemCdFilter" in source
    assert "ioa-list-data" in source
    assert "Core.replaceUrl" in source
    assert "onchange=\"this.form.submit()\"" not in source


def test_inventory_order_alert_list_template_loads_portal_list_scripts():
    template = (
        Path(__file__).resolve().parents[1] / "templates" / "inventory_order_alert" / "list.html"
    ).read_text(encoding="utf-8")
    assert "portal-list-core.js" in template
    assert "portal-list-prefix-filter.js" in template
    assert "portal-list-dependent-cust-filter.js" in template
    assert "portal-list-sort-dialog.js" in template
    assert "ioa-item-cd-options" in template
    assert "ioa-level1-item-cd-options" in template
    assert template.index("portal-list-core.js") < template.index("inventory-order-alert-list-client.js")


def test_inventory_order_alert_list_client_js_clears_part_number_filters_on_cust_change():
    source = (
        Path(__file__).resolve().parents[1] / "static" / "js" / "inventory-order-alert-list-client.js"
    ).read_text(encoding="utf-8")
    chrg_block = source.split("custChrgSelect?.addEventListener", 1)[1].split("custCodeSelect?.addEventListener", 1)[0]
    cust_block = source.split("custCodeSelect?.addEventListener", 1)[1].split("Core.bindPaginationControls", 1)[0]
    assert 'itemCd: ""' in chrg_block
    assert 'level1ItemCd: ""' in chrg_block
    assert 'itemCd: ""' in cust_block
    assert 'level1ItemCd: ""' in cust_block


def test_inventory_order_alert_list_client_js_resets_cust_code_on_chrg_change():
    source = (
        Path(__file__).resolve().parents[1] / "static" / "js" / "inventory-order-alert-list-client.js"
    ).read_text(encoding="utf-8")
    chrg_block = source.split("custChrgSelect?.addEventListener", 1)[1].split("custCodeSelect?.addEventListener", 1)[0]
    assert "state.custCode" not in chrg_block
    assert chrg_block.count('""') >= 3
