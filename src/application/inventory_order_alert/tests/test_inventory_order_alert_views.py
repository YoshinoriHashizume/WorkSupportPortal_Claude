from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from application.inventory_order_alert.infrastructure.persistence.summary_snapshot_repository import store_summary_snapshot
from application.inventory_order_alert.models import SlimsStockImport
from application.portal.models import PortalMenuGroupAccess


@pytest.fixture
def production_user(db):
    user = get_user_model().objects.create_user(username="10002", last_name="生産", first_name="担当")
    admin_group, _ = Group.objects.get_or_create(name="管理者")
    user.groups.add(admin_group)
    PortalMenuGroupAccess.objects.get_or_create(user=user, group_key="production")
    return user


STOCK_SUMMARY_HEADING_SUFFIX = "時点の集計結果を表示しています。"


def _sample_export_row() -> dict[str, object]:
    return {
        "cust_code": "112",
        "cust_name": "テスト得意先",
        "cust_chrg_psn_cd": "A01",
        "item_cd": "90249-10112",
        "level1_item_cd": "90249-10112-9209",
        "level1_vend_cd": "9209",
        "level1_vend_name": "小野メッキ",
        "last_incoming_date": "",
        "last_ship_date": "2026/06/15",
        "post_shipment_count": 1,
        "post_shipment_total_qty": 250,
        "stock_qty": "100",
        "stock_location_summary": "2D0-03-5",
        "stock_location_detail": "2D0-03-5=100",
        "stock_as_of_label": "2026年6月17日時点の在庫",
        "confirmation_status": "未確認",
        "confirmed_at": "",
        "confirmed_by": "",
        "confirmation_memo": "",
    }


def _dormant_stock_row(**overrides: object) -> dict[str, object]:
    """既定の判定期間（1 年、基準日 2026/6/17）で在庫死蔵品になる行。"""
    return _sample_export_row() | {
        "last_incoming_date": "2022/01/31",
        "last_ship_date": "2025/02/01",
        "post_shipment_count": 2,
        **overrides,
    }


@pytest.mark.django_db
def test_list_page_embeds_list_client_payload(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert 'id="ioa-list-data"' in html
    assert '"cust_code": "112"' in html or '"cust_code":"112"' in html
    assert 'onchange="this.form.submit()"' not in html
    assert "/static/js/inventory-order-alert-list-client.js" in html


@pytest.mark.django_db
def test_list_page_requires_login(client):
    response = client.get("/app/production/inventory-order-alert")
    assert response.status_code == 302
    assert "/login" in response.url


@pytest.mark.django_db
@patch("application.inventory_order_alert.infrastructure.persistence.slims_stock_repository.run_summary_aggregation")
def test_list_page_post_imports_slims_csv(mock_aggregate, client, production_user):
    mock_aggregate.return_value = ("", 0, "")
    fixture = Path(__file__).resolve().parent / "fixtures" / "slims_stock_sample_wkatqt.csv"
    client.force_login(production_user)
    before_count = SlimsStockImport.objects.count()

    with fixture.open("rb") as csv_file:
        response = client.post(
            "/app/production/inventory-order-alert",
            {"slims_csv": csv_file},
        )

    assert response.status_code == 200
    assert SlimsStockImport.objects.count() == before_count + 1
    html = response.content.decode("utf-8")
    assert "SLIMS 在庫 CSV を取り込み" in html
    mock_aggregate.assert_called_once()


@pytest.mark.django_db
def test_list_page_shows_slims_import_in_table_head(client, production_user):
    client.force_login(production_user)
    response = client.get("/app/production/inventory-order-alert")
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "取込・集計" not in html
    assert 'class="card stack ioa-import-card"' not in html
    assert "SLIMS在庫CSV" in html
    assert 'id="ioa-import-overlay"' in html
    assert "SLIMS 在庫 CSV を取込中" in html
    assert 'class="ioa-table-actions"' in html
    assert "SLIMS 在庫 CSVを選択してください" not in html
    assert "ファイルが選択されていません" not in html
    assert "CSV 出力（全件）" not in html
    assert "検索条件" not in html
    assert "表示する在庫発注データは全員で共有です。" not in html


@pytest.mark.django_db
def test_list_page_shows_favorite_toggle(client, production_user):
    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert 'data-menu-key="inventory-order-alert"' in html
    assert 'class="favorite-toggle portal-title-favorite"' in html
    assert "在庫発注アラートのお気に入りを切り替え" in html
    assert 'class="portal-page-description"' in html
    assert "SLIMS 在庫と基幹入出荷から、仕入先確認が必要な品目を一覧します。" in html


@pytest.mark.django_db
def test_list_page_shows_flow_quadrant_rules_button_and_dialog(client, production_user):
    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert "判定ルール" in html
    assert 'id="ioa-alert-rules-dialog"' in html
    assert 'class="ioa-alert-rules-table-wrap"' in html
    # 読み取り専用の凡例になり、月数セレクトと保存ボタンは撤去した（design.md §6.6.5）。
    assert 'id="ioa-warning-shipment-months"' not in html
    assert 'id="ioa-warning-incoming-months"' not in html
    assert "ioa-alert-rules-save" not in html
    assert "低流動品（入荷なし）" in html
    assert "在庫死蔵品" in html
    assert "低流動品（出荷なし）" in html
    assert "通常流動品" in html
    assert "調達G・営業G・生産管理" in html
    assert "期間内入荷" in html


@pytest.mark.django_db
def test_list_page_has_exactly_one_alert_rules_open_button(client, production_user):
    """開くボタンが重複すると JS の結線先とずれて無反応になるため 1 個に保つ。"""
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert html.count("ioa-alert-rules-open") == 1
    # 旧「警告条件」ボタンは判定ルールに置換済み（design.md §6.6.5）。
    assert "警告条件" not in html


@pytest.mark.django_db
def test_list_page_places_alert_rules_button_first_in_header_actions(client, production_user):
    """ヘッダーのアクション行は 判定ルール → SLIMS在庫CSV → CSV出力 → 設定 の順に並べる。"""
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    actions_pos = html.index('class="ioa-table-actions"')
    alert_rules_pos = html.index("ioa-alert-rules-open", actions_pos)
    slims_pos = html.index("SLIMS在庫CSV", actions_pos)
    csv_pos = html.index(">CSV 出力<", actions_pos)
    assert actions_pos < alert_rules_pos < slims_pos < csv_pos


@pytest.mark.django_db
def test_list_page_shows_flow_selection_controls(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    # TC-SFV-X-001: 判定軸セレクタはなく、判定期間セレクタがアクション行の先頭にある
    assert 'id="ioa-flow-axis"' not in html
    assert 'id="ioa-flow-period"' not in html
    assert 'id="ioa-evaluation-period"' in html
    assert 'id="ioa-flow-quadrant"' in html
    actions_pos = html.index('class="ioa-table-actions"')
    period_pos = html.index('id="ioa-evaluation-period"', actions_pos)
    rules_pos = html.index("ioa-alert-rules-open", actions_pos)
    assert actions_pos < period_pos < rules_pos
    # 判定条件・補助説明はセレクトボックス自体で分かるため、別途テキストでは表示しない。
    assert "ioa-flow-condition-label" not in html
    assert "判定期間内に入出荷のない品目（低流動品）を洗い出します" not in html
    assert "ioa-flow-axis-help" not in html
    assert "data-help-text" not in html


@pytest.mark.django_db
def test_list_page_places_flow_quadrant_filter_inside_filter_panel(client, production_user):
    """「判定条件」パネルは撤去し、流動区分フィルタはフィルタパネルに置く（05 design §6.3）。"""
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert 'class="ioa-flow-selector"' not in html
    filter_panel_pos = html.index('class="ioa-filter-panel"')
    quadrant_pos = html.index('id="ioa-flow-quadrant"')
    table_pos = html.index('class="ioa-table-wrap"')
    assert filter_panel_pos < quadrant_pos < table_pos


@pytest.mark.django_db
def test_list_page_flow_selects_reuse_filter_panel_appearance(client, production_user):
    """判定条件のセレクトは既存フィルタと同じ見た目のクラスを使う。"""
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    for select_id in ("ioa-evaluation-period", "ioa-flow-quadrant"):
        marker = f'id="{select_id}"'
        opening_tag = html[html.index(marker) : html.index(">", html.index(marker))]
        # 枠線・高さ・幅は ioa-filter-select、幅の伸縮は ioa-filter-control が担う。
        assert "ioa-filter-select" in opening_tag
        assert "ioa-filter-control" in opening_tag

    # フィルタパネル内のラベルは既存フィルタと同じ span を使う。
    assert '<span class="ioa-filter-field-label">流動区分</span>' in html
    assert '<span class="ioa-evaluation-period-label">判定期間</span>' in html


def test_app_css_has_flow_cell_and_period_selector_styles_without_flow_selector():
    css = (Path(__file__).resolve().parents[3] / "static" / "css" / "app.css").read_text(encoding="utf-8")

    # 「判定条件」パネルのスタイルは撤去済み（05 design §6.3）。
    assert "ioa-flow-selector" not in css
    # 区分名と判定期間セレクタのスタイルがある。セルを積み上げる旧スタイル・バッジは撤去済み（2026/09/17 改訂）。
    assert ".inventory-order-alert-page .ioa-flow-quadrant {" in css
    assert ".inventory-order-alert-page .ioa-evaluation-period-select {" in css
    for removed in ("ioa-no-incoming-badge", "ioa-flow-cell-head", "ioa-flow-status", "ioa-flow-urgency", "min-width: 22em"):
        assert removed not in css
    # 行の背景色クラスは新キーに追随し、旧キーは残っていない。
    # 行の色は在庫切れリスクのみ。流動区分の色（セルの色見本・判定ルールの行色）は使わない（2026/09/18 改訂）
    assert ".alert-row--stockout-danger" in css
    assert ".alert-row--stockout-caution" in css
    assert "ioa-flow-swatch" not in css
    assert "ioa-alert-rules-row--" not in css
    assert "supply-risk" not in css
    assert "excess-stock-risk" not in css


@pytest.mark.django_db
def test_api_save_alert_settings_is_removed(client, production_user):
    client.force_login(production_user)

    response = client.put(
        "/api/inventory-order-alert/alert-settings",
        data='{"warningShipmentMonths":18}',
        content_type="application/json",
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_shipment_trend_alert_settings_api_still_exists(client, production_user):
    # 同名 API を持つ別コンテキストを巻き込んでいないこと（design.md §9 R-8）。
    client.force_login(production_user)

    response = client.put(
        "/api/shipment-trend/alert-settings",
        data="{}",
        content_type="application/json",
    )

    assert response.status_code != 404


@pytest.mark.django_db
def test_list_page_places_slims_import_before_csv_export(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    actions_pos = html.index('class="ioa-table-actions"')
    slims_pos = html.index("SLIMS在庫CSV", actions_pos)
    csv_pos = html.index(">CSV 出力<", actions_pos)
    assert slims_pos < csv_pos
    assert "CSV 出力（全件）" not in html


def test_inventory_order_alert_page_uses_viewport_fitted_table_layout():
    css_path = Path(__file__).resolve().parents[3] / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")
    assert "body.portal-app-page .portal-main" in css
    assert "body.portal-app-page .layout" in css
    assert "body.portal-app-page.inventory-order-alert-page .content > .ioa-table-card" in css
    assert ".inventory-order-alert-page .ioa-table-card" in css
    assert "body.inventory-order-alert-page .ioa-alert-rules-dialog" in css
    assert ".inventory-order-alert-page .ioa-table th {\n  position: sticky;" in css
    assert "text-align: center;" in css.split(".inventory-order-alert-page .ioa-table th {")[1].split("}")[0]
    counts_rule = css.split(".inventory-order-alert-page .ioa-table-counts {")[1].split("}")[0]
    assert "font-size: var(--portal-font-size-caption)" in counts_rule
    assert "max-height: min(62vh, 720px)" not in css


@pytest.mark.django_db
def test_list_page_shows_stock_label_in_table_head(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    head_pos = html.index('class="portal-section-head ioa-table-head"')
    page_title_end = html.index("</div>", html.index("<h1>在庫発注アラート</h1>"))
    assert STOCK_SUMMARY_HEADING_SUFFIX not in html[:page_title_end]
    assert STOCK_SUMMARY_HEADING_SUFFIX in html[head_pos : head_pos + 500]
    assert "※入出荷の実績があるもののみ表示されます。" in html
    assert 'class="ioa-list-scope-note"' in html
    assert "一覧（" not in html


@pytest.mark.django_db
def test_list_page_hides_import_meta_line(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=42)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 18))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert "最終取込:" not in html
    assert "BOM 基準日:" not in html
    assert "在庫行:" not in html
    assert "sample.csv" not in html
    assert "監視 1 件" in html  # 06: 件数サマリは在庫切れリスク。旧行は監視


@pytest.mark.django_db
def test_list_page_shows_same_summary_for_all_users(client, db):
    import_record = SlimsStockImport.objects.create(file_name="shared.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    admin_group, _ = Group.objects.get_or_create(name="管理者")
    user_a = get_user_model().objects.create_user(username="10010", last_name="A", first_name="担当")
    user_b = get_user_model().objects.create_user(username="10011", last_name="B", first_name="担当")
    for user in (user_a, user_b):
        user.groups.add(admin_group)
        PortalMenuGroupAccess.objects.get_or_create(user=user, group_key="production")

    client.force_login(user_a)
    html_a = client.get("/app/production/inventory-order-alert").content.decode("utf-8")
    client.force_login(user_b)
    html_b = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert "90249-10112" in html_a
    assert "90249-10112" in html_b
    assert STOCK_SUMMARY_HEADING_SUFFIX in html_a
    assert "時点の在庫 時点の集計結果" not in html_a
    assert "一覧（1 件）" not in html_a


@pytest.mark.django_db
def test_list_page_shows_inline_confirmation_select(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert 'class="ioa-confirmation-status"' in html
    assert 'data-row-key="112|90249-10112"' in html
    assert 'data-cust-code="112"' in html
    assert 'data-item-cd="90249-10112"' in html
    assert '<option value="confirmed"' in html
    assert 'data-confirmation-status="unconfirmed"' in html
    assert "ioa-confirm-dialog" not in html


@pytest.mark.django_db
def test_list_page_alert_counts_include_confirmed_rows(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=2)
    rows = [
        _sample_export_row() | {"item_cd": "ITEM-A"},
        _dormant_stock_row(item_cd="ITEM-B"),
    ]
    store_summary_snapshot(import_record, rows, as_of_date=date(2026, 6, 17))
    from application.inventory_order_alert.models import ConfirmationStatus, InventoryOrderAlertConfirmation

    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.CONFIRMED,
        confirmed_by="10002",
    )

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert 'alert-row--確認済' in html
    assert "監視 2 件" in html  # 06: 在庫切れリスク（旧行は監視）
    assert "対象外 0 件" in html
    assert "確認済み 1 件" in html
    assert "未確認 1 件" in html


@pytest.mark.django_db
def test_list_page_in_progress_row_shows_blue_background(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))
    from application.inventory_order_alert.models import ConfirmationStatus, InventoryOrderAlertConfirmation

    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="90249-10112",
        status=ConfirmationStatus.IN_PROGRESS,
        confirmed_by="10002",
    )

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert 'alert-row--確認中' in html
    assert "監視 1 件" in html
    assert ">確認中<" in html or "確認中</option>" in html


@pytest.mark.django_db
def test_list_page_shows_test_data_warning_for_sample_import(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=21)
    rows = [_sample_export_row() | {"item_cd": f"ITEM-{index:02d}"} for index in range(21)]
    store_summary_snapshot(import_record, rows, as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8-sig")

    assert "単体テスト用のサンプルデータ" in html


@pytest.mark.django_db
def test_list_page_shows_paginated_summary_rows(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=21)
    rows = [_sample_export_row() | {"item_cd": f"ITEM-{index:02d}"} for index in range(21)]
    store_summary_snapshot(import_record, rows, as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    response = client.get("/app/production/inventory-order-alert?page_size=20&page=2&sort=item_cd&dir=asc")

    html = response.content.decode("utf-8-sig")
    assert response.status_code == 200
    assert "ITEM-20" in html
    assert "表示件数" in html
    assert "件目を表示（2 / 2 ページ）" in html
    assert 'class="muted ioa-table-range"' in html
    assert 'class="ioa-table-counts-left"' in html
    assert 'class="ioa-table-counts-right"' in html
    # 確認状態リセットは設定画面（SCR-02）へ移した。一覧には出さない。
    assert "ioa-confirmation-reset" not in html
    assert "危険 0 件 / 注意 0 件 / 監視 21 件 / 対象外 0 件" in html
    assert "全件数:" not in html
    assert "確認済み 0 件 / 確認中 0 件 / 未確認 21 件" in html
    assert "CSV 取込時に Oracle から全件集計し" not in html
    assert 'class="ioa-table-toolbar"' in html
    sort_open_pos = html.index('class="button-link ioa-sort-open"')
    sort_button_end = html.index("</button>", sort_open_pos)
    assert "（" not in html[sort_open_pos:sort_button_end]
    assert 'class="ioa-table-footer"' in html
    assert 'id="ioa-sort-dialog"' in html
    select_pos = html.index('id="ioa-page-size"')
    table_wrap_pos = html.index('class="ioa-table-wrap"')
    footer_pos = html.index('class="ioa-table-footer"')
    assert table_wrap_pos < footer_pos
    # 件数サマリは表の表示領域を優先し、フッタ行（表の下）に置く。
    assert html.index("監視 21 件") > footer_pos
    assert html.index("表示件数", footer_pos) < select_pos
    assert select_pos < html.index("前へ", footer_pos)
    assert html.index("前へ", footer_pos) < html.index("次へ", footer_pos)
    assert html.index("次へ", footer_pos) < html.index("件目を表示（2 / 2 ページ）", footer_pos)
    next_button_pos = html.index("ioa-pagination-next", footer_pos)
    assert "disabled" in html[next_button_pos : next_button_pos + 120]


@pytest.mark.django_db
def test_list_page_layout_places_filters_in_toolbar_and_counts_in_footer(client, production_user):
    """表の表示領域を優先し、フィルタは並び替えと同じ行、件数サマリは表の下へ置く。"""
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    response = client.get("/app/production/inventory-order-alert")

    html = response.content.decode("utf-8")
    toolbar_start = html.index('class="ioa-table-toolbar"')
    filter_panel_pos = html.index('class="ioa-filter-panel"', toolbar_start)
    table_wrap_pos = html.index('class="ioa-table-wrap"', toolbar_start)
    footer_row_pos = html.index('class="ioa-table-footer-row"', toolbar_start)
    counts_pos = html.index('class="ioa-table-counts"', footer_row_pos)
    assert toolbar_start < filter_panel_pos < table_wrap_pos < footer_row_pos < counts_pos


@pytest.mark.django_db
def test_list_page_shows_alert_counts_on_left(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=2)
    rows = [
        _sample_export_row() | {"cust_code": "112", "cust_chrg_psn_cd": "A01"},
        _sample_export_row() | {"cust_code": "201", "cust_name": "別得意先", "cust_chrg_psn_cd": "B02", "item_cd": "ITEM-2"},
    ]
    store_summary_snapshot(import_record, rows, as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert?cust_code=112").content.decode("utf-8")

    counts_pos = html.index('class="ioa-table-counts"')
    left_pos = html.index('class="ioa-table-counts-left"', counts_pos)
    right_pos = html.index('class="ioa-table-counts-right"', counts_pos)
    critical_pos = html.index("監視 1 件", left_pos)
    unconfirmed_pos = html.index("未確認", right_pos)
    assert left_pos < right_pos
    assert critical_pos < unconfirmed_pos
    assert "全件数:" not in html


@pytest.mark.django_db
def test_list_page_supports_multi_sort_query(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=3)
    rows = [
        _sample_export_row() | {"item_cd": "ITEM-A", "last_incoming_date": "2026/06/01"},
        _sample_export_row() | {"item_cd": "ITEM-B", "last_incoming_date": "2026/06/01"},
        _sample_export_row() | {"item_cd": "ITEM-C", "last_incoming_date": "2026/01/01"},
    ]
    store_summary_snapshot(import_record, rows, as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    response = client.get(
        "/app/production/inventory-order-alert"
        "?sort=last_incoming_date,item_cd&dir=asc,asc&page_size=50"
    )
    html = response.content.decode("utf-8")
    body = response.content.decode("utf-8")
    tbody_start = body.index("<tbody>")
    tbody_end = body.index("</tbody>", tbody_start)
    tbody = body[tbody_start:tbody_end]
    assert tbody.index("ITEM-C") < tbody.index("ITEM-A") < tbody.index("ITEM-B")
    assert "ioa-sort-open" in html
    assert 'id="ioa-list-data"' in html
    assert "番号をドラッグして順序を変更" in html


@pytest.mark.django_db
def test_list_page_shows_filter_panel_with_snapshot_options(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=2)
    rows = [
        _sample_export_row() | {"cust_code": "112", "cust_chrg_psn_cd": "A01"},
        _sample_export_row() | {"cust_code": "201", "cust_name": "別得意先", "cust_chrg_psn_cd": "B02", "item_cd": "ITEM-2"},
    ]
    store_summary_snapshot(import_record, rows, as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    response = client.get("/app/production/inventory-order-alert?cust_code=112&cust_chrg_psn_cd=A01")
    html = response.content.decode("utf-8")

    assert response.status_code == 200
    assert 'class="ioa-filter-panel"' in html
    assert "ioa-filter-panel-title" not in html
    assert "担当者コード" in html
    assert ">担当者コード<" in html or "担当者コード</a>" in html or "担当者コード ▲" in html or "担当者コード ▼" in html
    assert "得意先コード" in html
    assert '<option value="A01"' in html
    assert '<option value="B02"' in html
    assert '<option value="112"' in html
    assert "112 - テスト得意先" in html
    assert STOCK_SUMMARY_HEADING_SUFFIX in html
    assert "一覧（1 件 / 全 2 件）" not in html
    assert "90249-10112" in html
    tbody_start = html.index("<tbody>")
    tbody_end = html.index("</tbody>", tbody_start)
    tbody = html[tbody_start:tbody_end]
    assert "ITEM-2" not in tbody


@pytest.mark.django_db
def test_list_page_includes_row_selection_markup(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert 'class="alert-row alert-row--stockout-watch ioa-data-row"' in html
    assert 'data-flow-quadrant="low-flow-no-incoming"' in html
    assert 'data-cust-code="112"' in html
    assert 'data-item-cd="90249-10112"' in html
    assert 'data-stock-location-detail=' in html
    assert 'id="ioa-location-dialog"' in html
    assert 'class="ioa-location-dialog"' in html
    assert ">詳細<" in html
    assert 'class="ioa-detail-memo-table"' in html
    assert "登録日時" in html
    assert "登録者" in html
    assert 'id="ioa-detail-memo"' in html
    assert "ioa-detail-memo-hint" not in html
    assert "追記すると確認状態は変わりません" not in html
    assert "ioa-detail-save" in html
    assert "在庫内訳(SLIMS)" in html
    assert "ロケーション内訳" not in html
    assert 'class="ioa-location-col-incoming"' in html
    assert 'class="ioa-location-col-location"' in html
    assert 'class="ioa-location-col-qty"' in html
    assert 'class="ioa-confirmation-status"' in html


@pytest.mark.django_db
def test_list_page_labels_stock_columns_by_source(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(
        import_record, [_sample_export_row() | {"mari_stock_qty": 95}], as_of_date=date(2026, 6, 17)
    )

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert "在庫数(SLIMS)" in html
    assert "在庫数(MARI)" in html


@pytest.mark.django_db
def test_list_page_has_no_responsible_department_column(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    # 責任部署は一覧列から外し詳細ダイアログへ移した（REQ-MSV-F-005）。
    assert '"key": "responsible_department"' not in html


@pytest.mark.django_db
def test_list_page_keeps_zero_mari_stock_distinct_from_blank(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(
        import_record, [_sample_export_row() | {"mari_stock_qty": 0}], as_of_date=date(2026, 6, 17)
    )

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    # 0 は「在庫なし」であって「該当なし」ではない（design.md §9 R-2）。
    assert '"mari_stock_qty": "0"' in html


@pytest.mark.django_db
def test_list_page_server_rendered_row_carries_detail_data_attributes(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(
        import_record, [_sample_export_row() | {"mari_stock_qty": 95}], as_of_date=date(2026, 6, 17)
    )

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    # JS の行描画と対で維持する（JS 初期化前・失敗時も詳細ダイアログを埋められるように）。
    assert 'data-mari-stock-qty="95"' in html
    assert 'data-level1-vend-cd="9209"' in html
    assert 'data-level1-item-cd="90249-10112-9209"' in html
    assert "data-flow-quadrant=" in html
    assert "data-no-incoming-record=" in html
    assert "data-last-ship-date=" in html


@pytest.mark.django_db
def test_list_page_server_rendered_row_marks_not_fetched_mari_stock(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    # 既存スナップショットは未取得。サーバ描画でも JS 描画と同じ「－」を出す。
    assert 'data-mari-stock-qty="－"' in html


@pytest.mark.django_db
def test_list_page_detail_dialog_has_four_sections(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    # design.md §6.3 の 4 区分。
    assert "ioa-detail-item-section" in html
    assert "ioa-detail-flow-section" in html
    assert "ioa-detail-stock-section" in html
    assert "ioa-detail-memo-section" in html
    assert "ioa-detail-department" in html
    assert "ioa-detail-condition" not in html
    # TC-SFV-X-011: 流動区分区分に 状況 / 推奨アクション / 判定期間
    assert "ioa-detail-flow-status" in html
    assert "ioa-detail-recommended-action" in html
    assert "ioa-detail-evaluation-period" in html
    assert "ioa-detail-stock-slims" in html
    assert "ioa-detail-stock-mari" in html
    # 圧縮された 1 行のメタ表示は 4 区分に置き換えた。
    assert "ioa-location-meta" not in html
    assert "/static/js/inventory-order-alert-list.js" in html


@pytest.mark.django_db
def test_shipment_trend_dedicated_section_was_removed(client, production_user):
    """入出荷推移の独立グラフ区分は削除した（推定在庫推移に統合。DECISIONS.md参照）。"""
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert "ioa-detail-shipment-trend-section" not in html


@pytest.mark.django_db
def test_TC_SHC_X_015_anchored_stock_trend_section_is_between_stock_and_memo(client, production_user):
    """推定在庫推移区分が「在庫」と「メモ」の間にある（design.md §6.5）。"""
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    stock_pos = html.index("ioa-detail-stock-section")
    trend_pos = html.index("ioa-detail-anchored-stock-trend-section")
    memo_pos = html.index("ioa-detail-memo-section")
    assert stock_pos < trend_pos < memo_pos


@pytest.mark.django_db
def test_TC_SHC_X_027_gonen_link_is_below_the_anchored_stock_trend_chart(client, production_user):
    """5年9組への遷移ボタンは推定在庫推移グラフの直下、メモ区分より前にある（design.md §6.7）。"""
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    chart_pos = html.index("ioa-detail-anchored-stock-trend-chart")
    empty_pos = html.index("ioa-detail-anchored-stock-trend-empty")
    link_pos = html.index("ioa-detail-gonen-link")
    memo_pos = html.index("ioa-detail-memo-section")
    assert chart_pos < empty_pos < link_pos < memo_pos


@pytest.mark.django_db
def test_TC_SHC_X_028_gonen_link_opens_in_a_new_tab(client, production_user):
    """別タブで開く（詳細ダイアログの操作を中断させないため）。"""
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    link_tag = html[html.index('<a class="button-link ioa-detail-gonen-link"') :][:400]
    assert 'target="_blank"' in link_tag
    assert 'rel="noopener"' in link_tag
    assert "5年9組で開く" in link_tag


@pytest.mark.django_db
def test_list_page_without_data_still_loads_page_script_for_file_picker(client, production_user):
    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert "inventory-order-alert-list.js" in html
    assert "ioa-data-row" not in html


@pytest.mark.django_db
def test_export_csv_returns_utf8_bom_attachment(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    response = client.get("/app/production/inventory-order-alert/export.csv")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert "attachment" in response["Content-Disposition"]
    assert response.content.startswith(b"\xef\xbb\xbf")
    body = response.content.decode("utf-8-sig")
    assert "得意先コード" in body
    assert "90249-10112" in body


@pytest.mark.django_db
def test_export_csv_404_without_summary(client, production_user):
    client.force_login(production_user)
    response = client.get("/app/production/inventory-order-alert/export.csv")
    assert response.status_code == 404


@pytest.mark.django_db
def test_api_export_csv_uses_same_handler(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    response = client.get("/api/inventory-order-alert/export.csv")

    assert response.status_code == 200
    assert response.content.startswith(b"\xef\xbb\xbf")


@pytest.mark.django_db
def test_export_csv_forbidden_without_production_access(client, db):
    user = get_user_model().objects.create_user(username="10003", last_name="一般", first_name="ユーザー")
    client.force_login(user)
    response = client.get("/app/production/inventory-order-alert/export.csv")
    assert response.status_code == 403


@pytest.mark.django_db
@patch("application.inventory_order_alert.interfaces.wiring.portal_dashboard_usecase")
def test_dashboard_shows_inventory_order_alert_banner(mock_usecase_factory, client, production_user):
    from application.inventory_order_alert.use_cases.portal_dashboard import DashboardBannerContext

    mock_usecase_factory.return_value.execute.return_value = DashboardBannerContext(
        stockout_no_incoming=2,
        stockout=3,
        low_flow_no_incoming=1,
        dormant_stock=1,
        low_flow_no_shipment=1,
        unconfirmed=1,
        stock_as_of_label="2026年6月17日時点の在庫",
        has_stock_data=True,
        stock_stale=False,
    )
    client.force_login(production_user)
    response = client.get("/app")
    html = response.content.decode("utf-8")
    assert "在庫発注アラート" in html
    assert "inventory-order-alert-banner" in html
    # TC-FQR-C-002: 帯は 欠品（入荷なし）/ 欠品 / 低流動品（入荷なし）/ 在庫死蔵品 の 4 件数
    assert "欠品（入荷なし） 2 件" in html
    assert "欠品 3 件" in html
    # TC-SFV-X-012: 新区分名・判定期間 1 年。旧称・3か月・判定軸は出ない
    assert "低流動品（入荷なし）" in html
    assert "在庫死蔵品" in html
    assert "判定期間 1年" in html
    assert "供給リスク品" not in html
    assert "在庫過剰リスク品" not in html
    assert "3か月" not in html
    assert "判定軸" not in html


# --- 05_single-flow-view: TC-SFV-X-002〜X-010 ---


def _low_flow_no_shipment_row(**overrides: object) -> dict[str, object]:
    """判定期間 1 年で低流動品（出荷なし）になる行。"""
    return _sample_export_row() | {
        "last_incoming_date": "2026/05/01",
        "last_ship_date": "2024/01/01",
        **overrides,
    }


def _normal_flow_row(**overrides: object) -> dict[str, object]:
    return _sample_export_row() | {
        "last_incoming_date": "2026/05/01",
        "last_ship_date": "2026/06/15",
        **overrides,
    }


def _store_four_quadrants() -> None:
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=4)
    rows = [
        _sample_export_row() | {"item_cd": "ITEM-NO-INCOMING"},
        _dormant_stock_row(item_cd="ITEM-DORMANT"),
        _low_flow_no_shipment_row(item_cd="ITEM-NO-SHIPMENT"),
        _normal_flow_row(item_cd="ITEM-NORMAL"),
    ]
    store_summary_snapshot(import_record, rows, as_of_date=date(2026, 6, 17))


@pytest.mark.django_db
def test_x002_evaluation_period_options_are_one_three_five_years(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    start = html.index('id="ioa-evaluation-period"')
    end = html.index("</select>", start)
    select_html = html[start:end]
    assert select_html.count("<option") == 3
    assert '<option value="1" data-period-key="Y1" selected>1年</option>' in select_html
    assert '<option value="3" data-period-key="Y3" >3年</option>' in select_html
    assert '<option value="5" data-period-key="Y5" >5年</option>' in select_html


@pytest.mark.django_db
def test_x003_page_has_no_legacy_names_or_axis(client, production_user):
    _store_four_quadrants()

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    for legacy in ("供給リスク品", "在庫過剰リスク品", "判定軸", "低流動判定軸", "死蔵判定軸", "supply-risk", "excess-stock-risk"):
        assert legacy not in html


@pytest.mark.django_db
def test_x004_flow_cell_shows_quadrant_name_only(client, production_user):
    """セルは区分名のみ。説明（状況・対処方法）は詳細ダイアログ（2026/09/17 改訂）。"""
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(
        import_record,
        [_sample_export_row() | {"last_incoming_date": "2025/04/02", "last_ship_date": "2026/06/15"}],
        as_of_date=date(2026, 6, 17),
    )

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    cell_start = html.index('<td class="ioa-flow-cell">')
    cell = html[cell_start : html.index("</td>", cell_start)]
    # 流動区分は文字のみ（行の色は使わない。2026/09/18）。区分キーのクラスは欠品 3 区分のバッジ色に使う（07 design §5.1）
    assert cell == (
        '<td class="ioa-flow-cell">'
        '<span class="ioa-flow-quadrant ioa-flow-quadrant--low-flow-no-incoming">低流動品（入荷なし）</span>'
    )
    for removed in ("ioa-flow-status", "ioa-flow-action", "ioa-flow-departments", "ioa-flow-urgency", "ioa-flow-cell-head"):
        assert removed not in html
    # 詳細ダイアログ用の属性は残す
    assert 'data-flow-status="出荷は継続、最終入荷 2025/04/02（1年以上入荷なし）"' in html
    assert 'data-recommended-action="仕入先へ' in html
    assert 'data-responsible-department="調達G・営業G・生産管理"' in html


@pytest.mark.django_db
def test_x005_normal_flow_cell_is_empty(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_normal_flow_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    cell_start = html.index('<td class="ioa-flow-cell">')
    cell = html[cell_start : html.index("</td>", cell_start)]
    assert "ioa-flow-quadrant" not in cell
    assert "ioa-flow-action" not in cell
    assert "通常流動品" not in cell
    assert 'ioa-flow-swatch' not in cell


@pytest.mark.django_db
def test_x006_no_incoming_record_has_no_badge(client, production_user):
    """入荷実績なしバッジは出さない（最終入荷日が空欄で分かる。2026/09/17 改訂）。"""
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert "ioa-no-incoming-badge" not in html
    cell_start = html.index('<td class="ioa-flow-cell">')
    cell = html[cell_start : html.index("</td>", cell_start)]
    assert "入荷実績なし" not in cell
    # 状況（詳細ダイアログ用）には「入荷実績なし」が入る
    assert 'data-no-incoming-record="1"' in html
    assert "最終入荷 入荷実績なし" in html


@pytest.mark.django_db
def test_x007_legacy_axis_and_month_period_url_does_not_fail(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(
        import_record,
        [_sample_export_row() | {"last_incoming_date": "2025/04/02", "last_ship_date": "2026/06/15"}],
        as_of_date=date(2026, 6, 17),
    )

    client.force_login(production_user)
    response = client.get("/app/production/inventory-order-alert?axis=low_flow&period=3")
    html = response.content.decode("utf-8")

    assert response.status_code == 200
    # period=3 は 3 年として解釈され、最終入荷 2025/04/02 は期間内 → 通常流動品
    assert '<option value="3" data-period-key="Y3" selected>3年</option>' in html
    assert 'data-flow-quadrant="normal-flow"' in html

    response = client.get("/app/production/inventory-order-alert?axis=dormant&period=6")
    html = response.content.decode("utf-8")

    assert response.status_code == 200
    # 旧値 6 は既定 1 年へ
    assert '<option value="1" data-period-key="Y1" selected>1年</option>' in html
    assert 'data-flow-quadrant="low-flow-no-incoming"' in html


@pytest.mark.django_db
def test_x008_legacy_flow_quadrant_key_filters_by_new_quadrant(client, production_user):
    _store_four_quadrants()

    client.force_login(production_user)
    response = client.get("/app/production/inventory-order-alert?flow_quadrant=supply-risk")
    html = response.content.decode("utf-8")

    assert response.status_code == 200
    assert '<option value="low-flow-no-incoming" selected>低流動品（入荷なし）</option>' in html
    assert "supply-risk" not in html


@pytest.mark.django_db
def test_x009_counts_summary_uses_new_quadrant_names(client, production_user):
    _store_four_quadrants()

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    # 06: 件数サマリは在庫切れリスク。流動区分は行の data 属性で確認する
    assert "危険 0 件 / 注意 0 件 / 監視 4 件 / 対象外 0 件" in html
    for key in ("low-flow-no-incoming", "dormant-stock", "low-flow-no-shipment", "normal-flow"):
        assert f'data-flow-quadrant="{key}"' in html


@pytest.mark.django_db
def test_x010_rules_dialog_has_status_action_department_columns(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    start = html.index('id="ioa-alert-rules-dialog"')
    dialog = html[start : html.index("</dialog>", start)]
    for header in ("期間内入荷", "期間内出荷", "流動区分", "状況", "推奨アクション", "責任部署"):
        assert f"<th scope=\"col\">{header}</th>" in dialog
    assert "判定軸" not in dialog
    assert 'class="ioa-alert-rules-period"' in dialog
    assert "現在の判定期間" in dialog
    assert "処分・廃却の検討" in dialog
    assert "発注を抑制" in dialog


# --- 05_single-flow-view 第 2 段階: TC-SFV-X-013〜X-016 ---


def _forecast_row(**overrides: object) -> dict[str, object]:
    """需要予測つきの行（内示ベース）。取込時に attach_demand_forecast が付ける項目を直接持たせる。"""
    return _sample_export_row() | {
        "last_incoming_date": "2025/04/02",
        "last_ship_date": "2026/06/15",
        "internal_item_cd": "90249-10112-9209",
        "unconfirmed_order_trend": [
            {"month": "2026-06", "qty": 0},
            {"month": "2026-07", "qty": 224},
            {"month": "2026-08", "qty": 216},
            {"month": "2026-09", "qty": 197},
        ],
        "reconciliation_unit_key": "90249-10112",
        "demand_forecast_basis": "内示",
        "demand_forecast_current_month_remaining": 0,
        "demand_forecast_monthly": [224, 216, 197],
        "demand_forecast_monthly_average": 212.3333,
        "demand_forecast_stock_total": 100.0,
        "months_of_stock": 0.5,
        "stockout_forecast_month": "2026-07",
        **overrides,
    }


@pytest.mark.django_db
def test_x013_export_csv_has_stage2_trailing_columns_and_values(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_forecast_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    response = client.get("/app/production/inventory-order-alert/export.csv?period=1")
    body = response.content.decode("utf-8-sig")
    header, data = body.strip().splitlines()[:2]

    assert response.status_code == 200
    columns = header.split(",")
    assert columns[24:28] == ["在庫月数", "在庫切れ予測月", "需要予測の算出根拠", "推奨アクション"]
    assert columns[-1] == "上流工程の納期超過"
    assert columns.index("流動区分") < columns.index("判定軸") < columns.index("判定期間")
    import csv
    import io

    record = next(csv.DictReader(io.StringIO(body)))
    assert record["流動区分"] == "低流動品（入荷なし）"
    assert record["判定軸"] == ""
    assert record["判定期間"] == "1年"
    assert record["在庫月数"] == "0.5"
    assert record["在庫切れ予測月"] == "2026-07"
    assert record["需要予測の算出根拠"] == "内示"
    assert record["推奨アクション"].startswith("仕入先へ")
    assert "供給リスク品" not in body


@pytest.mark.django_db
def test_x014_legacy_snapshot_without_unconfirmed_orders_renders(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    response = client.get("/app/production/inventory-order-alert")
    html = response.content.decode("utf-8")

    assert response.status_code == 200
    cell_start = html.index('<td class="ioa-flow-cell">')
    cell = html[cell_start : html.index("</td>", cell_start)]
    assert "ioa-flow-urgency" not in cell
    assert 'data-demand-forecast-basis=""' in html
    # 旧スナップショットでもペイロードの需要予測は「なし」で配信される
    import json

    start = html.index('<script id="ioa-list-data" type="application/json">') + len('<script id="ioa-list-data" type="application/json">')
    payload = json.loads(html[start : html.index("</script>", start)])
    assert payload["rows"][0]["demandForecast"]["basis"] == "なし"
    assert payload["rows"][0]["demandForecast"]["monthsOfStock"] is None
    assert {"key": "months_of_stock", "label": "在庫月数"} in payload["sortOnlyColumns"]


@pytest.mark.django_db
def test_x015_urgency_is_only_in_row_data_and_detail_dialog(client, production_user):
    """緊急度は一覧セルに出さず、行の data-* と詳細ダイアログで示す（2026/09/17 改訂）。"""
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_forecast_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert "ioa-flow-urgency" not in html
    assert 'data-months-of-stock="0.5"' in html
    assert 'data-stockout-forecast-month="2026-07"' in html
    assert 'data-demand-forecast-basis="内示"' in html
    assert "ioa-detail-months-of-stock" in html
    assert "ioa-detail-stockout-month" in html


@pytest.mark.django_db
def test_x015_row_data_carries_empty_stockout_month_when_stock_is_enough(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(
        import_record,
        [_forecast_row(months_of_stock=150.6, stockout_forecast_month=None)],
        as_of_date=date(2026, 6, 17),
    )

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert 'data-months-of-stock="150.6"' in html
    assert 'data-stockout-forecast-month=""' in html


@pytest.mark.django_db
def test_x016_detail_dialog_has_demand_forecast_section_between_trend_and_memo(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    trend_pos = html.index("ioa-detail-anchored-stock-trend-section")
    forecast_pos = html.index("ioa-detail-demand-forecast-section")
    memo_pos = html.index("ioa-detail-memo-section")
    assert trend_pos < forecast_pos < memo_pos
    for class_name in (
        "ioa-detail-demand-basis",
        "ioa-detail-demand-monthly",
        "ioa-detail-months-of-stock",
        "ioa-detail-stockout-month",
        "ioa-detail-demand-unit-breakdown",
        "ioa-detail-demand-empty",
    ):
        assert class_name in html


@pytest.mark.django_db
def test_stage2_list_page_accepts_months_of_stock_sort(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=2)
    rows = [
        _forecast_row(item_cd="ITEM-LATE", months_of_stock=9.0),
        _forecast_row(item_cd="ITEM-SOON", months_of_stock=0.5),
    ]
    store_summary_snapshot(import_record, rows, as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    response = client.get("/app/production/inventory-order-alert?sort=months_of_stock&dir=asc")
    html = response.content.decode("utf-8")

    assert response.status_code == 200
    assert html.index('data-item-cd="ITEM-SOON"') < html.index('data-item-cd="ITEM-LATE"')


# --- 06_stockout-risk: TC-SOR-X-001〜008 ---


def _risk_row(risk: str, *, item_cd: str, reasons: list[str] | None = None, days: int | None = 0, quadrant_dates=("2025/04/02", "2026/06/15"), **extra) -> dict[str, object]:
    last_incoming, last_ship = quadrant_dates
    return _forecast_row(item_cd=item_cd, last_incoming_date=last_incoming, last_ship_date=last_ship) | {
        "stockout_risk": risk,
        "stockout_risk_key": {"危険": "danger", "注意": "caution", "監視": "watch", "対象外": "none"}[risk],
        "stockout_risk_reasons": reasons or [],
        "days_until_stockout": days,
        "shortage_qty": 200,
        "replenishment_qty": 0,
        "replenishment_later_qty": 0,
        "replenishment_earliest_due": "",
        "replenishment_has_overdue": False,
        "replenishment_unknown": False,
        "lead_time_days": 5,
        "lead_time_source": "master",
        "ordering_method": "手動発注",
        **extra,
    }


def _store_risk_rows() -> None:
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=4)
    rows = [
        _risk_row("危険", item_cd="ITEM-DANGER", reasons=["発注忘れの可能性", "リードタイム内"], days=0),
        _risk_row("注意", item_cd="ITEM-CAUTION", reasons=["数量不足"], days=40, ordering_method="MRP 発注"),
        _risk_row("監視", item_cd="ITEM-WATCH", days=None),
        _risk_row("対象外", item_cd="ITEM-NONE", days=30, quadrant_dates=("2026/05/01", "2026/06/15")),
    ]
    store_summary_snapshot(import_record, rows, as_of_date=date(2026, 6, 17))


@pytest.mark.django_db
def test_sor_x001_stockout_risk_column_is_first_and_cell_shows_label_only(client, production_user):
    _store_risk_rows()

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    header_pos = html.index("在庫切れリスク")
    assert header_pos < html.index("流動区分")
    assert '<span class="ioa-stockout-risk ioa-stockout-risk--danger">危険</span>' in html
    assert '<span class="ioa-stockout-risk ioa-stockout-risk--caution">注意</span>' in html
    assert '<span class="ioa-stockout-risk ioa-stockout-risk--watch">監視</span>' in html
    assert "ioa-stockout-risk--none" not in html  # 対象外は空
    assert 'data-stockout-risk="danger"' in html


@pytest.mark.django_db
def test_sor_x002_row_class_prefers_stockout_risk_over_flow_quadrant(client, production_user):
    _store_risk_rows()

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert 'class="alert-row alert-row--stockout-danger ioa-data-row"' in html
    assert 'class="alert-row alert-row--stockout-caution ioa-data-row"' in html
    # 監視・対象外は色なし（流動区分は行の色に使わない）
    assert 'class="alert-row alert-row--stockout-watch ioa-data-row"' in html
    assert 'class="alert-row alert-row--stockout-none ioa-data-row"' in html
    assert 'class="alert-row alert-row--low-flow-no-incoming ioa-data-row"' not in html


@pytest.mark.django_db
def test_sor_x003_counts_summary_is_by_stockout_risk(client, production_user):
    _store_risk_rows()

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert "危険 1 件 / 注意 1 件 / 監視 1 件 / 対象外 1 件" in html


@pytest.mark.django_db
@patch("application.inventory_order_alert.interfaces.wiring.portal_dashboard_usecase")
def test_sor_x004_dashboard_banner_shows_danger_and_caution(mock_usecase_factory, client, production_user):
    from application.inventory_order_alert.use_cases.portal_dashboard import DashboardBannerContext

    mock_usecase_factory.return_value.execute.return_value = DashboardBannerContext(
        low_flow_no_incoming=3,
        dormant_stock=1,
        low_flow_no_shipment=1,
        unconfirmed=4,
        stock_as_of_label="2026年6月17日時点の在庫",
        has_stock_data=True,
        stock_stale=False,
        danger=2,
        caution=5,
        watch=10,
    )
    client.force_login(production_user)
    html = client.get("/app").content.decode("utf-8")

    assert "在庫切れリスク" in html
    assert "危険 <strong>2</strong> 件" in html
    assert "注意 <strong>5</strong> 件" in html
    assert "監視期間 6か月" in html
    assert "判定期間 1年" in html
    assert "inventory-order-alert-banner--critical" in html


@pytest.mark.django_db
def test_sor_x005_detail_dialog_has_stockout_risk_section(client, production_user):
    _store_risk_rows()

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    risk_pos = html.index("ioa-detail-stockout-risk-section")
    forecast_pos = html.index("ioa-detail-demand-forecast-section")
    assert risk_pos < forecast_pos
    for class_name in (
        "ioa-detail-stockout-risk",
        "ioa-detail-stockout-risk-reasons",
        "ioa-detail-stockout-days",
        "ioa-detail-stockout-replenishment",
        "ioa-detail-stockout-shortage",
        "ioa-detail-stockout-lead-time",
        "ioa-detail-stockout-ordering-method",
    ):
        assert class_name in html


@pytest.mark.django_db
def test_sor_x006_filters_by_stockout_risk_and_ordering_method(client, production_user):
    _store_risk_rows()

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert?stockout_risk=danger&ordering_method=manual").content.decode("utf-8")

    assert '<option value="danger" selected>危険</option>' in html
    assert '<option value="manual" selected>手動発注</option>' in html
    assert 'id="ioa-stockout-risk"' in html
    assert 'id="ioa-ordering-method"' in html
    # ソート・ページングのリンクに絞り込みが引き継がれる
    assert "stockout_risk=danger" in html
    assert "ordering_method=manual" in html


@pytest.mark.django_db
def test_sor_x007_csv_appends_stockout_risk_columns(client, production_user):
    _store_risk_rows()

    client.force_login(production_user)
    body = client.get("/app/production/inventory-order-alert/export.csv").content.decode("utf-8-sig")
    import csv
    import io

    records = list(csv.DictReader(io.StringIO(body)))
    header = body.splitlines()[0].split(",")
    assert header[-11:] == ["在庫切れリスク", "在庫切れリスクの理由", "猶予日数", "補充見込み", "補充見込みの最早納期", "納期超過", "不足数量", "リードタイム", "発注方式", "上流工程の発注残", "上流工程の納期超過"]
    danger = next(r for r in records if r["得意先品番"] == "ITEM-DANGER")
    assert danger["在庫切れリスク"] == "危険"
    assert danger["在庫切れリスクの理由"] == "発注忘れの可能性・リードタイム内"
    assert danger["猶予日数"] == "0"
    assert danger["発注方式"] == "手動発注"


@pytest.mark.django_db
def test_sor_x008_legacy_snapshot_is_watch_and_renders(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    response = client.get("/app/production/inventory-order-alert")
    html = response.content.decode("utf-8")

    assert response.status_code == 200
    assert "監視 1 件" in html
    assert 'data-stockout-risk="watch"' in html
    assert "ioa-stockout-risk--watch" not in html  # 旧行（キーなし）はセルを空にする
