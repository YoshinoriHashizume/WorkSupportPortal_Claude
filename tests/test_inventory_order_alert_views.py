from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.inventory_order_alert.infrastructure.persistence.summary_snapshot_repository import store_summary_snapshot
from apps.inventory_order_alert.models import SlimsStockImport
from apps.portal.models import PortalMenuGroupAccess


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
        "alert_level": "重点",
        "confirmation_status": "未確認",
        "confirmed_at": "",
        "confirmed_by": "",
        "confirmation_memo": "",
    }


def _warning_ship_row(**overrides: object) -> dict[str, object]:
    return _sample_export_row() | {
        "last_incoming_date": "2022/01/31",
        "last_ship_date": "2025/11/27",
        "post_shipment_count": 2,
        "alert_level": "警告（出荷あり）",
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
@patch("apps.inventory_order_alert.infrastructure.persistence.slims_stock_repository.run_summary_aggregation")
def test_list_page_post_imports_slims_csv(mock_aggregate, client, production_user):
    mock_aggregate.return_value = ("", 0)
    fixture = Path("tests/fixtures/slims_stock_sample_wkatqt.csv")
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
def test_list_page_shows_alert_rules_button_and_dialog(client, production_user):
    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert "警告条件" in html
    assert 'id="ioa-alert-rules-dialog"' in html
    assert "警告を出す条件" in html
    assert 'class="ioa-alert-rules-table-wrap"' in html
    assert 'id="ioa-warning-shipment-months"' in html
    assert 'id="ioa-warning-incoming-months"' in html
    assert "なし（12か月以上）" in html
    assert "あり（12か月未満）" in html
    assert "設定した月数で判定" in html
    assert "暦月数" not in html


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
    css_path = Path(__file__).resolve().parents[1] / "static" / "css" / "app.css"
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
    assert "重点 1 件" in html


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
    assert '<option value="confirmed"' in html
    assert 'data-confirmation-status="unconfirmed"' in html
    assert "ioa-confirm-dialog" not in html


@pytest.mark.django_db
def test_list_page_alert_counts_include_confirmed_rows(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=2)
    rows = [
        _sample_export_row() | {"item_cd": "ITEM-A"},
        _warning_ship_row(item_cd="ITEM-B"),
    ]
    store_summary_snapshot(import_record, rows, as_of_date=date(2026, 6, 17))
    from apps.inventory_order_alert.models import ConfirmationStatus, InventoryOrderAlertConfirmation

    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.CONFIRMED,
        confirmed_by="10002",
    )

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert 'alert-row--確認済' in html
    assert "重点 1 件" in html
    assert "警告（出荷あり） 1 件" in html
    assert "確認済み 1 件" in html
    assert "未確認 1 件" in html


@pytest.mark.django_db
def test_list_page_in_progress_row_shows_blue_background(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))
    from apps.inventory_order_alert.models import ConfirmationStatus, InventoryOrderAlertConfirmation

    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112",
        item_cd="90249-10112",
        status=ConfirmationStatus.IN_PROGRESS,
        confirmed_by="10002",
    )

    client.force_login(production_user)
    html = client.get("/app/production/inventory-order-alert").content.decode("utf-8")

    assert 'alert-row--確認中' in html
    assert "重点 1 件" in html
    assert ">確認中<" in html or "確認中</option>" in html


@pytest.mark.django_db
def test_api_save_alert_settings(client, production_user):
    client.force_login(production_user)
    response = client.put(
        "/api/inventory-order-alert/alert-settings",
        data='{"warningShipmentMonths":18,"warningIncomingMonths":6}',
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True

    from apps.inventory_order_alert.infrastructure.persistence.settings_repository import load_app_settings

    settings = load_app_settings()
    assert settings.warning_shipment_months == 18
    assert settings.warning_incoming_months == 6


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
    assert 'class="ioa-table-counts-right-wrap"' in html
    assert "リセット" in html
    assert "確認状態リセット" not in html
    assert "ioa-confirmation-reset" in html
    assert "重点 21 件 / 警告（出荷あり） 0 件 / 警告（出荷なし） 0 件 / アラート無し 0 件" in html
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
    assert html.index("重点 21 件") < table_wrap_pos
    assert html.index("表示件数", footer_pos) < select_pos
    assert select_pos < html.index("前へ", footer_pos)
    assert html.index("前へ", footer_pos) < html.index("次へ", footer_pos)
    assert html.index("次へ", footer_pos) < html.index("件目を表示（2 / 2 ページ）", footer_pos)
    next_button_pos = html.index("ioa-pagination-next", footer_pos)
    assert "disabled" in html[next_button_pos : next_button_pos + 120]


@pytest.mark.django_db
def test_list_page_layout_places_counts_in_controls_row(client, production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_export_row()], as_of_date=date(2026, 6, 17))

    client.force_login(production_user)
    response = client.get("/app/production/inventory-order-alert")

    html = response.content.decode("utf-8")
    toolbar_start = html.index('class="ioa-table-toolbar"')
    counts_pos = html.index("ioa-table-counts", toolbar_start)
    table_wrap_pos = html.index('class="ioa-table-wrap"', toolbar_start)
    footer_pos = html.index('class="ioa-table-footer"', toolbar_start)
    assert toolbar_start < counts_pos < table_wrap_pos < footer_pos


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
    critical_pos = html.index("重点 1 件", left_pos)
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

    assert 'class="alert-row alert-row--重点 ioa-data-row"' in html
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
    assert "在庫内訳" in html
    assert "ロケーション内訳" not in html
    assert 'class="ioa-location-col-incoming"' in html
    assert 'class="ioa-location-col-location"' in html
    assert 'class="ioa-location-col-qty"' in html
    assert 'class="ioa-confirmation-status"' in html
    assert "/static/js/inventory-order-alert-list.js" in html


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
@patch("apps.inventory_order_alert.composition.portal_dashboard_usecase")
def test_dashboard_shows_inventory_order_alert_banner(mock_usecase_factory, client, production_user):
    from apps.inventory_order_alert.usecase.usecase_portal_dashboard import DashboardBannerContext

    mock_usecase_factory.return_value.execute.return_value = DashboardBannerContext(
        critical=1,
        warning_ship=1,
        warning_incoming=1,
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
