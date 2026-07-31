from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LIST_JS = ROOT / "static" / "js" / "shipment-trend-list.js"
CLIENT_JS = ROOT / "static" / "js" / "shipment-trend-list-client.js"
TEMPLATE = ROOT / "templates" / "shipment_trend" / "list.html"
CSS = ROOT / "static" / "css" / "app.css"


def test_shipment_trend_list_client_js_keeps_cust_name_on_row():
    source = CLIENT_JS.read_text(encoding="utf-8")
    assert "data-cust-name" in source
    assert "st-detail-open" not in source


def test_shipment_trend_list_client_js_uses_portal_list_core():
    source = CLIENT_JS.read_text(encoding="utf-8")
    assert "window.PortalListCore" in source
    assert "Core.renderTableHeaders" in source
    assert 'headerMode: "link"' in source
    assert 'sortColumnDataAttr: "data-st-sort-column"' in source
    assert "function initListClient()" in source
    assert "document.querySelector(\".shipment-trend-page\")" in source


def test_shipment_trend_list_js_initializes_independently_of_list_client():
    source = LIST_JS.read_text(encoding="utf-8")
    assert "onReady(initShipmentTrendPage)" in source
    assert "initListClientSafely" in source
    assert "bindDetailDialog()" in source
    assert "initShipmentTrendPage" in source
    assert "if (!root || !window.ShipmentTrendListClient)" not in source
    assert "PortalListSortDialog.init" in source
    assert "PortalListSortDialog.bind" not in source
    init_block = source.split("function initShipmentTrendPage()", 1)[1].split("onReady", 1)[0]
    assert init_block.index("bindDetailDialog()") < init_block.index("initListClientSafely()")
    assert init_block.index("initListClientSafely()") < init_block.index("bindSortDialog(listClient)")


def test_shipment_trend_list_js_detail_open_uses_row_click():
    source = LIST_JS.read_text(encoding="utf-8")
    detail_block = source.split("function bindDetailDialog()", 1)[1].split("function initListClientSafely", 1)[0]
    assert 'target.closest(".st-data-row")' in detail_block
    assert 'target.closest("select, option, button, a, label, textarea")' in detail_block
    assert "st-detail-open" not in detail_block
    assert "tableWrap.addEventListener" in detail_block
    assert "buildDetailTitle" in source
    assert "renderFiscalYearRows" in source
    assert "buildChartSvgMarkup" in source
    assert "xmlns=\"http://www.w3.org/2000/svg\"" in source
    assert "CHART_API" in source


def test_shipment_trend_alert_rules_dialog_table_fits_popup_with_row_colors():
    source = TEMPLATE.read_text(encoding="utf-8")
    assert "st-alert-rules-table-wrap" in source
    assert 'class="st-alert-rules-row st-alert-rules-row--{{ rule.class_key }}"' in source
    assert "st-alert-rules-color-swatch" in source
    assert "portal-alert-rules-select" in source
    assert "portal-alert-rules-setting" in source
    assert "st-threshold-select" not in source
    css = CSS.read_text(encoding="utf-8")
    assert "table-layout: fixed" in css.split(".st-alert-rules-table {", 1)[1].split("}", 1)[0]
    assert "overflow-x: hidden" in css.split(".st-alert-rules-table-wrap {", 1)[1].split("}", 1)[0]
    portal_select_block = css.split("body.portal-app-page .portal-alert-rules-select {", 1)[1].split("}", 1)[0]
    assert "padding: 6px 10px" in portal_select_block
    assert "border: 1px solid #cbd5e1" in portal_select_block
    shared_block = css.split("/* ポータル共通: 一覧・警告条件ダイアログの行背景色 */", 1)[1]
    assert ".shipment-trend-page .st-row-decrease-strong," in shared_block
    assert "#fde8e8" in shared_block
    assert "#fff8e1" in shared_block


def test_shipment_trend_list_template_detail_dialog_close_button_is_times_mark():
    source = TEMPLATE.read_text(encoding="utf-8")
    assert 'class="dialog-close-button st-detail-close"' in source
    assert 'st-detail-close" aria-label="閉じる">×</button>' in source
    assert 'id="st-detail-dialog"' in source
    assert "st-detail-open" not in source
    assert "詳細表示" not in source
    assert "st-chart-dialog" not in source


def test_shipment_trend_list_template_detail_dialog_has_fiscal_year_table():
    source = TEMPLATE.read_text(encoding="utf-8")
    assert "st-detail-metrics-table" in source
    assert "年度別出荷" in source
    assert "出荷推移" in source
    assert "基準年比変動率" in source
    assert "st-baseline-year-select" in source
    assert "st-filter-select" in source.split('id="st-baseline-year-select"', 1)[1].split("</select>", 1)[0]
    assert "自動（データ初年度）に戻す" in source
    assert ">初年度に戻す<" not in source
    assert "最小二乗法" in source
    assert "st-regression-stats" in source
    css = CSS.read_text(encoding="utf-8")
    detail_dialog_block = css.split("body.portal-app-page.shipment-trend-page .st-detail-dialog {", 1)[1].split("}", 1)[0]
    assert "overflow: hidden" in detail_dialog_block
    content_block = css.split("body.portal-app-page.shipment-trend-page .st-detail-content {", 1)[1].split("}", 1)[0]
    assert "overflow-y: auto" in content_block
    assert "overflow-x: hidden" in content_block


def test_shipment_trend_list_js_supports_year_month_chart_toggle():
    source = LIST_JS.read_text(encoding="utf-8")
    assert "resolveChartSeries" in source
    assert 'granularity === "year"' in source
    assert "yearPoints" in source
    assert "yearRegression" in source
    assert "st-chart-granularity-select" in source
    template = TEMPLATE.read_text(encoding="utf-8")
    assert 'value="year" selected' in template
    assert 'value="month"' in template
    assert "表示単位" in template


def test_shipment_trend_list_js_hatches_years_before_baseline():
    source = LIST_JS.read_text(encoding="utf-8")
    assert "st-detail-metrics-row--before-baseline" in source
    assert "baselineFiscalYear" in source.split("function renderFiscalYearRows", 1)[1].split(
        "function buildDetailTitle", 1
    )[0]
    assert "Number(year) < Number(baselineYear)" in source
    css = CSS.read_text(encoding="utf-8")
    hatch_block = css.split(".st-detail-metrics-row--before-baseline td {", 1)[1].split("}", 1)[0]
    assert "repeating-linear-gradient" in hatch_block
    assert "#e2e8f0" in hatch_block


def test_shipment_trend_list_js_draws_regression_and_baseline_api():
    source = LIST_JS.read_text(encoding="utf-8")
    assert "BASELINE_API" in source
    assert 'stroke="#f59e0b"' in source
    assert "chart.regression" in source
    assert "formatRegressionStats" in source
    assert "saveBaselineYear" in source
    assert "revertBaselineYear" in source
    assert "updateListFromChart" in source
    assert "window.location.reload()" not in source.split("async function saveBaselineYear", 1)[1].split(
        "async function revertBaselineYear", 1
    )[0]
    assert "window.location.reload()" not in source.split("async function revertBaselineYear", 1)[1].split(
        "baselineSelect?.addEventListener", 1
    )[0]
    assert "await loadDetail(" in source.split("async function saveBaselineYear", 1)[1]
    svg_block = source.split("function buildChartSvgMarkup", 1)[1].split("function renderChart", 1)[0]
    assert "regressionPath" in svg_block
    client = CLIENT_JS.read_text(encoding="utf-8")
    assert "updateRowBaselineMetrics" in client


def test_shipment_trend_list_template_includes_first_fiscal_year_column():
    source = TEMPLATE.read_text(encoding="utf-8")
    assert "display_first_fiscal_year" in source
    assert source.index("display_first_fiscal_year") < source.index("display_first_fy_total")


def test_shipment_trend_list_template_includes_item_cd_filter_with_autocomplete():
    source = TEMPLATE.read_text(encoding="utf-8")
    assert 'includes/portal_prefix_filter_field.html' in source
    assert 'name="item_cd"' in source
    assert 'datalist_id="st-item-cd-options"' in source
    assert "portal-list-prefix-filter.js" in source
    assert "portal-list-dependent-cust-filter.js" in source
    assert source.index("portal-list-dependent-cust-filter.js") < source.index(
        "shipment-trend-list-client.js"
    )
    client_js = CLIENT_JS.read_text(encoding="utf-8")
    assert "PortalListPrefixFilter" in client_js
    assert "createPrefixColumnFilter" in client_js
    assert "itemCdColumnFilter" in client_js


def test_shipment_trend_list_template_item_cd_filter_label_is_cust_item_cd():
    source = TEMPLATE.read_text(encoding="utf-8")
    assert 'label="内作品番"' in source
    assert 'placeholder="内作品番"' in source


def test_shipment_trend_list_client_clears_item_cd_on_cust_change():
    source = CLIENT_JS.read_text(encoding="utf-8")
    chrg_block = source.split("custChrgSelect?.addEventListener", 1)[1].split("custCodeSelect?.addEventListener", 1)[0]
    cust_block = source.split("custCodeSelect?.addEventListener", 1)[1].split("Core.bindPaginationControls", 1)[0]
    assert 'itemCd: ""' in chrg_block
    assert 'itemCd: ""' in cust_block


def test_shipment_trend_list_client_resets_cust_code_on_chrg_change():
    source = CLIENT_JS.read_text(encoding="utf-8")
    chrg_block = source.split("custChrgSelect?.addEventListener", 1)[1].split("custCodeSelect?.addEventListener", 1)[0]
    assert "state.custCode" not in chrg_block
    assert chrg_block.count('""') >= 2


def test_shipment_trend_list_template_item_cd_is_plain_text():
    source = TEMPLATE.read_text(encoding="utf-8")
    assert "st-item-link" not in source
    assert "{{ row.item_cd }}" in source


def test_shipment_trend_chart_renders_line_graph():
    source = LIST_JS.read_text(encoding="utf-8")
    chart_block = source.split("function buildChartSvgMarkup", 1)[1].split("function renderChart", 1)[0]
    assert '<path d="' in chart_block
    assert "<circle" in chart_block
    assert "stroke-dasharray" in chart_block
    assert "<rect" not in chart_block


def test_shipment_trend_chart_renders_marker_tooltips():
    source = LIST_JS.read_text(encoding="utf-8")
    svg_block = source.split("function buildChartSvgMarkup", 1)[1].split("function renderChart", 1)[0]
    assert "buildMarkerTooltipLabel" in source
    assert "st-chart-marker-hit" in svg_block
    assert "bindChartMarkerTooltips" in source
    assert "st-chart-tooltip" in source
    css = CSS.read_text(encoding="utf-8")
    assert ".st-chart-tooltip" in css


def test_shipment_trend_chart_renders_monthly_axis():
    source = LIST_JS.read_text(encoding="utf-8")
    svg_block = source.split("function buildChartSvgMarkup", 1)[1].split("function renderChart", 1)[0]
    assert "resolveChartLayout" in source
    assert "measureChartContainerWidth" in source
    assert "shouldShowSemiannualAxisLabel" in source
    assert "CHART_HEIGHT = 440" in source
    assert 'width="100%"' in svg_block
    assert "horizontalGridLines" in svg_block
    assert "monthGridLines" not in svg_block
    assert "monthSlotWidth" in svg_block
    assert 'y1="${y.toFixed(1)}"' in svg_block.split("horizontalGridLines", 1)[1].split("const labels", 1)[0]
    assert "chartBottom.toFixed(1)" not in svg_block.split("horizontalGridLines", 1)[1].split("const labels", 1)[0]
    css = CSS.read_text(encoding="utf-8")
    canvas_block = css.split(".st-chart-canvas-wrap {", 1)[1].split("}", 1)[0]
    assert "overflow-x: hidden" in canvas_block
    assert "width: 100%" in canvas_block
    assert "overflow-x: auto" not in canvas_block


def test_shipment_trend_chart_y_axis_scale_fits_max_near_top():
    source = LIST_JS.read_text(encoding="utf-8")
    scale_block = source.split("function buildYAxisScale", 1)[1].split("function buildChartSvgMarkup", 1)[0]
    assert "step * intervalCount" not in scale_block
    assert "candidate < axisMax" in scale_block


def test_shipment_trend_chart_renders_y_axis_ticks():
    source = LIST_JS.read_text(encoding="utf-8")
    chart_block = source.split("function buildYAxisScale", 1)[1].split("function buildChartSvgMarkup", 1)[0]
    svg_block = source.split("function buildChartSvgMarkup", 1)[1].split("function renderChart", 1)[0]
    assert "buildYAxisScale(maxQty, 5)" in svg_block
    assert "yAxisLine" in svg_block
    assert "yAxisTicks" in svg_block
    assert "padding.left - 6" in svg_block
    assert "formatChartQtyLabel" in source


def test_shipment_trend_list_template_loads_portal_list_scripts_at_content_end():
    source = TEMPLATE.read_text(encoding="utf-8")
    assert "portal-list-core.js" in source
    assert "portal-list-sort-dialog.js" in source
    assert "shipment-trend-list-client.js" in source
    assert "shipment-trend-list.js" in source
    assert "{% block extra_head %}" not in source
    assert source.index("portal-list-core.js") < source.index("shipment-trend-list-client.js")
    assert source.index("st-detail-dialog") < source.index("shipment-trend-list.js")


def test_shipment_trend_table_css_matches_inventory_order_alert_layout():
    css = CSS.read_text(encoding="utf-8")
    assert ".shipment-trend-page .st-table-card" in css
    assert "flex-direction: column" in css.split(".shipment-trend-page .st-table-card")[1].split("}")[0]
    assert ".shipment-trend-page .st-table-wrap" in css
    assert "position: sticky" in css.split(".shipment-trend-page .st-table th")[1].split("}")[0]
    assert "body.portal-app-page.shipment-trend-page .content > .st-table-card" in css


def test_shipment_trend_table_does_not_scroll_horizontally():
    css = CSS.read_text(encoding="utf-8")
    wrap_block = css.split(".shipment-trend-page .st-table-wrap {", 1)[1].split("}", 1)[0]
    table_block = css.split(".shipment-trend-page .st-table {", 1)[1].split("}", 1)[0]
    cell_block = css.split(".shipment-trend-page .st-table th,\n.shipment-trend-page .st-table td {", 1)[1].split("}", 1)[0]
    content_block = css.split("body.portal-app-page.shipment-trend-page .content {", 1)[1].split("}", 1)[0]
    card_block = css.split("body.portal-app-page.shipment-trend-page .content > .st-table-card {", 1)[1].split("}", 1)[0]
    assert "overflow-x: hidden" in wrap_block
    assert "overflow-y: auto" in wrap_block
    assert "min-width: 0" in wrap_block
    assert "table-layout: fixed" in table_block
    assert "width: 100%" in table_block
    assert "width: max-content" not in table_block
    assert "max-width: 0" in cell_block
    assert "overflow-x: hidden" in content_block
    assert "min-width: 0" in card_block


def test_shipment_trend_list_js_shows_refresh_loading_overlay():
    source = LIST_JS.read_text(encoding="utf-8")
    assert "initRefreshForm" in source
    assert "showRefreshLoading" in source
    assert "st-refresh-overlay" in source
    assert "st-refresh-loading" in source
    template = TEMPLATE.read_text(encoding="utf-8")
    assert 'id="st-refresh-overlay"' in template
    css = CSS.read_text(encoding="utf-8")
    assert ".st-refresh-overlay" in css
    assert ".st-refresh-spinner" in css
    assert "body.shipment-trend-page.st-refresh-loading" in css
    assert ".shipment-trend-page .st-table tbody tr.st-data-row" in css
    assert "cursor: pointer" in css.split(".shipment-trend-page .st-table tbody tr.st-data-row")[1].split("}")[0]
    detail_dialog_block = css.split("body.portal-app-page.shipment-trend-page .st-detail-dialog {", 1)[1].split("}", 1)[0]
    assert "1920px" in detail_dialog_block
