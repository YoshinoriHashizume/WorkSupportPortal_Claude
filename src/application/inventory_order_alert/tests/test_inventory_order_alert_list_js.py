from __future__ import annotations

from pathlib import Path


JS_PATH = Path(__file__).resolve().parents[3] / "static" / "js" / "inventory-order-alert-list.js"
CLIENT_JS_PATH = Path(__file__).resolve().parents[3] / "static" / "js" / "inventory-order-alert-list-client.js"


def test_TC_SHC_X_002_client_js_has_get_shipment_trend_getter():
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    getter_block = source.split("getShipmentTrend(custCode, itemCd)", 1)[1].split("},", 1)[0]

    # findRow() を再利用して行を引く（design.md §6.3）。
    assert "findRow(custCode, itemCd)" in getter_block
    assert "shipment_trend" in getter_block


def test_TC_SHC_X_008_client_js_has_get_incoming_trend_getter():
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    getter_block = source.split("getIncomingTrend(custCode, itemCd)", 1)[1].split("},", 1)[0]

    # findRow() を再利用して行を引く（design.md §6.3, §6.1）。
    assert "findRow(custCode, itemCd)" in getter_block
    assert "incoming_trend" in getter_block


def test_shipment_trend_dedicated_chart_removed():
    """入出荷推移の独立グラフ区分は削除した（推定在庫推移に統合。DECISIONS.md参照）。

    getShipmentTrend/getIncomingTrend（データ取得）と shipment_trend/incoming_trend
    の算出自体は推定在庫推移の入力として引き続き使うため、renderShipmentTrendChart
    （専用グラフの描画）とその呼び出しのみが存在しないことを確認する。
    """
    source = JS_PATH.read_text(encoding="utf-8")

    assert "function renderShipmentTrendChart" not in source
    assert "ioa-detail-shipment-trend-chart" not in source


def test_TC_SHC_X_010_list_js_builds_anchored_stock_trend_from_last_index():
    source = JS_PATH.read_text(encoding="utf-8")
    func_block = source.split("function buildAnchoredStockTrend", 1)[1].split("\n  function ", 1)[0]

    # 末尾要素（直近月）を起点値（anchorQty）とし、過去へ逆算する（design.md §6.6）。
    assert "length - 1" in func_block
    assert "anchorQty" in func_block


def test_TC_SHC_X_011_list_js_parses_anchor_qty_strips_commas_and_returns_null():
    source = JS_PATH.read_text(encoding="utf-8")
    func_block = source.split("function parseAnchorQty", 1)[1].split("\n  function ", 1)[0]

    assert "replace" in func_block
    assert "null" in func_block


def test_TC_SHC_X_012_list_js_renders_anchored_stock_chart_with_zero_baseline():
    source = JS_PATH.read_text(encoding="utf-8")
    func_block = source.split("function renderAnchoredStockChart", 1)[1].split("\n  function ", 1)[0]

    # 0 を必ず範囲に含めるスケールでゼロ基準線を描く（design.md §6.6）。
    assert "Math.min(0" in func_block


def test_TC_SHC_X_013_anchored_stock_trend_is_not_clamped_to_zero():
    source = JS_PATH.read_text(encoding="utf-8")
    build_block = source.split("function buildAnchoredStockTrend", 1)[1].split("\n  function ", 1)[0]
    render_block = source.split("function renderAnchoredStockChart", 1)[1].split("\n  function ", 1)[0]

    # マイナスのまま表示する（クランプしない）合意事項（requirements.md §1.5）。
    assert "Math.max(0," not in build_block
    assert "Math.max(0," not in render_block


def test_TC_SHC_X_014_fill_detail_sections_wires_anchored_stock_chart():
    source = JS_PATH.read_text(encoding="utf-8")
    fill_block = source.split("function fillDetailSections", 1)[1].split("async function openLocationDialog", 1)[0]

    assert "buildAnchoredStockTrend(" in fill_block
    assert "renderAnchoredStockChart(" in fill_block


def test_TC_SHC_X_016_list_js_month_labels_avoid_edge_clipping():
    source = JS_PATH.read_text(encoding="utf-8")
    render_block = source.split("function renderAnchoredStockChart", 1)[1].split("\n  function ", 1)[0]

    # 先頭/末尾の月ラベルは text-anchor を start/end に切り替え、グラフ端での見切れを防ぐ。
    assert 'text-anchor", "start"' in render_block
    assert 'text-anchor", "end"' in render_block


def test_TC_SHC_X_017_list_js_renders_y_axis_scale_labels():
    source = JS_PATH.read_text(encoding="utf-8")
    render_block = source.split("function renderAnchoredStockChart", 1)[1].split("\n  function ", 1)[0]

    # 左側に最大値・最小値の数量目盛りを表示する。
    assert "ioa-anchored-stock-trend-y-axis-label" in render_block
    assert "toLocaleString" in render_block


def test_TC_SHC_X_015_list_html_has_anchored_stock_trend_section():
    template = (
        Path(__file__).resolve().parents[3] / "templates" / "inventory_order_alert" / "list.html"
    ).read_text(encoding="utf-8")

    assert "ioa-detail-anchored-stock-trend-section" in template
    assert "参考値" in template


def test_inventory_order_alert_list_client_js_renders_sort_headers_as_links():
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    assert "window.PortalListCore" in source
    assert "Core.renderTableHeaders" in source
    assert 'headerMode: "link"' in source
    assert 'sortColumnDataAttr: "data-ioa-sort-column"' in source
    assert "function renderTableHeaders()" not in source


def test_inventory_order_alert_list_client_js_selects_flow_period_option_by_axis_and_value():
    """判定期間の value は軸をまたいで重複する（低流動1か月＝死蔵1年＝どちらも "1"）。

    select.value への代入は DOM 順で最初に一致した option（隠れていても）を選んでしまうため、
    軸と value の両方が一致する option を明示的に選択しなければならない
    （死蔵判定軸を選ぶと「1年」ではなく「1か月」と表示される不具合の再発防止）。
    """
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    sync_block = source.split("function syncFlowSelector()", 1)[1].split("flowAxisSelect?.addEventListener", 1)[0]

    assert "flowPeriodSelect.value = String(state.flowPeriod)" not in sync_block
    assert "option.dataset.axis === state.flowAxis" in sync_block
    assert "matchedOption.selected = true" in sync_block


def test_inventory_order_alert_list_client_js_sorts_confirmation_status_by_key_rank():
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    assert "CONFIRMATION_STATUS_RANK" in source
    assert "confirmationStatusSortRank" in source
    assert 'column === "confirmation_status"' in source
    assert "row.confirmationStatusKey" in source
    assert "data-cust-code" in source
    assert "renderConfirmationSelect(selectedValue, identity)" in source
    assert "data-row-key" in source
    assert "parseRowKey" in source
    assert "readRowKeysFromDomElement" in source


def test_inventory_order_alert_list_js_init_location_dialog_has_no_duplicate_table_body():
    source = JS_PATH.read_text(encoding="utf-8")
    block = source.split("function initLocationDialog(", 1)[1].split("function initAlertRulesDialog", 1)[0]
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
    source = JS_PATH.read_text(encoding="utf-8")
    sort_dialog_source = (
        Path(__file__).resolve().parents[3] / "static" / "js" / "portal-list-sort-dialog.js"
    ).read_text(encoding="utf-8")
    assert "bindSortRowDrag" not in source
    assert "draggable" in sort_dialog_source
    assert "insertBefore" in sort_dialog_source


def test_inventory_order_alert_list_js_initializes_alert_rules_dialog():
    source = JS_PATH.read_text(encoding="utf-8")
    assert "initAlertRulesDialog" in source
    assert "ioa-alert-rules-open" in source
    assert "ioa-alert-rules-dialog" in source
    # 開くボタンが複数あっても全件に結線する（querySelector 単数だと 2 個目以降が無反応）。
    assert 'document.querySelectorAll(".inventory-order-alert-page .ioa-alert-rules-open")' in source
    assert 'document.querySelector(".inventory-order-alert-page .ioa-alert-rules-open")' not in source
    # 判定ルールダイアログは読み取り専用。保存処理は撤去した（design.md §6.6.5）。
    assert "/api/inventory-order-alert/alert-settings" not in source
    assert "ioa-alert-rules-save" not in source
    assert "warningShipmentMonths" not in source


def test_inventory_order_alert_list_js_saves_confirmation_on_select_change():
    source = JS_PATH.read_text(encoding="utf-8")
    assert "initConfirmationStatusSelects" in source
    assert "ioa-confirmation-status" in source
    assert "/api/inventory-order-alert/confirmation" in source
    assert "saveConfirmationStatus" in source


def test_inventory_order_alert_list_js_updates_table_counts_label():
    source = JS_PATH.read_text(encoding="utf-8")
    assert "ioa-table-counts-left" in source
    assert "ioa-table-counts-right" in source
    assert "供給リスク品" in source
    assert "在庫死蔵品" in source
    assert "在庫過剰リスク品" in source
    assert "通常流動品" in source
    assert "全件数:" not in source
    assert "確認済み" in source
    # 確認状態リセットは設定画面（SCR-02）へ移した。一覧の JS には持たない。
    assert "ioa-confirmation-reset" not in source
    assert "confirmation/reset" not in source


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


def test_inventory_order_alert_list_client_js_renders_detail_data_attributes():
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    row_block = source.split('<tr class="alert-row alert-row--', 1)[1].split("</tr>", 1)[0]

    # 詳細ダイアログは行の data-* 属性から組み立てる（design.md §6.3.1）。
    for attribute in (
        "data-mari-stock-qty",
        "data-flow-quadrant",
        "data-no-incoming-record",
        "data-level1-vend-cd",
        "data-level1-vend-name",
        "data-level1-item-cd",
        "data-last-incoming-date",
        "data-last-ship-date",
    ):
        assert attribute in row_block


def test_inventory_order_alert_list_client_js_sorts_mari_stock_like_slims_stock():
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")

    assert 'column === "stock_qty" || column === "mari_stock_qty"' in source
    assert 'column === "mari_stock_qty"' in source.split("function defaultDirectionForColumn", 1)[1]
    # 責任部署は一覧列ではなくなったのでソート・描画の分岐も残さない。
    assert 'column === "responsible_department"' not in source
    assert 'column.key === "responsible_department"' not in source


def test_inventory_order_alert_list_client_js_keeps_flow_quadrant_departments():
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")

    # 一覧列からは外すが、詳細ダイアログが流動区分キーで引くため対応表は残す（design.md §7.3）。
    assert "flowQuadrantDepartments" in source


def test_inventory_order_alert_list_js_fills_detail_dialog_sections():
    source = JS_PATH.read_text(encoding="utf-8")
    block = source.split("function initLocationDialog(", 1)[1].split("function initAlertRulesDialog", 1)[0]

    assert "ioa-detail-item" in block
    assert "ioa-detail-flow" in block
    assert "ioa-detail-department" in block
    assert "ioa-detail-condition" in block
    assert "ioa-detail-stock-slims" in block
    assert "ioa-detail-stock-mari" in block


def test_inventory_order_alert_list_js_import_overlay_has_spinner_css():
    css = (Path(__file__).resolve().parents[3] / "static" / "css" / "app.css").read_text(encoding="utf-8")
    assert ".ioa-import-overlay" in css
    assert ".ioa-import-spinner" in css
    assert "ioa-import-spin" in css


    css = (Path(__file__).resolve().parents[3] / "static" / "css" / "app.css").read_text(encoding="utf-8")
    assert "body.inventory-order-alert-page .ioa-alert-rules-dialog {\n  width: min(480px" in css
    assert "body.inventory-order-alert-page .ioa-location-dialog {\n  width: min(960px" in css
    assert "body.inventory-order-alert-page .ioa-detail-memo-col-at {\n  width: 140px" in css
    assert "body.inventory-order-alert-page .ioa-detail-memo-col-by {\n  width: 100px" in css
    assert "body.inventory-order-alert-page .ioa-detail-memo-col-content" not in css
    table_rule = css.split("body.inventory-order-alert-page .ioa-alert-rules-table,")[1].split("}")[0]
    assert "ioa-location-table" in table_rule
    assert "ioa-alert-rules-color-swatch" in css
    assert "td:last-child" not in css.split("ioa-alert-rules-row--supply-risk")[1].split("ioa-alert-rules-actions", 1)[0]
    shared_block = css.split("/* ポータル共通: 一覧・判定ルールダイアログの行背景色", 1)[1]
    assert "body.inventory-order-alert-page .ioa-alert-rules-row--supply-risk" in shared_block
    assert ".shipment-trend-page .st-row-decrease-strong," in shared_block


def test_inventory_order_alert_list_js_updates_confirmation_without_reload():
    source = JS_PATH.read_text(encoding="utf-8")
    assert "updateRowConfirmationState" in source
    assert "updateTableCounts" in source
    assert "getListFilterParams" in source
    assert "IoaListClient" in source
    # フィルタ条件の解決は saveConfirmation 側へ切り出し済み。
    # saveConfirmationStatus は「リロードせずに saveConfirmation へ委譲する」ことのみ担う。
    save_block = source.split("async function saveConfirmationStatus", 1)[1].split("function initConfirmationStatusSelects", 1)[0]
    assert "reloadInventoryOrderAlertPage" not in save_block
    assert "saveConfirmation(row," in save_block

    request_block = source.split("async function saveConfirmation(row", 1)[1].split("async function saveConfirmationStatus", 1)[0]
    assert "getListFilterParams" in request_block
    assert "reloadInventoryOrderAlertPage" not in request_block
    assert "updateRowFromConfirmation" in source
    assert "readRowKeysFromDomElement" in source
    assert "readRowKeys" in source
    assert "resolveRowKeysFromElement" in source
    assert 'getAttribute("data-confirmation-status")' in save_block
    assert "getRowConfirmationStatus" not in source


def test_inventory_order_alert_list_client_js_exists():
    client_path = Path(__file__).resolve().parents[3] / "static" / "js" / "inventory-order-alert-list-client.js"
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
        Path(__file__).resolve().parents[3] / "templates" / "inventory_order_alert" / "list.html"
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
        Path(__file__).resolve().parents[3] / "static" / "js" / "inventory-order-alert-list-client.js"
    ).read_text(encoding="utf-8")
    chrg_block = source.split("custChrgSelect?.addEventListener", 1)[1].split("custCodeSelect?.addEventListener", 1)[0]
    cust_block = source.split("custCodeSelect?.addEventListener", 1)[1].split("Core.bindPaginationControls", 1)[0]
    assert 'itemCd: ""' in chrg_block
    assert 'level1ItemCd: ""' in chrg_block
    assert 'itemCd: ""' in cust_block
    assert 'level1ItemCd: ""' in cust_block


def test_inventory_order_alert_list_client_js_resets_cust_code_on_chrg_change():
    source = (
        Path(__file__).resolve().parents[3] / "static" / "js" / "inventory-order-alert-list-client.js"
    ).read_text(encoding="utf-8")
    chrg_block = source.split("custChrgSelect?.addEventListener", 1)[1].split("custCodeSelect?.addEventListener", 1)[0]
    assert "state.custCode" not in chrg_block
    assert chrg_block.count('""') >= 3
