from __future__ import annotations

import re
from datetime import datetime
from email.header import decode_header
from pathlib import Path
from urllib.parse import unquote
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404

from apps.portal.favorites import (
    is_menu_path_active,
    receipt_comparison_menu_key,
    receipt_comparison_type_from_path,
)
from apps.portal.middleware import receipt_comparison_menu_key_for_request
from apps.portal.models import PortalMenuGroupAccess
from apps.receipt_comparison.domain.comparison import compare_receipts, normalize_qty
from apps.receipt_comparison.domain.file_parser import parse_receipt_file
from apps.receipt_comparison.domain.records import MariReceiptRow, ReceiptFileRow
from apps.receipt_comparison.models import (
    FinishedProductComparisonResult,
    FinishedProductFileImport,
    FinishedProductReceiptSupplier,
    FinishedProductReceivingSetting,
    ReceiptComparisonType,
    ReceiptFlag,
    SuppliedPartsReceiptSupplier,
)
from apps.receipt_comparison.domain.comparison_type import is_finished_product
from apps.receipt_comparison.infrastructure.persistence.model_registry import (
    comparison_result_model,
    list_suppliers_for_settings,
    supplier_model,
)
from apps.receipt_comparison.domain.comparison_type import UnknownComparisonTypeError, comparison_type_from_slug
from apps.receipt_comparison.domain.comparison_urls import is_results_panel_active, settings_redirect_path
from apps.receipt_comparison.domain.settings_labels import settings_target_label
from apps.receipt_comparison.infrastructure.oracle.receipt_choices import list_customer_choices, list_vendor_choices
from apps.receipt_comparison.infrastructure.persistence.supplier_lookup import receiving_places_for_supplier
from apps.receipt_comparison.usecase.usecase_comparison_page import comparison_export_filename


def attachment_filename_from_response(response) -> str:
    header = response["Content-Disposition"]
    if header.startswith("=?"):
        decoded_parts = []
        for part, charset in decode_header(header):
            if isinstance(part, bytes):
                decoded_parts.append(part.decode(charset or "utf-8"))
            else:
                decoded_parts.append(part)
        header = "".join(decoded_parts)
    filename_star = re.search(r"filename\*=utf-8''([^;]+)", header, re.IGNORECASE)
    if filename_star:
        return unquote(filename_star.group(1))
    match = re.search(r'filename="([^"]+)"', header)
    assert match is not None
    return match.group(1)


def assert_results_head_button_order(
    html: str,
    *,
    has_register: bool = False,
    has_update: bool = False,
) -> None:
    actions_start = html.index('class="receipt-results-head-actions"')
    actions_html = html[actions_start : actions_start + 1200]
    file_pos = actions_html.index("ファイル選択")
    csv_pos = actions_html.index("CSV</a>")
    assert file_pos < csv_pos
    if has_register:
        register_pos = actions_html.index('name="action" value="register"')
        assert csv_pos < register_pos
    if has_update:
        update_pos = actions_html.index('name="action" value="update"')
        assert csv_pos < update_pos


def test_comparison_export_filename_uses_type_label_and_timestamp():
    at = datetime(2026, 6, 23, 13, 45, 6, tzinfo=ZoneInfo("Asia/Tokyo"))
    finished = comparison_export_filename(ReceiptComparisonType.FINISHED_PRODUCT, at=at)
    supplied = comparison_export_filename(ReceiptComparisonType.SUPPLIED_PARTS, at=at)

    assert finished == "検収書比較結果(完成品)_20260623134506.csv"
    assert supplied == "検収書比較結果(支給品)_20260623134506.csv"


@pytest.fixture
def admin_user(db):
    user = get_user_model().objects.create_user(username="receipt-admin")
    group, _ = Group.objects.get_or_create(name="管理者")
    user.groups.add(group)
    PortalMenuGroupAccess.objects.create(user=user, group_key="production")
    return user


@pytest.fixture
def production_user(db):
    user = get_user_model().objects.create_user(username="receipt-user")
    group, _ = Group.objects.get_or_create(name="一般ユーザー")
    user.groups.add(group)
    PortalMenuGroupAccess.objects.create(user=user, group_key="production")
    return user


@pytest.fixture
def supplier(db):
    return FinishedProductReceiptSupplier.objects.create(
        customer_code="001",
        name="テスト取引先",
    )


def test_receipt_comparison_menu_key_maps_type_to_menu_key():
    assert receipt_comparison_menu_key("finished-product") == "receipt-comparison-finished-product"
    assert receipt_comparison_menu_key("supplied-parts") == "receipt-comparison-supplied-parts"
    assert receipt_comparison_menu_key("finished_product") == "receipt-comparison-finished-product"
    assert receipt_comparison_menu_key("supplied_parts") == "receipt-comparison-supplied-parts"


@pytest.mark.django_db
def test_receipt_comparison_page_shows_favorite_toggle(client, production_user):
    client.force_login(production_user)

    finished_html = client.get("/app/production/receipt-comparison?type=finished-product").content.decode("utf-8")
    supplied_html = client.get("/app/production/receipt-comparison?type=supplied-parts").content.decode("utf-8")

    assert 'data-menu-key="receipt-comparison-finished-product"' in finished_html
    assert 'data-menu-key="receipt-comparison-supplied-parts"' in supplied_html
    assert 'class="favorite-toggle portal-title-favorite"' in finished_html
    assert "完成品のお気に入りを切り替え" in finished_html
    assert "支給品のお気に入りを切り替え" in supplied_html


def test_receipt_comparison_type_from_path():
    assert receipt_comparison_type_from_path("/app/production/receipt-comparison/supplied-parts/settings") == "supplied-parts"
    assert receipt_comparison_type_from_path("/app/production/receipt-comparison") == "finished-product"


def test_is_menu_path_active_for_unified_receipt_comparison_url():
    assert is_menu_path_active(
        "/app/production/receipt-comparison",
        "/app/production/receipt-comparison?type=finished-product",
        "finished-product",
    )
    assert is_menu_path_active(
        "/app/production/receipt-comparison",
        "/app/production/receipt-comparison?type=supplied-parts",
        "supplied-parts",
    )
    assert not is_menu_path_active(
        "/app/production/receipt-comparison",
        "/app/production/receipt-comparison?type=finished-product",
        "supplied-parts",
    )


def test_comparison_type_from_slug():
    assert comparison_type_from_slug("finished-product") == ReceiptComparisonType.FINISHED_PRODUCT
    assert comparison_type_from_slug("supplied-parts") == ReceiptComparisonType.SUPPLIED_PARTS

    with pytest.raises(UnknownComparisonTypeError):
        comparison_type_from_slug("invalid")


def test_model_registry_returns_split_models():
    assert supplier_model(ReceiptComparisonType.FINISHED_PRODUCT) is FinishedProductReceiptSupplier
    assert supplier_model(ReceiptComparisonType.SUPPLIED_PARTS) is SuppliedPartsReceiptSupplier
    assert comparison_result_model(ReceiptComparisonType.FINISHED_PRODUCT) is FinishedProductComparisonResult
    assert is_finished_product(ReceiptComparisonType.FINISHED_PRODUCT) is True
    assert is_finished_product(ReceiptComparisonType.SUPPLIED_PARTS) is False


def test_finished_product_csv_skips_card_no_s():
    content = "カードNO,品番,納入月日,納入数,納入取消数\nA,AB-001,0601,10,0\nS,SKIP,0601,5,0\n".encode("cp932")

    rows = parse_receipt_file(
        comparison_type=ReceiptComparisonType.FINISHED_PRODUCT,
        file_name="receipt.csv",
        content=content,
    )

    assert rows == [ReceiptFileRow(item_cd="AB-001", delivery_month_day="0601", qty="10", cancel_qty="0")]


def test_supplied_parts_txt_filters_and_converts_rows():
    content = "x,V001,2026/06/01,1234567890,x,10\nx,OTHER,2026/06/01,1234567890,x,10\n".encode("cp932")

    rows = parse_receipt_file(
        comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
        file_name="receipt.txt",
        content=content,
        subcontractor_codes=["V001"],
        exclusion=True,
    )

    assert rows == [
        ReceiptFileRow(
            item_cd="1234567890",
            delivery_month_day="0601",
            qty="10",
            cancel_qty="0",
            supplier_name="V001",
        )
    ]


def test_normalize_qty_treats_oracle_null_as_zero():
    assert normalize_qty(None) == "0"
    assert normalize_qty(0) == "0"
    assert normalize_qty("0") == "0"
    assert normalize_qty("") == ""


def test_compare_receipts_displays_null_mari_qty_as_zero():
    rows = compare_receipts(
        [MariReceiptRow(item_cd="2305250410", ship_date="2026/05/12", ship_qty=None, delivery_place="WH1")],
        [],
        supplied_parts=True,
    )

    assert len(rows) == 1
    assert rows[0].mari_item_cd == "2305250410"
    assert rows[0].mari_date == "2026/05/12"
    assert rows[0].mari_qty == "0"


def test_compare_receipts_matches_item_date_and_quantity():
    rows = compare_receipts(
        [MariReceiptRow(item_cd="AB-001", ship_date="2026/06/01", ship_qty="10", delivery_place="A1")],
        [ReceiptFileRow(item_cd="AB001", delivery_month_day="0601", qty="10", cancel_qty="0")],
    )

    assert len(rows) == 1
    assert rows[0].receipt_flag == ReceiptFlag.OK
    assert rows[0].supplier_item_cd == "AB001"


def test_compare_receipts_supplied_parts_matches_ten_digit_item():
    rows = compare_receipts(
        [MariReceiptRow(item_cd="2305231010", ship_date="2026/05/19", ship_qty="1800", delivery_place="WH")],
        [
            ReceiptFileRow(
                item_cd="2305231010",
                delivery_month_day="0519",
                qty="1800",
                cancel_qty="0",
                supplier_name="106",
            )
        ],
        supplied_parts=True,
    )

    assert len(rows) == 1
    assert rows[0].receipt_flag == ReceiptFlag.OK
    assert rows[0].supplier_item_cd == "2305231010"
    assert rows[0].supplier_qty == "1800"
    assert rows[0].supplier_name == "106"


@pytest.mark.django_db
def test_receipt_comparison_menu_shows_customer_and_supplied_parts(client, production_user):
    client.force_login(production_user)

    response = client.get("/app")

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "完成品" in html
    assert "支給品" in html
    assert "検収書比較" in html
    assert 'href="/app/production/receipt-comparison?type=finished-product"' in html
    assert 'href="/app/production/receipt-comparison?type=supplied-parts"' in html


@pytest.mark.django_db
def test_receipt_comparison_title_shows_type_without_in_page_switch(client, production_user):
    client.force_login(production_user)

    finished = client.get("/app/production/receipt-comparison?type=finished-product")
    supplied = client.get("/app/production/receipt-comparison?type=supplied-parts")

    assert finished.status_code == 200
    assert supplied.status_code == 200
    finished_html = finished.content.decode("utf-8")
    supplied_html = supplied.content.decode("utf-8")
    assert "検収書比較（完成品）" in finished_html
    assert "検収書比較（支給品）" in supplied_html
    assert "<label>得意先" in finished_html
    assert "<label>得意先" in supplied_html
    assert "得意先を選択してください" in finished_html
    assert "取引先を選択してください" not in finished_html
    assert 'class="receipt-type-switch"' not in finished_html
    assert 'class="receipt-type-switch"' not in supplied_html


@pytest.mark.django_db
def test_receipt_comparison_settings_link_visible_only_for_admin(client, production_user, admin_user):
    client.force_login(production_user)
    general_html = client.get("/app/production/receipt-comparison?type=finished-product").content.decode("utf-8")
    assert "/app/production/receipt-comparison/settings" not in general_html

    client.force_login(admin_user)
    admin_html = client.get("/app/production/receipt-comparison?type=finished-product").content.decode("utf-8")
    assert "/app/production/receipt-comparison/settings?type=finished-product" in admin_html


@pytest.mark.django_db
def test_receipt_comparison_settings_requires_admin(client, production_user, admin_user):
    client.force_login(production_user)

    response = client.get("/app/production/receipt-comparison/settings?type=finished-product")

    assert response.status_code == 403

    client.force_login(admin_user)
    admin_response = client.get("/app/production/receipt-comparison/settings?type=finished-product")

    assert admin_response.status_code == 200


@pytest.mark.django_db
def test_receipt_comparison_redirects_without_type(client, production_user):
    client.force_login(production_user)

    response = client.get("/app/production/receipt-comparison")

    assert response.status_code == 302
    assert response["Location"] == "/app/production/receipt-comparison?type=finished-product"


@pytest.mark.django_db
def test_receipt_comparison_legacy_slug_redirects_to_unified_url(client, production_user):
    client.force_login(production_user)

    response = client.get("/app/production/receipt-comparison/supplied-parts?supplier_id=1")

    assert response.status_code == 302
    assert response["Location"] == "/app/production/receipt-comparison?type=supplied-parts&supplier_id=1"


@pytest.mark.django_db
def test_user_without_production_group_cannot_open_receipt_comparison(client):
    user = get_user_model().objects.create_user(username="no-production")
    client.force_login(user)

    response = client.get("/app/production/receipt-comparison?type=finished-product")

    assert response.status_code == 403


@pytest.mark.django_db
def test_receipt_comparison_compare_does_not_save_until_register(client, production_user, supplier, monkeypatch):
    def fake_fetch_mari_rows(**kwargs):
        return [MariReceiptRow(item_cd="AB-001", ship_date="2026/06/01", ship_qty="10", delivery_place="A1")]

    monkeypatch.setattr("apps.receipt_comparison.infrastructure.oracle.client.fetch_mari_rows", fake_fetch_mari_rows)
    client.force_login(production_user)
    upload = SimpleUploadedFile(
        "receipt.csv",
        "カードNO,品番,納入月日,納入数,納入取消数\nA,AB001,0601,10,0\n".encode("cp932"),
        content_type="text/csv",
    )

    compare_response = client.post(
        "/app/production/receipt-comparison?type=finished-product",
        {
            "type": "finished-product",
            "supplier_id": str(supplier.id),
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
            "action": "compare",
            "receipt_file": upload,
        },
    )

    assert compare_response.status_code == 302
    assert FinishedProductComparisonResult.objects.filter(supplier=supplier).count() == 0

    pending_page = client.get(compare_response["Location"])
    assert pending_page.status_code == 200
    pending_html = pending_page.content.decode("utf-8")
    assert "（未登録）" in pending_html
    assert 'name="action" value="register"' in pending_html
    assert 'class="receipt-results-head-actions"' in pending_html
    assert "CSV</a>" in pending_html
    assert f"{supplier.primary_code} - {supplier.name} /" not in pending_html
    assert_results_head_button_order(pending_html, has_register=True)

    register_response = client.post(
        compare_response["Location"],
        {
            "type": "finished-product",
            "supplier_id": str(supplier.id),
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
            "action": "register",
            "receipt_flag_pending_0": str(ReceiptFlag.OK),
            "remarks_pending_0": "",
        },
    )

    assert register_response.status_code == 302
    result = FinishedProductComparisonResult.objects.get(supplier=supplier)
    assert result.receipt_flag == ReceiptFlag.OK
    assert result.mari_item_cd == "AB-001"
    assert result.supplier_item_cd == "AB001"


@pytest.mark.django_db
def test_receipt_comparison_display_clears_pending_preview(client, production_user, supplier, monkeypatch):
    def fake_fetch_mari_rows(**kwargs):
        return []

    monkeypatch.setattr("apps.receipt_comparison.infrastructure.oracle.client.fetch_mari_rows", fake_fetch_mari_rows)
    client.force_login(production_user)
    upload = SimpleUploadedFile(
        "receipt.csv",
        "カードNO,品番,納入月日,納入数,納入取消数\nA,AB001,0601,10,0\n".encode("cp932"),
        content_type="text/csv",
    )
    compare_response = client.post(
        "/app/production/receipt-comparison?type=finished-product",
        {
            "type": "finished-product",
            "supplier_id": str(supplier.id),
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
            "action": "compare",
            "receipt_file": upload,
        },
    )

    display_response = client.get(
        "/app/production/receipt-comparison"
        f"?type=finished-product&supplier_id={supplier.id}&start_date=2026-06-01&end_date=2026-06-30&display=1"
    )

    assert display_response.status_code == 200
    assert 'name="action" value="register"' not in display_response.content.decode("utf-8")


@pytest.mark.django_db
def test_receipt_comparison_sort_header_link(client, production_user, supplier):
    file_import = FinishedProductFileImport.objects.create(
        supplier=supplier,
        original_file_name="receipt.csv",
        stored_file_name="receipt.csv",
        receipt_date="2026-06-30",
    )
    FinishedProductComparisonResult.objects.create(
        supplier=supplier,
        file_import=file_import,
        receipt_flag=ReceiptFlag.NG,
        mari_item_cd="Z-999",
    )
    client.force_login(production_user)

    response = client.get(
        "/app/production/receipt-comparison"
        f"?type=finished-product&supplier_id={supplier.id}&start_date=2026-06-01&end_date=2026-06-30"
        "&display=1&sort=mari_item_cd&dir=desc"
    )

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "sort=mari_item_cd" in html
    assert "▼" in html


@pytest.mark.django_db
def test_receipt_comparison_update_keeps_results_panel_actions(client, production_user, supplier):
    file_import = FinishedProductFileImport.objects.create(
        supplier=supplier,
        original_file_name="receipt.csv",
        stored_file_name="receipt.csv",
        receipt_date="2026-06-30",
    )
    result = FinishedProductComparisonResult.objects.create(
        supplier=supplier,
        file_import=file_import,
        receipt_flag=ReceiptFlag.NG,
        mari_item_cd="Z-999",
        remarks="",
    )
    client.force_login(production_user)
    client.get(
        "/app/production/receipt-comparison"
        f"?type=finished-product&supplier_id={supplier.id}&start_date=2026-06-01&end_date=2026-06-30&display=1"
    )

    update_response = client.post(
        "/app/production/receipt-comparison?type=finished-product",
        {
            "type": "finished-product",
            "supplier_id": str(supplier.id),
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
            "action": "update",
            "result_id": str(result.id),
            f"receipt_flag_{result.id}": str(ReceiptFlag.OK),
            f"remarks_{result.id}": "確認済み",
        },
    )

    assert update_response.status_code == 302
    assert "display=1" in update_response["Location"]

    html = client.get(update_response["Location"]).content.decode("utf-8")
    assert "receipt-comparison--results-panel" in html
    assert 'class="receipt-results-file-input"' in html
    assert "CSV</a>" in html
    assert '>更新</button>' in html
    assert 'name="action" value="update"' in html
    assert_results_head_button_order(html, has_update=True)

    result.refresh_from_db()
    assert result.receipt_flag == ReceiptFlag.OK
    assert result.remarks == "確認済み"


@pytest.mark.django_db
def test_receipt_comparison_can_export_pending_without_register(client, production_user, supplier, monkeypatch):
    def fake_fetch_mari_rows(**kwargs):
        return [MariReceiptRow(item_cd="AB-001", ship_date="2026/06/01", ship_qty="10", delivery_place="A1")]

    monkeypatch.setattr("apps.receipt_comparison.infrastructure.oracle.client.fetch_mari_rows", fake_fetch_mari_rows)
    client.force_login(production_user)
    upload = SimpleUploadedFile(
        "receipt.csv",
        "カードNO,品番,納入月日,納入数,納入取消数\nA,AB001,0601,10,0\n".encode("cp932"),
        content_type="text/csv",
    )
    compare_response = client.post(
        "/app/production/receipt-comparison?type=finished-product",
        {
            "type": "finished-product",
            "supplier_id": str(supplier.id),
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
            "action": "compare",
            "receipt_file": upload,
        },
    )

    export = client.get(
        "/app/production/receipt-comparison/export"
        f"?type=finished-product&supplier_id={supplier.id}&start_date=2026-06-01&end_date=2026-06-30"
    )

    assert compare_response.status_code == 302
    assert export.status_code == 200
    assert "filename*=utf-8''" in export["Content-Disposition"].lower()
    assert attachment_filename_from_response(export).startswith("検収書比較結果(完成品)_")
    assert attachment_filename_from_response(export).endswith(".csv")
    assert "AB-001" in export.content.decode("cp932")
    assert FinishedProductComparisonResult.objects.filter(supplier=supplier).count() == 0


@pytest.mark.django_db
def test_receipt_comparison_can_register_and_export(client, production_user, supplier, monkeypatch):
    def fake_fetch_mari_rows(**kwargs):
        return [MariReceiptRow(item_cd="AB-001", ship_date="2026/06/01", ship_qty="10", delivery_place="A1")]

    monkeypatch.setattr("apps.receipt_comparison.infrastructure.oracle.client.fetch_mari_rows", fake_fetch_mari_rows)
    client.force_login(production_user)
    upload = SimpleUploadedFile(
        "receipt.csv",
        "カードNO,品番,納入月日,納入数,納入取消数\nA,AB001,0601,10,0\n".encode("cp932"),
        content_type="text/csv",
    )

    compare_response = client.post(
        "/app/production/receipt-comparison?type=finished-product",
        {
            "type": "finished-product",
            "supplier_id": str(supplier.id),
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
            "action": "compare",
            "receipt_file": upload,
        },
    )
    client.post(
        compare_response["Location"],
        {
            "type": "finished-product",
            "supplier_id": str(supplier.id),
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
            "action": "register",
            "receipt_flag_pending_0": str(ReceiptFlag.OK),
            "remarks_pending_0": "",
        },
    )

    export = client.get(
        "/app/production/receipt-comparison/export"
        f"?type=finished-product&supplier_id={supplier.id}&start_date=2026-06-01&end_date=2026-06-30"
        "&sort=receipt_flag&dir=asc"
    )

    assert export.status_code == 200
    assert "text/csv" in export["Content-Type"]
    assert attachment_filename_from_response(export).startswith("検収書比較結果(完成品)_")
    assert "AB-001" in export.content.decode("cp932")



@pytest.mark.django_db
def test_receiving_places_for_supplier_uses_all_registered_settings(supplier):
    FinishedProductReceivingSetting.objects.create(supplier=supplier, delivery_place="A1")
    FinishedProductReceivingSetting.objects.create(supplier=supplier, delivery_place="B2")

    assert receiving_places_for_supplier(supplier) == ["A1", "B2"]


@pytest.mark.django_db
def test_finished_product_settings_get_with_registered_supplier(client, admin_user, supplier, monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")
    client.force_login(admin_user)

    response = client.get("/app/production/receipt-comparison/settings?type=finished-product")

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "得意先一覧" in html
    assert supplier.customer_code in html
    assert supplier.name in html
    assert f'receipt-supplier-dialog-{supplier.id}' in html
    assert 'class="receipt-supplier-row"' in html
    assert 'receipt-settings-body' in html
    assert 'receipt-settings-list-card' in html
    assert 'receipt-supplier-table--finished' in html
    assert 'receipt-receiving-table' in html
    assert 'receipt-receiving-enabled-field' not in html
    assert '>有効</th>' not in html
    assert "得意先追加" in html
    sidebar = html.split("receipt-settings-sidebar")[1].split("receipt-settings-list-card")[0]
    assert sidebar.index("得意先追加") < sidebar.index("</form>")
    assert 'receipt-settings-sidebar' in html
    assert "設定した受入/納品場所を除外する" in html
    assert ">受入/納品場所</th>" in html
    assert 'receipt-supplier-dialog-settings' in html
    assert 'receipt-supplier-dialog-settings-toolbar' in html
    assert 'receipt-supplier-dialog-settings-panel' in html
    assert 'receipt-supplier-direct-delivery-label' in html
    assert 'receipt-supplier-direct-delivery-row' in html
    assert '直送先得意先コード' in html
    label_index = html.index('receipt-supplier-direct-delivery-label')
    row_index = html.index('receipt-supplier-direct-delivery-row', label_index)
    exclusion_index = html.index('receipt-supplier-exclusion-field', row_index)
    row_section = html[row_index:exclusion_index]
    assert 'name="direct_delivery_customer_code"' in row_section
    assert 'value="update_supplier">更新</button>' in row_section
    assert 'value="delete_supplier"' in row_section
    assert '>削除</button>' in row_section
    assert 'receipt-supplier-direct-delivery-field' in html
    assert 'portal-customer-select--receipt' in html
    assert '設定を更新' not in html
    assert '得意先を削除' not in html
    assert '<th scope="row">直送先得意先コード</th>' not in html
    assert 'value="update_receiving"' not in html


@pytest.mark.django_db
def test_receipt_settings_receiving_table_is_delete_only(client, admin_user, supplier, monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")
    FinishedProductReceivingSetting.objects.create(supplier=supplier, delivery_place="A1")
    client.force_login(admin_user)

    response = client.get(
        f"/app/production/receipt-comparison/settings?type=finished-product&supplier_id={supplier.id}"
    )

    html = response.content.decode("utf-8")
    assert response.status_code == 200
    assert 'value="update_receiving"' not in html
    assert 'class="mono">A1</td>' in html
    assert 'value="delete_receiving"' in html
    receiving_section = html.split("receipt-receiving-table", 1)[1].split("</table>", 1)[0]
    tbody = receiving_section.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    assert 'name="delivery_place"' not in tbody


def test_receipt_supplier_dialog_settings_toolbar_layout_css():
    css_path = Path(__file__).resolve().parents[1] / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")
    assert ".receipt-supplier-dialog-settings-toolbar" in css
    assert ".receipt-supplier-direct-delivery-row" in css
    direct_delivery_row_rule = css.split(".receipt-supplier-direct-delivery-row {")[1].split("}")[0]
    assert "display: flex" in direct_delivery_row_rule
    assert "justify-content: flex-start" in direct_delivery_row_rule
    panel_rule = css.split(".receipt-supplier-dialog-settings-panel {")[1].split("}")[0]
    assert "justify-items: start" in panel_rule


def test_receipt_supplier_dialog_tables_use_full_width_columns():
    css_path = Path(__file__).resolve().parents[1] / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")
    assert ".receipt-supplier-dialog-table-wrap" in css
    assert "overflow-x: hidden" in css.split(".receipt-supplier-dialog .receipt-supplier-dialog-table-wrap {")[1].split("}")[0]
    assert ".receipt-supplier-dialog .receipt-supplier-dialog-table-wrap .db-table th {" in css
    assert "position: sticky" in css.split(".receipt-supplier-dialog .receipt-supplier-dialog-table-wrap .db-table th {")[1]


def test_receipt_receiving_table_column_widths():
    css_path = Path(__file__).resolve().parents[1] / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")
    no_col_rule = css.split(
        ".receipt-supplier-dialog .receipt-receiving-table th:nth-child(1),\n"
        ".receipt-supplier-dialog .receipt-receiving-table td:nth-child(1) {"
    )[1].split("}")[0]
    place_col_rule = css.split(
        ".receipt-supplier-dialog .receipt-receiving-table th:nth-child(2),\n"
        ".receipt-supplier-dialog .receipt-receiving-table td:nth-child(2) {"
    )[1].split("}")[0]
    action_col_rule = css.split(
        ".receipt-supplier-dialog .receipt-receiving-table th:last-child,\n"
        ".receipt-supplier-dialog .receipt-receiving-table td:last-child {"
    )[1].split("}")[0]
    assert "width: 3rem" in no_col_rule
    assert "width: auto" in place_col_rule
    assert "width: 120px" in action_col_rule
    actions_button_rule = css.split(".receipt-receiving-table .receipt-table-actions button {")[1].split("}")[0]
    assert "width: 100%" not in actions_button_rule


def test_receipt_supplier_dialog_table_actions_are_centered():
    css_path = Path(__file__).resolve().parents[1] / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")
    actions_rule = css.split(
        ".receipt-supplier-dialog .receipt-supplier-dialog-table-wrap .receipt-table-actions {"
    )[1].split("}")[0]
    assert "text-align: center" in actions_rule
    receiving_actions_rule = css.split(".receipt-receiving-table .receipt-table-actions {")[1].split("}")[0]
    assert "justify-content: center" in receiving_actions_rule


@pytest.mark.django_db
def test_receipt_settings_receiving_table_shows_row_numbers(client, admin_user, supplier, monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")
    FinishedProductReceivingSetting.objects.create(supplier=supplier, delivery_place="B2")
    FinishedProductReceivingSetting.objects.create(supplier=supplier, delivery_place="A1")
    client.force_login(admin_user)

    response = client.get(
        f"/app/production/receipt-comparison/settings?type=finished-product&supplier_id={supplier.id}"
    )

    html = response.content.decode("utf-8")
    assert response.status_code == 200
    assert ">No.</th>" in html
    receiving_section = html.split("receipt-receiving-table", 1)[1].split("</table>", 1)[0]
    tbody = receiving_section.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    assert 'class="receipt-table-row-no">1</td>' in tbody
    assert 'class="mono">A1</td>' in tbody
    assert 'class="receipt-table-row-no">2</td>' in tbody
    assert 'class="mono">B2</td>' in tbody
    assert tbody.index('class="receipt-table-row-no">1</td>') < tbody.index('class="mono">A1</td>')
    assert tbody.index('class="receipt-table-row-no">2</td>') < tbody.index('class="mono">B2</td>')


def _supplier_list_table_head(html: str, table_class: str) -> str:
    return html.split(table_class, 1)[1].split("</thead>", 1)[0]


@pytest.mark.django_db
def test_finished_product_supplier_list_table_column_order(client, admin_user, supplier, monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")
    client.force_login(admin_user)

    response = client.get("/app/production/receipt-comparison/settings?type=finished-product")

    assert response.status_code == 200
    thead = _supplier_list_table_head(response.content.decode("utf-8"), "receipt-supplier-table--finished")
    assert thead.index(">除外</th>") < thead.index(">受入/納品場所</th>")


@pytest.mark.django_db
def test_supplied_parts_supplier_list_table_column_order(client, admin_user, db, monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")
    SuppliedPartsReceiptSupplier.objects.create(customer_code="191", name="支給品取引先")
    client.force_login(admin_user)

    response = client.get("/app/production/receipt-comparison/settings?type=supplied-parts")

    assert response.status_code == 200
    thead = _supplier_list_table_head(response.content.decode("utf-8"), "receipt-supplier-table--supplied")
    assert thead.index(">除外</th>") < thead.index(">品番</th>")


@pytest.mark.django_db
def test_receipt_settings_dialog_includes_scrollable_table_wrap(client, admin_user, supplier, monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")
    client.force_login(admin_user)

    response = client.get("/app/production/receipt-comparison/settings?type=finished-product")

    html = response.content.decode("utf-8")
    assert response.status_code == 200
    assert 'class="db-table-wrap receipt-supplier-dialog-table-wrap receipt-receiving-table-wrap"' in html


def test_receipt_comparison_page_fixes_table_header_and_scroll_area():
    css_path = Path(__file__).resolve().parents[1] / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")
    assert "body.portal-app-page { overflow: hidden; height: 100dvh; }" in css
    assert "body.portal-app-page .portal-shell { height: 100dvh; max-height: 100dvh; overflow: hidden; }" in css
    assert "body.portal-app-page .portal-main { height: 100dvh; max-height: 100dvh; overflow: hidden; min-height: 0; }" in css
    assert "body.portal-app-page .content > .receipt-comparison" in css
    assert ".receipt-comparison-page .receipt-results-card .db-table-wrap" in css
    table_wrap_rule = css.split(".receipt-comparison-page .receipt-results-card .db-table-wrap {")[1].split("}")[0]
    assert "overflow: auto" in table_wrap_rule
    assert "min-height: 0" in table_wrap_rule
    assert "flex: 1" not in table_wrap_rule
    assert ".receipt-comparison-page .receipt-results-card .db-table th" in css
    assert "position: sticky" in css
    receipt_comparison_rule = css.split(".receipt-comparison-page .receipt-comparison {")[1].split("}")[0]
    assert "align-content: stretch" in receipt_comparison_rule
    assert "minmax(0, 1fr)" in receipt_comparison_rule
    assert "height: 100%" not in receipt_comparison_rule
    results_card_rule = css.split(".receipt-comparison-page .receipt-results-card {")[1].split("}")[0]
    assert "height: 100%" not in results_card_rule
    filter_field_rule = css.split("body.portal-app-page .receipt-filter select,")[1].split("}")[0]
    assert "var(--portal-control-height)" in filter_field_rule
    assert 'input[type="date"]' in filter_field_rule


@pytest.mark.django_db
def test_comparison_page_uses_fixed_layout_body_class(client, production_user):
    client.force_login(production_user)
    response = client.get("/app/production/receipt-comparison?type=finished-product")
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert 'class="portal-app-page receipt-comparison-page"' in html


@pytest.mark.django_db
def test_display_shows_file_select_in_results_header(client, production_user, supplier):
    client.force_login(production_user)
    response = client.get(
        "/app/production/receipt-comparison?type=finished-product"
        f"&supplier_id={supplier.id}&start_date=2026-06-01&end_date=2026-06-30&display=1"
    )

    html = response.content.decode("utf-8")
    assert response.status_code == 200
    assert "receipt-comparison--results-panel" in html
    assert 'id="receipt-results-compare-form"' in html
    assert 'class="receipt-results-file-input"' in html
    assert "ファイル選択" in html
    assert 'receipt-upload card' not in html
    assert f"{supplier.primary_code} - {supplier.name} /" not in html


@pytest.mark.django_db
def test_display_without_results_still_shows_file_select(client, production_user, supplier):
    client.force_login(production_user)
    response = client.get(
        "/app/production/receipt-comparison?type=finished-product"
        f"&supplier_id={supplier.id}&start_date=2026-06-01&end_date=2026-06-30&display=1"
    )

    html = response.content.decode("utf-8")
    assert "比較結果はありません。" in html
    assert 'class="receipt-results-file-input"' in html
    assert 'name="action" value="update"' not in html


@pytest.mark.django_db
def test_display_file_select_runs_compare(client, production_user, supplier, monkeypatch):
    def fake_fetch_mari_rows(**kwargs):
        return [MariReceiptRow(item_cd="AB-001", ship_date="2026/06/01", ship_qty="10", delivery_place="A1")]

    monkeypatch.setattr("apps.receipt_comparison.infrastructure.oracle.client.fetch_mari_rows", fake_fetch_mari_rows)
    client.force_login(production_user)
    client.get(
        "/app/production/receipt-comparison?type=finished-product"
        f"&supplier_id={supplier.id}&start_date=2026-06-01&end_date=2026-06-30&display=1"
    )
    upload = SimpleUploadedFile(
        "receipt.csv",
        "カードNO,品番,納入月日,納入数,納入取消数\nA,AB001,0601,10,0\n".encode("cp932"),
        content_type="text/csv",
    )
    compare_response = client.post(
        "/app/production/receipt-comparison?type=finished-product",
        {
            "type": "finished-product",
            "supplier_id": str(supplier.id),
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
            "action": "compare",
            "receipt_file": upload,
        },
    )

    assert compare_response.status_code == 302
    pending_page = client.get(compare_response["Location"])
    html = pending_page.content.decode("utf-8")
    assert "（未登録）" in html
    assert 'class="receipt-results-file-input"' in html
    assert 'href="/app/production/receipt-comparison/export' in html
    assert "CSV</a>" in html
    assert_results_head_button_order(html, has_register=True)
    assert FinishedProductComparisonResult.objects.filter(supplier=supplier).count() == 0


@pytest.mark.django_db
def test_supplier_without_display_does_not_show_upload_form(client, production_user, supplier):
    client.force_login(production_user)
    response = client.get(
        "/app/production/receipt-comparison?type=finished-product"
        f"&supplier_id={supplier.id}&start_date=2026-06-01&end_date=2026-06-30"
    )

    html = response.content.decode("utf-8")
    assert 'class="receipt-upload card"' not in html
    assert 'class="receipt-results-file-input"' not in html
    assert "比較結果はありません。" in html


@pytest.mark.django_db
def test_no_supplier_shows_message_in_results_card_without_file_select(client, production_user):
    client.force_login(production_user)
    html = client.get("/app/production/receipt-comparison?type=finished-product").content.decode("utf-8")

    assert "得意先を選択してください" in html
    assert "管理者に得意先の登録を依頼してください" in html
    assert 'class="receipt-results-head-actions"' not in html
    assert 'class="receipt-results-file-input"' not in html
    message_pos = html.index("得意先を選択してください")
    results_card_pos = html.index('class="receipt-results-card card receipt-results-main-form"')
    assert results_card_pos < message_pos


@pytest.mark.django_db
def test_no_supplier_admin_sees_settings_hint_in_results_card(client, admin_user):
    client.force_login(admin_user)
    html = client.get("/app/production/receipt-comparison?type=finished-product").content.decode("utf-8")

    assert "得意先が表示されない場合は、設定画面で登録してください。" in html
    assert 'class="receipt-results-head-actions"' not in html


@pytest.mark.django_db
def test_is_results_panel_active_with_display_flag(supplier):
    assert is_results_panel_active(
        method="GET",
        get_display="1",
        get_compared=None,
        post_action=None,
        supplier_selected=True,
        has_pending=False,
    )


def test_is_results_panel_active_with_compare_post(supplier):
    assert is_results_panel_active(
        method="POST",
        get_display=None,
        get_compared=None,
        post_action="compare",
        supplier_selected=True,
        has_pending=False,
    )


@pytest.mark.django_db
def test_list_suppliers_for_settings_prefetch_by_comparison_type(supplier, db):
    finished_queryset = list_suppliers_for_settings(ReceiptComparisonType.FINISHED_PRODUCT)
    supplied_queryset = list_suppliers_for_settings(ReceiptComparisonType.SUPPLIED_PARTS)

    assert list(finished_queryset) == [supplier]
    assert "receiving_settings" in finished_queryset._prefetch_related_lookups
    assert "subcontractors" not in finished_queryset._prefetch_related_lookups

    SuppliedPartsReceiptSupplier.objects.create(customer_code="191", name="支給品取引先")
    assert list(supplied_queryset)
    assert "receiving_settings" in supplied_queryset._prefetch_related_lookups
    assert "subcontractors" in supplied_queryset._prefetch_related_lookups


@pytest.mark.django_db
def test_finished_product_settings_can_delete_receiving_setting(client, admin_user, supplier):
    setting = FinishedProductReceivingSetting.objects.create(supplier=supplier, delivery_place="A1")
    client.force_login(admin_user)

    response = client.post(
        "/app/production/receipt-comparison/settings?type=finished-product",
        {
            "type": "finished-product",
            "action": "delete_receiving",
            "supplier_id": str(supplier.id),
            "setting_id": str(setting.id),
        },
    )

    assert response.status_code == 302
    assert response["Location"] == f"/app/production/receipt-comparison/settings?type=finished-product&supplier_id={supplier.id}"
    assert not FinishedProductReceivingSetting.objects.filter(id=setting.id).exists()


@pytest.mark.django_db
def test_finished_product_settings_update_supplier_does_not_change_customer_code(client, admin_user, supplier):
    client.force_login(admin_user)

    response = client.post(
        "/app/production/receipt-comparison/settings?type=finished-product",
        {
            "type": "finished-product",
            "action": "update_supplier",
            "supplier_id": str(supplier.id),
            "direct_delivery_customer_code": "102",
            "exclusion": "on",
        },
        follow=True,
    )

    assert response.status_code == 200
    supplier.refresh_from_db()
    assert supplier.customer_code == "001"
    assert supplier.direct_delivery_customer_code == "102"
    assert supplier.exclusion is True


@pytest.mark.django_db
def test_supplied_parts_settings_update_supplier_does_not_change_customer_code(client, admin_user):
    supplier = SuppliedPartsReceiptSupplier.objects.create(customer_code="191", name="サンプル得意先E")
    client.force_login(admin_user)

    response = client.post(
        "/app/production/receipt-comparison/settings?type=supplied-parts",
        {
            "type": "supplied-parts",
            "action": "update_supplier",
            "supplier_id": str(supplier.id),
            "exclusion": "on",
        },
        follow=True,
    )

    assert response.status_code == 200
    supplier.refresh_from_db()
    assert supplier.customer_code == "191"
    assert supplier.exclusion is True


@pytest.mark.django_db
def test_finished_product_settings_can_delete_supplier_with_related_data(client, admin_user, supplier, production_user):
    setting = FinishedProductReceivingSetting.objects.create(supplier=supplier, delivery_place="A1")
    file_import = FinishedProductFileImport.objects.create(
        supplier=supplier,
        original_file_name="receipt.csv",
        stored_file_name="stored.csv",
        receipt_date="2026-06-30",
        imported_by=production_user,
    )
    result = FinishedProductComparisonResult.objects.create(
        supplier=supplier,
        file_import=file_import,
        receipt_flag=ReceiptFlag.OK,
        mari_item_cd="AB-001",
    )
    client.force_login(admin_user)

    response = client.post(
        "/app/production/receipt-comparison/settings?type=finished-product",
        {
            "type": "finished-product",
            "action": "delete_supplier",
            "supplier_id": str(supplier.id),
        },
    )

    assert response.status_code == 302
    assert not FinishedProductReceiptSupplier.objects.filter(id=supplier.id).exists()
    assert not FinishedProductReceivingSetting.objects.filter(id=setting.id).exists()
    assert not FinishedProductFileImport.objects.filter(id=file_import.id).exists()
    assert not FinishedProductComparisonResult.objects.filter(id=result.id).exists()


@pytest.mark.django_db
def test_finished_product_settings_can_create_supplier(client, admin_user, monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")
    client.force_login(admin_user)

    response = client.post(
        "/app/production/receipt-comparison/settings?type=finished-product",
        {
            "type": "finished-product",
            "action": "add_supplier",
            "customer_code": "101",
            "direct_delivery_customer_code": "102",
            "exclusion": "on",
        },
    )

    assert response.status_code == 302
    assert response["Location"] == "/app/production/receipt-comparison/settings?type=finished-product"
    supplier = FinishedProductReceiptSupplier.objects.get(customer_code="101")
    assert supplier.name == "サンプル得意先A"
    assert supplier.direct_delivery_customer_code == "102"
    assert supplier.exclusion is True


@pytest.mark.django_db
def test_settings_use_unified_template_with_oracle_customer_selection(client, admin_user, monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")
    client.force_login(admin_user)

    finished_response = client.get("/app/production/receipt-comparison/settings?type=finished-product")
    finished_html = finished_response.content.decode("utf-8")
    assert finished_response.status_code == 200
    assert "101 - サンプル得意先A" in finished_html
    assert "得意先" in finished_html
    assert "得意先一覧" in finished_html
    assert 'name="customer_code"' in finished_html
    assert 'class="portal-customer-select portal-customer-select--receipt"' in finished_html
    assert 'name="direct_delivery_customer_code"' in finished_html
    assert "直送先得意先コード" in finished_html
    assert 'name="code_type"' not in finished_html
    assert 'name="vendor_code"' not in finished_html
    assert "比較画面にはここで登録した得意先のみ表示されます" in finished_html

    create_response = client.post(
        "/app/production/receipt-comparison/settings?type=supplied-parts",
        {
            "type": "supplied-parts",
            "action": "add_supplier",
            "customer_code": "191",
        },
    )

    assert create_response.status_code == 302
    supplier = SuppliedPartsReceiptSupplier.objects.get(customer_code="191")
    assert supplier.name == "サンプル得意先E"

    supplied_response = client.get("/app/production/receipt-comparison/settings?type=supplied-parts")
    supplied_html = supplied_response.content.decode("utf-8")
    assert "191 - サンプル得意先E" in supplied_html
    add_form = supplied_html.split("receipt-supplier-add-card")[1].split("receipt-settings-list-card")[0]
    assert "101 - サンプル得意先A" in add_form
    assert 'name="vendor_code"' in supplied_html
    assert 'portal-vendor-select--receipt' in supplied_html
    assert "9990 - サンプル仕入先E" in supplied_html


def test_settings_redirect_url_includes_supplier_id():
    base = "/app/production/receipt-comparison/settings"
    assert (
        settings_redirect_path(base, "finished-product", 12)
        == "/app/production/receipt-comparison/settings?type=finished-product&supplier_id=12"
    )
    assert settings_redirect_path(base, "supplied-parts") == "/app/production/receipt-comparison/settings?type=supplied-parts"


@pytest.mark.django_db
def test_receipt_comparison_display_resets_sort_to_result(client, production_user, supplier):
    file_import = FinishedProductFileImport.objects.create(
        supplier=supplier,
        original_file_name="receipt.csv",
        stored_file_name="receipt.csv",
        receipt_date="2026-06-30",
    )
    FinishedProductComparisonResult.objects.create(
        supplier=supplier,
        file_import=file_import,
        receipt_flag=ReceiptFlag.NG,
        mari_item_cd="A-001",
    )
    FinishedProductComparisonResult.objects.create(
        supplier=supplier,
        file_import=file_import,
        receipt_flag=ReceiptFlag.OK,
        mari_item_cd="Z-999",
    )
    client.force_login(production_user)

    sorted_by_item = client.get(
        "/app/production/receipt-comparison"
        f"?type=finished-product&supplier_id={supplier.id}&start_date=2026-06-01&end_date=2026-06-30"
        "&display=1&sort=mari_item_cd&dir=desc"
    )
    body_sorted = sorted_by_item.content.decode("utf-8").split("<tbody>")[1].split("</tbody>")[0]
    assert body_sorted.index("Z-999") < body_sorted.index("A-001")

    display_response = client.get(
        "/app/production/receipt-comparison"
        f"?type=finished-product&supplier_id={supplier.id}&start_date=2026-06-01&end_date=2026-06-30&display=1"
    )
    html = display_response.content.decode("utf-8")
    assert "▲" in html
    body = html.split("<tbody>")[1].split("</tbody>")[0]
    assert body.index("A-001") < body.index("Z-999")


class DummyRequest:
    def __init__(self, path: str, query: dict[str, str] | None = None):
        self.path = path
        self.GET = query or {}


def test_receipt_comparison_menu_key_for_request():
    assert receipt_comparison_menu_key_for_request(
        DummyRequest("/app/production/receipt-comparison", {"type": "finished-product"})
    ) == "receipt-comparison-finished-product"
    assert receipt_comparison_menu_key_for_request(
        DummyRequest("/app/production/receipt-comparison/settings", {"type": "supplied-parts"})
    ) == "receipt-comparison-supplied-parts"
    assert receipt_comparison_menu_key_for_request(
        DummyRequest("/app/production/receipt-comparison/finished-product/export")
    ) == "receipt-comparison-finished-product"
    assert receipt_comparison_menu_key_for_request(DummyRequest("/app/other")) is None
