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
    # 関数は IIFE 内の 4 スペースインデント。区切りを誤るとファイル末尾まで拾ってしまう（2026-09-30 修正）
    build_block = source.split("function buildAnchoredStockTrend", 1)[1].split("\n    function ", 1)[0]
    render_block = source.split("function renderAnchoredStockChart", 1)[1].split("\n    function ", 1)[0]

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

    # text-anchor は setAttribute ではなく label.style（インラインstyle）で上書きする。
    # setAttribute はCSSクラス（.ioa-anchored-stock-trend-axis-label の text-anchor: middle）
    # より優先度が低く上書きされないため、実際の描画では見切れが解消されなかった不具合の修正。
    assert "label.style.textAnchor" in render_block
    assert '"start"' in render_block
    assert '"end"' in render_block
    assert 'setAttribute("text-anchor"' not in render_block


def test_TC_SHC_X_017_list_js_renders_y_axis_scale_labels():
    source = JS_PATH.read_text(encoding="utf-8")
    render_block = source.split("function renderAnchoredStockChart", 1)[1].split("\n  function ", 1)[0]

    # 左側に数量目盛りを表示する。
    assert "ioa-anchored-stock-trend-y-axis-label" in render_block
    assert "toLocaleString" in render_block


def test_TC_SHC_X_018_list_js_renders_evenly_spaced_grid_lines():
    source = JS_PATH.read_text(encoding="utf-8")
    render_block = source.split("function renderAnchoredStockChart", 1)[1].split("\n  function ", 1)[0]

    # Excel風の等間隔複数目盛り線（GRID_LINE_COUNT 分割）をループで描画する。
    assert "GRID_LINE_COUNT" in render_block
    assert "ioa-anchored-stock-trend-grid-line" in render_block


def test_TC_SHC_X_019_render_anchored_stock_chart_no_longer_takes_mari_series():
    """推定在庫推移グラフはSLIMS起点の1系列のみ描画する（MARI起点は撤去。DECISIONS.md参照）。"""
    source = JS_PATH.read_text(encoding="utf-8")
    render_block = source.split("function renderAnchoredStockChart", 1)[1].split("\n  function ", 1)[0]

    assert "mariSeries" not in render_block
    assert "ioa-anchored-stock-trend-line--mari" not in render_block
    assert "ioa-anchored-stock-trend-point--mari" not in render_block
    assert "ioa-anchored-stock-trend-legend-item--mari" not in render_block
    assert "MARI起点" not in render_block


def test_TC_SHC_X_020_fill_detail_sections_does_not_build_mari_anchored_trend():
    """MARI 起点の系列は算出しない（撤去済み）。入荷推移は棒グラフ用に第3引数で渡す。"""
    source = JS_PATH.read_text(encoding="utf-8")
    fill_block = source.split("function fillDetailSections", 1)[1].split("async function openLocationDialog", 1)[0]

    assert "mariAnchor" not in fill_block
    assert "mariAnchoredTrend" not in fill_block
    assert (
        "renderAnchoredStockChart(anchoredStockTrendSection, slimsAnchoredTrend, incomingTrend)"
        in fill_block
    )


def test_TC_SHC_X_021_render_anchored_stock_chart_draws_incoming_bars():
    """入荷実績(V-217)を棒グラフとして重ねて描く（design.md §6.6）。"""
    source = JS_PATH.read_text(encoding="utf-8")
    render_block = source.split("function renderAnchoredStockChart", 1)[1].split(
        "\n    function fillDetailSections", 1
    )[0]

    assert "incomingSeries" in render_block
    assert 'createElementNS(svgNs, "rect")' in render_block
    assert "ioa-anchored-stock-trend-bar--incoming" in render_block


def test_TC_SHC_X_022_chart_scale_includes_incoming_quantities():
    """入荷が推定在庫を上回る月でも棒が切れないよう、値域に入荷数量を算入する。"""
    source = JS_PATH.read_text(encoding="utf-8")
    render_block = source.split("function renderAnchoredStockChart", 1)[1].split(
        "\n    function fillDetailSections", 1
    )[0]

    assert "incomingQtys" in render_block
    # 値域は実績（points）と入荷の棒を含む（09 で予測部分を撤去）
    assert "Math.max(1, ...points.map((point) => Number(point.qty) || 0), ...incomingQtys)" in render_block


def test_TC_SHC_X_023_legend_shows_incoming_item():
    source = JS_PATH.read_text(encoding="utf-8")
    render_block = source.split("function renderAnchoredStockChart", 1)[1].split(
        "\n    function fillDetailSections", 1
    )[0]

    assert "ioa-anchored-stock-trend-legend-item--incoming" in render_block
    assert "入荷(MARI)" in render_block


def test_TC_SHC_X_024_parse_anchor_qty_treats_empty_stock_as_zero():
    """在庫数が「該当なし」（空）の行は 0 を起点に履歴を描く（ユビキタス言語 V-218）。"""
    source = JS_PATH.read_text(encoding="utf-8")
    func_block = source.split("function parseAnchorQty", 1)[1].split("\n  function ", 1)[0]

    # 空文字は 0 を返す（未取得の "－" は Number() が NaN になり null を返す）。
    assert "if (!trimmed) {\n        return 0;\n      }" in func_block


def test_TC_SHC_X_025_parse_anchor_qty_returns_null_for_not_fetched_marker():
    """未取得（"－"）は SLIMS 未参照なので 0 起点にせず、グラフを出さない。"""
    source = JS_PATH.read_text(encoding="utf-8")
    func_block = source.split("function parseAnchorQty", 1)[1].split("\n  function ", 1)[0]
    build_block = source.split("function buildAnchoredStockTrend", 1)[1].split("\n  function ", 1)[0]

    assert "Number.isFinite(number) ? number : null" in func_block
    # null の場合は空配列を返し、呼び出し側が「算出できません」を表示する経路が残っている。
    assert "anchorQty === null" in build_block
    assert "return [];" in build_block


def test_TC_SHC_X_026_incoming_bars_are_drawn_behind_the_line():
    """棒は折れ線より先に描画し、折れ線・データ点を隠さない（design.md §6.6）。"""
    source = JS_PATH.read_text(encoding="utf-8")
    render_block = source.split("function renderAnchoredStockChart", 1)[1].split(
        "\n    function fillDetailSections", 1
    )[0]

    assert render_block.index("drawIncomingBars(incoming)") < render_block.index("drawSeries(slims,")


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


def test_x017_list_client_js_state_has_period_key_and_no_axis():
    """TC-SFV-X-017: 状態に flowAxis がなく、evaluationPeriods / periodKey で判定期間を扱う。"""
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")

    assert "flowAxis" not in source
    assert "flowPeriods" not in source
    assert "resolveFlowPeriod(" not in source
    assert "state.periodKey" in source
    assert "payload.evaluationPeriods" in source
    assert "payload.defaultPeriodKey" in source
    assert '"#ioa-evaluation-period"' in source
    assert '"#ioa-flow-axis"' not in source
    assert '"#ioa-flow-period"' not in source


def test_x017_list_client_js_reads_year_matrix_keys():
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")

    assert 'DEFAULT_PERIOD_KEY = "Y1"' in source
    # 07 で 7 区分になりランクがずれた（TC-FQR-C-006）
    assert '"low-flow-no-incoming": 2' in source
    assert '"low-flow-no-shipment": 4' in source
    assert "supply-risk" not in source
    assert "excess-stock-risk" not in source


def test_x018_list_client_js_renders_status_by_template_replacement_only():
    """TC-SFV-X-018: 状況は recommendedActions.statusTemplate の置換だけで描き、日付比較を JS に持たない。"""
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    block = source.split("function renderStatusText(", 1)[1].split("\n  }\n", 1)[0]

    assert '.replace("{period}"' in block
    assert '.replace("{last_incoming}"' in block
    assert '.replace("{last_ship}"' in block
    assert "payload.recommendedActions" in source
    assert "statusTemplate" in source
    # 判定条件（暦月の遡り比較）を JS に持たない。日付の生成は並び替えキー（dateSortKey）だけ
    assert "addCalendarMonths" not in source
    assert "is_within_evaluation_period" not in source
    assert "months" not in block
    assert "new Date(" not in block
    status_and_cell = source.split("function flowStatusOf(", 1)[1].split("function renderTableBody(", 1)[0]
    assert "new Date(" not in status_and_cell
    # セルは区分名のみ（05 design §6.3、2026/09/17 改訂）。状況等は詳細ダイアログ用の API で引く
    cell = source.split("function renderFlowCell(", 1)[1].split("function renderTableBody(", 1)[0]
    assert "ioa-flow-cell" in cell and "ioa-flow-quadrant" in cell
    for removed in ("ioa-flow-cell-head", "ioa-no-incoming-badge", "ioa-flow-status", "ioa-flow-action", "ioa-flow-departments", "ioa-flow-urgency"):
        assert removed not in cell
    assert 'quadrantKey === QUADRANT_NORMAL_FLOW_KEY' in cell
    assert "getFlowStatus(custCode, itemCd, quadrantKey)" in source


def test_x019_list_client_js_syncs_only_period_to_url():
    """TC-SFV-X-019: URL 同期は period のみ。axis は書かない。"""
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    block = source.split("function updateUrl()", 1)[1].split("function renderConfirmationSelect", 1)[0]

    assert 'params.set("period"' in block
    assert 'params.set("axis"' not in block
    assert 'params.set("axis"' not in source


def test_list_client_js_counts_use_new_quadrant_names():
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")

    assert "lowFlowNoIncoming" in source
    assert "lowFlowNoShipment" in source
    assert "supplyRisk" not in source
    assert "excessStockRisk" not in source
    # 08: 件数サマリは対応区分
    assert "発注遅れ ${counts.orderOverdue} 件" in source
    assert "供給リスク品" not in source
    assert "在庫過剰リスク品" not in source


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
    # 08: 件数サマリは対応区分（発注遅れ / 納期確認 / 要発注 / 要監視 / 対象外）
    assert "発注遅れ ${counts.orderOverdue ?? 0} 件" in source
    assert "対象外 ${counts.noneResponse ?? 0} 件" in source
    assert "供給リスク品" not in source
    assert "在庫過剰リスク品" not in source
    assert "supplyRisk" not in source
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
    assert "ioa-detail-condition" not in block
    # 10 REQ-DDC-F-008: 流動区分の区分は詳細ダイアログから撤去した（一覧の列・絞り込みには残る）
    for class_name in (
        "ioa-detail-flow-quadrant",
        "ioa-detail-flow-status",
        "ioa-detail-flow-reasons",
        "ioa-detail-evaluation-period",
        "ioa-detail-recommended-action",
        "ioa-detail-department",
    ):
        assert class_name not in block, f"{class_name} が詳細ダイアログの JS に残っている"
    # 品番情報の中身
    assert "ioa-detail-stock-slims" in block
    assert "ioa-detail-stock-mari" in block
    # 流動区分由来の文言を引くヘルパーはもう詳細ダイアログから呼ばない（REQ-DDC-F-008）
    for helper in ("getFlowStatus", "getRecommendedAction", "getEvaluationPeriodLabel", "getFlowConditionLabel"):
        assert helper not in block, f"{helper} が詳細ダイアログの JS に残っている"
    # 判定サマリと月別内示は残る
    assert "renderAssessment" in block
    assert "renderMonthlyDemand" in block


def test_inventory_order_alert_list_js_import_overlay_has_spinner_css():
    css = (Path(__file__).resolve().parents[3] / "static" / "css" / "app.css").read_text(encoding="utf-8")
    assert ".ioa-import-overlay" in css
    assert ".ioa-import-spinner" in css
    assert "ioa-import-spin" in css


    css = (Path(__file__).resolve().parents[3] / "static" / "css" / "app.css").read_text(encoding="utf-8")
    assert "body.inventory-order-alert-page .ioa-alert-rules-dialog {\n" in css
    assert "width: min(900px" in css
    assert "body.inventory-order-alert-page .ioa-location-dialog {\n  width: min(960px" in css
    assert "body.inventory-order-alert-page .ioa-detail-memo-col-at {\n  width: 140px" in css
    assert "body.inventory-order-alert-page .ioa-detail-memo-col-by {\n  width: 100px" in css
    assert "body.inventory-order-alert-page .ioa-detail-memo-col-content" not in css
    table_rule = css.split("body.inventory-order-alert-page .ioa-alert-rules-table,")[1].split("}")[0]
    assert "ioa-location-table" in table_rule
    # 判定ルールダイアログの行は流動区分で色付けしない（2026/09/18: 色の意味は在庫切れリスクのみ）
    assert "ioa-alert-rules-color-swatch" not in css
    assert "ioa-alert-rules-row--" not in css
    shared_block = css.split("/* ポータル共通: 一覧・判定ルールダイアログの行背景色", 1)[1]
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


def test_TC_SHC_X_029_gonen_link_points_to_five_year_nine_result_page():
    """5年9組の検索結果ページを遷移先とする（design.md §6.7）。"""
    source = JS_PATH.read_text(encoding="utf-8")

    assert 'const GONEN_RESULT_PATH = "/app/production/five-year-nine/result"' in source
    assert "gonenLink.href = `${GONEN_RESULT_PATH}?${params.toString()}`" in source


def test_TC_SHC_X_030_gonen_link_passes_four_search_params():
    """得意先コード・得意先品番・年月・対象日付を渡し、設変値は5年9組側の既定に委ねる。"""
    source = JS_PATH.read_text(encoding="utf-8")
    func_block = source.split("function updateGonenLink", 1)[1].split("\n    function ", 1)[0]

    assert "new URLSearchParams({" in func_block
    assert "custCode," in func_block
    assert "custItem: itemCd," in func_block
    assert "yearMonth: currentYearMonth()," in func_block
    assert "asOfDate: todayIsoDate()," in func_block
    assert "optionChange" not in func_block


def test_TC_SHC_X_031_gonen_link_builds_dates_from_local_time():
    """年月は今月・対象日付は今日。UTC変換で前日・前月にずれる toISOString() は使わない。"""
    source = JS_PATH.read_text(encoding="utf-8")
    ym_block = source.split("function currentYearMonth", 1)[1].split("\n    function ", 1)[0]
    today_block = source.split("function todayIsoDate", 1)[1].split("\n    function ", 1)[0]

    assert "now.getFullYear()" in ym_block
    assert "now.getMonth() + 1" in ym_block
    assert "now.getFullYear()" in today_block
    assert "now.getDate()" in today_block
    assert "toISOString" not in ym_block
    assert "toISOString" not in today_block


def test_TC_SHC_X_032_gonen_link_hidden_when_search_keys_are_missing():
    """得意先コード・得意先品番のどちらかが欠けている行ではリンクを隠す。"""
    source = JS_PATH.read_text(encoding="utf-8")
    func_block = source.split("function updateGonenLink", 1)[1].split("\n    function ", 1)[0]

    assert "const canSearch = Boolean(custCode && itemCd)" in func_block
    assert "gonenLinkRow.hidden = !canSearch" in func_block


def test_gonen_link_is_wired_from_fill_detail_sections():
    source = JS_PATH.read_text(encoding="utf-8")
    fill_block = source.split("function fillDetailSections", 1)[1].split("async function openLocationDialog", 1)[0]

    assert 'updateGonenLink(custCode, row.dataset.itemCd || "")' in fill_block


def test_TC_SHC_X_033_client_js_exposes_reconciliation_unit_trends_getter():
    """推定在庫推移は照合単位（内作品番×仕入先を共有する得意先品番の集合）で合算する（design.md §6.6）。"""
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    getter_block = source.split("getItemTrends(itemCd)", 1)[1].split("},", 1)[0]

    assert "itemTrendsOf(itemCd)" in getter_block


def test_TC_SHC_X_034_units_sum_shipments_across_all_rows_in_the_unit():
    """出荷は行が (得意先, 得意先品番) で一意なので、照合単位の全行をそのまま合算する。"""
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    func_block = source.split("function buildReconciliationUnits", 1)[1].split("\n    function ", 1)[0]

    assert "unitRows.forEach((row) => sumTrendInto(shipmentTrend, row.shipment_trend))" in func_block


def test_TC_SHC_X_035_units_deduplicate_incoming_by_level1_pair():
    """入荷は (内作品番, 仕入先) 単位のため、同じ組を共有する行での重複計上を除く。"""
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    func_block = source.split("function buildReconciliationUnits", 1)[1].split("\n    function ", 1)[0]

    assert "const countedPairs = new Set()" in func_block
    assert "countedPairs.has(key)" in func_block
    assert "sumTrendInto(incomingTrend, row.incoming_trend)" in func_block


def test_TC_SHC_X_036_units_ignore_the_current_list_filter():
    """物理的な在庫・入荷は画面の絞り込みと無関係なので、未フィルタの全行で合算する。"""
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    func_block = source.split("function buildReconciliationUnits", 1)[1].split("\n    function ", 1)[0]

    assert "allRows.forEach" in func_block
    assert "applyListFilters" not in func_block


def test_TC_SHC_X_037_fill_detail_sections_uses_unit_level_trends_and_anchor():
    """詳細ダイアログは照合単位の合算値と合算した起点で逆算・棒描画する。"""
    source = JS_PATH.read_text(encoding="utf-8")
    fill_block = source.split("function fillDetailSections", 1)[1].split("async function openLocationDialog", 1)[0]

    assert 'getItemTrends?.(row.dataset.itemCd || "")' in fill_block
    assert "itemTrends.shipmentTrend || []" in fill_block
    assert "itemTrends.incomingTrend || []" in fill_block
    assert "sumUnitAnchorQty(itemTrends.stocks, row.dataset.stockQty)" in fill_block
    assert "renderAnchorBreakdown(itemTrends.stocks, slimsAnchor)" in fill_block
    # 行単位のアクセサは推定在庫推移の算出には使わない（重複計上の原因だったため）。
    assert "getShipmentTrend?.(" not in fill_block
    assert "getIncomingTrend?.(" not in fill_block


def test_TC_SHC_X_039_reconciliation_units_are_built_as_connected_components():
    """得意先品番と (内作品番, 仕入先) を節点とする二部グラフの連結成分を単位とする。"""
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    func_block = source.split("function buildReconciliationUnits", 1)[1].split("\n    function ", 1)[0]

    # Union-Find で辺 (得意先品番 ―― 内作品番×仕入先) をつなぐ。
    assert "allRows.forEach((row) => union(itemKeyOf(row), pairKeyOf(row)))" in func_block
    assert "const union = (a, b)" in func_block


def test_TC_SHC_X_040_anchor_sums_unit_stocks_and_keeps_not_fetched_rule():
    """起点は照合単位の在庫合計。全品番が未取得なら算出しない（従来の非表示動作を維持）。"""
    source = JS_PATH.read_text(encoding="utf-8")
    func_block = source.split("function sumUnitAnchorQty", 1)[1].split("\n    // 照合単位が複数", 1)[0]

    assert "parseAnchorQty(entry.stockDisplay)" in func_block
    assert "return hasKnown ? total : null" in func_block


def test_TC_SHC_X_041_anchor_breakdown_shown_only_for_multi_item_units():
    """起点の内訳は複数品番の照合単位のときだけ表示し、品番が多い場合は丸める。"""
    source = JS_PATH.read_text(encoding="utf-8")
    func_block = source.split("function renderAnchorBreakdown", 1)[1].split("\n    // 5年9組", 1)[0]

    assert "entries.length < 2" in func_block
    assert "anchorBreakdown.hidden = true" in func_block
    assert "ANCHOR_BREAKDOWN_MAX_ITEMS" in func_block
    assert "他${rest}品番" in func_block


# --- 05_single-flow-view 第 2 段階: TC-SFV-X-020 ---


def test_x020_list_client_js_sorts_months_of_stock_with_empty_last():
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    block = source.split("function nullsLastSortValue(", 1)[1].split("function sortValue(", 1)[0]

    assert "monthsOfStock" in block
    assert 'sortDirectionOf(state, column) === "desc"' in block
    # 空は昇順・降順とも末尾: desc では [0, …]、asc では [1, …] を空に割り当てる
    assert "isEmpty ? [0, 0] : [1, number]" in block
    assert "isEmpty ? [1, 0] : [0, number]" in block
    assert 'column === "months_of_stock"' in source
    assert "payload.sortOnlyColumns" in source
    assert "sortableColumns.concat(sortOnlyColumns)" in source


def test_stage2_list_client_js_keeps_urgency_text_for_detail_dialog_only():
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    block = source.split("function urgencyTextOf(", 1)[1].split("// 流動区分セルは区分名のみ", 1)[0]

    assert 'forecast.basis === "なし"' in block
    assert "十分" in block
    assert "に在庫切れ" in block
    assert "getUrgencyText(custCode, itemCd)" in source
    cell = source.split("function renderFlowCell(", 1)[1].split("function renderTableBody(", 1)[0]
    assert "ioa-flow-urgency" not in cell




def test_srr_c005_list_client_js_handles_response_class():
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")

    assert 'RESPONSE_CLASS_RANK = { "order-overdue": 0, "delivery-check": 1, "order-needed": 2, watch: 3, none: 4 }' in source
    assert "function rowResponseClassKey(row)" in source
    assert 'column === "response_class"' in source
    assert 'column === "stockout_date" || column === "order_deadline"' in source
    assert "`response-${responseKey}`" in source  # 行の色は対応区分のみ
    assert 'params.set("response_class"' in source
    assert 'params.set("ordering_method"' in source
    assert '"#ioa-response-class"' in source and '"#ioa-ordering-method"' in source
    assert "getResponseClass(custCode, itemCd)" in source
    # 判定はサーバ値のみ。JS で発注残やリードタイムを比較しない
    cell = source.split('if (column.key === "response_class")', 1)[1].split("return `<td", 1)[0]
    assert "leadTime" not in cell and "overdueOrderQty" not in cell




def test_srr_c009_replenishment_terms_are_gone_from_the_js():
    """補充見込み・猶予日数・長期納期超過は 08 で撤去した（TC-SRR-C-009）。"""
    for path in (JS_PATH, CLIENT_JS_PATH):
        source = path.read_text(encoding="utf-8")
        for term in ("replenishment", "daysUntilStockout", "shortageQty", "stockoutRiskKey", "補充見込み", "長期納期超過", "猶予日数"):
            assert term not in source, f"{path.name} に {term} が残っている"



# --- TC-FQR-C-006: 7 区分のランク・理由表示（07_flow-quadrant-refinement） ---


def test_fqr_c006_client_js_flow_quadrant_rank_has_seven_keys():
    """クライアント側のランクは 7 区分（欠品 2 区分と打ち切り候補を含む）。未知キーは通常流動品に倒れるため、
    ここが 4 キーのままだと欠品の行が通常流動品として表示されてしまう。"""
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    block = source.split("const FLOW_QUADRANT_RANK = {", 1)[1].split("};", 1)[0]

    for index, key in enumerate(
        [
            "stockout-no-incoming",
            "stockout",
            "low-flow-no-incoming",
            "dormant-stock",
            "low-flow-no-shipment",
            "discontinuation-candidate",
        ]
    ):
        assert f'"{key}": {index}' in block
    assert "[QUADRANT_NORMAL_FLOW_KEY]: 6" in block


def test_fqr_c006_client_js_exposes_flow_reasons():
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")

    assert "getFlowReasons(" in source
    assert "row.flowReasons" in source


def test_fqr_c005a_client_js_reads_flow_reasons_by_period():
    """理由も判定期間で変わるため、区分と同じく期間キーで引き直す（07 design §1-6）。"""
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    block = source.split("getFlowReasons(", 1)[1].split("getEvaluationPeriodLabel(", 1)[0]

    assert "flowReasonsByPeriod" in block
    assert "flowSelectionKey(state)" in block  # 既定は選択中の判定期間


def test_ddc_f008_flow_quadrant_section_is_removed_from_the_detail_dialog():
    """10 REQ-DDC-F-008: 流動区分の区分は詳細ダイアログから撤去（2026-09-30 ユーザー指示）。

    流動区分（S-203）自体は一覧の列・絞り込み・件数サマリ・CSV に残る。
    """
    source = JS_PATH.read_text(encoding="utf-8")
    template = (Path(__file__).resolve().parents[3] / "templates" / "inventory_order_alert" / "list.html").read_text(encoding="utf-8")

    for class_name in (
        "ioa-detail-flow-quadrant",
        "ioa-detail-flow-status",
        "ioa-detail-flow-reasons",
        "ioa-detail-evaluation-period",
    ):
        assert class_name not in source
        assert class_name not in template
    assert "renderFlowReasons" not in source


def test_fqr_c005b_rules_dialog_explains_the_evaluation_period_basis():
    """判定ルールダイアログで期間判断の基準を説明する（用語集 V-211「期間判断の基準」）。"""
    template = (Path(__file__).resolve().parents[3] / "templates" / "inventory_order_alert" / "list.html").read_text(encoding="utf-8")
    block = template.split('<dialog id="ioa-alert-rules-dialog"', 1)[1].split("</dialog>", 1)[0]

    assert "期間にかかわる判断はすべて上の判定期間で行います" in block
    assert "判定期間では変わりません" in block
    # 需要の定義は内示のみ（出荷実績は見ない。07 REQ-FQR-F-002）
    assert "需要は<strong>内示の有無</strong>" in block
    assert "内示または出荷実績" not in block


def test_fqr_c006_css_has_badges_for_the_new_quadrants():
    css = (Path(__file__).resolve().parents[3] / "static" / "css" / "app.css").read_text(encoding="utf-8")

    for key in ("stockout-no-incoming", "stockout", "discontinuation-candidate"):
        assert f"ioa-flow-quadrant--{key}" in css


# --- 09_stock-simulation-chart: TC-SSC-J-001〜005 ---


def test_ssc_j003_forecast_part_of_the_monthly_chart_is_removed():
    """V-218 の予測部分は撤去した（09 REQ-SSC-F-001）。在庫シミュレーション（V-237）へ移した。"""
    source = JS_PATH.read_text(encoding="utf-8")

    for name in (
        "buildForecastStockTrend",
        "plannedIncomingByMonth",
        "addMonthsToKey",
        "drawPlannedBars",
        "drawForecastSeries",
        "drawStockoutMarker",
        "予測在庫(内示)",
        "予定入荷(発注残)",
    ):
        assert name not in source, f"{name} が残っている"


def test_ssc_j004_monthly_chart_takes_no_forecast_arguments():
    source = JS_PATH.read_text(encoding="utf-8")
    chart = source.split("function renderAnchoredStockChart(", 1)[1].split("function fillDetailSections(", 1)[0]

    assert source.count("function renderAnchoredStockChart(sectionEl, slimsSeries, incomingSeries) {") == 1
    assert "forecastSeries" not in chart
    assert "stockoutMonth" not in chart
    assert "const points = slims;" in chart


def test_ssc_j001_build_stock_simulation_only_accumulates():
    """JS は累積するだけ。重複除去・工程の絞り込み・判定はサーバ側（09 design §1・§5.3）。"""
    source = JS_PATH.read_text(encoding="utf-8")
    block = source.split("function buildStockSimulation(", 1)[1].split("// 在庫推移（実績。V-218）", 1)[0]

    # 過去は遡り、未来は進む
    assert "qty = qty + (ship[key] || 0) - (incoming[key] || 0);" in block
    assert "qty = qty - (demand[key] || 0) + (planned[key] || 0);" in block
    # 判定ロジックは持ち込まない
    for term in ("order_cd", "orderCd", "level", "remainingQty", "leadTime", "safetyStock"):
        assert term not in block, f"{term} が JS に漏れている"


def test_ssc_j005_stockout_date_is_not_recalculated_in_js():
    """在庫切れ日・発注期限・安全在庫はサーバの判定値をそのまま描く。"""
    source = JS_PATH.read_text(encoding="utf-8")
    block = source.split("function renderStockSimulation(", 1)[1].split("async function openLocationDialog(", 1)[0]

    assert "info?.stockoutDate" in block
    assert "info?.orderDeadline" in block
    assert "info?.safetyStock" in block
    assert "info?.overdueOrderQty" in block


def test_ssc_j002_simulation_chart_draws_marks():
    source = JS_PATH.read_text(encoding="utf-8")
    block = source.split("function renderStockSimulationChart(", 1)[1].split("function renderStockSimulation(", 1)[0]

    # 縦線 3 本（取込日・発注期限・在庫切れ）と安全在庫の水平線
    assert 'drawVerticalLine(marks.asOfDate, "ioa-stock-simulation-now-line", "取込日")' in block
    assert 'drawVerticalLine(marks.orderDeadline, "ioa-stock-simulation-deadline-line", "発注期限")' in block
    assert 'drawVerticalLine(marks.stockoutDate, "ioa-stock-simulation-stockout-line", "在庫切れ")' in block
    assert "ioa-stock-simulation-safety-line" in block
    # 棒: 予定入荷と納期遅れ（納期遅れは線に足さない）
    assert "ioa-stock-simulation-planned-bar" in block
    assert "ioa-stock-simulation-overdue-bar" in block
    assert "線には足していません" in block
    # 折れ線は取込日までが実線、以降が点線
    assert "ioa-stock-simulation-line--actual" in block
    assert "ioa-stock-simulation-line--outlook" in block


def test_ssc_j006_date_axis_shows_every_day_without_the_year():
    """横軸は範囲内の全日を「月/日」で出す。年は重なるので出さない（2026-09-30 ユーザー指示）。"""
    source = JS_PATH.read_text(encoding="utf-8")
    block = source.split("function renderStockSimulationChart(", 1)[1].split("function renderStockSimulation(", 1)[0]

    # "2026-09-18" → "09/18"（slice(5)）。年 2 桁の slice(2) は使わない
    assert 'point.date.slice(5).replace("-", "/")' in block
    assert "point.date.slice(2)" not in block
    # 間引かずに全日ラベルを出す（month-first だけ強調）
    assert "ioa-stock-simulation-date-label" in block
    assert "ioa-stock-simulation-date-label--month-first" in block
    assert "ioa-stock-simulation-month-separator" in block


def test_ssc_j007_chart_scrolls_horizontally_with_a_fixed_axis():
    """全日付を出すと横に長いので、本体は横スクロール・Y 軸は左に固定する。"""
    source = JS_PATH.read_text(encoding="utf-8")
    block = source.split("function renderStockSimulationChart(", 1)[1].split("function renderStockSimulation(", 1)[0]

    assert "SIMULATION_DAY_WIDTH" in source
    assert "const plotWidth = series.length * SIMULATION_DAY_WIDTH;" in block
    assert 'scroller.className = "ioa-stock-simulation-scroll";' in block
    assert 'axisWrap.className = "ioa-stock-simulation-axis";' in block
    # 取込日あたりまでスクロールしておく
    assert "scroller.scrollLeft" in block

    css = (Path(__file__).resolve().parents[3] / "static" / "css" / "app.css").read_text(encoding="utf-8")
    # `.ioa-stock-simulation-scroll` は min-width の指定とスクロールの指定の 2 か所に出る
    blocks = [part.split("}", 1)[0] for part in css.split(".ioa-stock-simulation-scroll {")[1:]]
    assert any("overflow-x: auto" in part for part in blocks)
    for class_name in ("ioa-stock-simulation-axis", "ioa-stock-simulation-date-label--month-first", "ioa-stock-simulation-month-separator"):
        assert class_name in css


def test_ssc_j001_client_js_serves_the_simulation_materials():
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    block = source.split("getResponseClass(custCode, itemCd)", 1)[1].split("getFlowQuadrantLabel", 1)[0]

    for key in ("dailyShipment", "dailyIncoming", "unconfirmedOrderDaily", "plannedIncoming", "asOfDate"):
        assert key in block


def test_ssc_j001_simulation_uses_the_fixed_range_from_the_server():
    """左右の端はサーバが決めた固定値を使う（品目ごとに変えない）。"""
    source = JS_PATH.read_text(encoding="utf-8")
    block = source.split("function buildStockSimulation(", 1)[1].split("// 在庫推移（実績。V-218）", 1)[0]

    assert "series.rangeStart" in block
    assert "series.rangeEnd" in block
    # 動きのあった日から端を決めていない
    assert "if (day && day < first)" not in block


# --- 10_detail-dialog-cleanup: TC-DDC-J-001〜004 ---


def test_ddc_j001_no_headline_wording_in_the_js():
    """見出し文は domain が組み立てる。JS に文言を書かない（REQ-DDC-NF-003）。"""
    source = JS_PATH.read_text(encoding="utf-8")

    for phrase in ("在庫が切れます", "までに発注が必要", "在庫は切れません", "在庫は足ります", "は過ぎています", "を下回ります"):
        assert phrase not in source, f"文言 {phrase} が JS に漏れている"


def test_ddc_j002_render_assessment_only_fills_in_server_values():
    source = JS_PATH.read_text(encoding="utf-8")
    block = source.split("function renderAssessment(", 1)[1].split("function renderStockAndOrders(", 1)[0]

    assert "summary?.headline" in block
    assert "summary?.nextAction" in block
    assert "summary?.deadlineText" in block
    assert "summary?.reasons" in block
    # 判定も文言の組み立てもしない
    for term in ("stockoutDate", "orderDeadline", "leadTime", "Math."):
        assert term not in block, f"{term} が判定サマリの描画に漏れている"


def test_ddc_j003_demand_forecast_rendering_is_removed():
    source = JS_PATH.read_text(encoding="utf-8")

    assert "function renderDemandForecast(" not in source
    assert "function renderResponseClass(" not in source
    for class_name in ("ioa-detail-months-of-stock", "ioa-detail-stockout-month", "ioa-detail-demand-basis", "ioa-detail-demand-empty"):
        assert class_name not in source
    # 月別内示は材料として残す
    assert "ioa-detail-demand-monthly" in source
    assert "function renderMonthlyDemand(" in source


def test_ddc_j004_process_chain_and_stock_rendering_remain():
    source = JS_PATH.read_text(encoding="utf-8")

    assert "function renderProcessChain(" in source
    assert "function renderStockAndOrders(" in source
    block = source.split("function renderStockAndOrders(", 1)[1].split("function renderMonthlyDemand(", 1)[0]
    assert "renderProcessChain(info.processChain)" in block
    assert "riskFields.plannedIncoming" in block
    assert "在庫の計算に入れていません" in block


def test_ddc_j002_client_js_passes_the_summary_through():
    source = CLIENT_JS_PATH.read_text(encoding="utf-8")
    block = source.split("getResponseClass(custCode, itemCd)", 1)[1].split("getFlowQuadrantLabel", 1)[0]

    assert "row.assessmentSummary" in block


def test_ddc_simulation_note_does_not_repeat_the_summary():
    """在庫シミュレーション下の注記に在庫切れ日・発注期限を繰り返さない（2026-09-30 ユーザー指示）。"""
    source = JS_PATH.read_text(encoding="utf-8")
    block = source.split("function renderStockSimulationChart(", 1)[1].split("function renderStockSimulation(", 1)[0]
    note_block = block.split("if (note) {", 1)[1].split("}", 1)[0]

    for term in ("在庫切れ日", "発注期限", "納期遅れの発注残", "安全在庫"):
        assert term not in note_block, f"注記に {term} が残っている（判定サマリと重複）"
    assert "取り込み直すと表示されます" in note_block
