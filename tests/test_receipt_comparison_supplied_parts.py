from __future__ import annotations

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.portal.models import PortalMenuGroupAccess
from apps.receipt_comparison.domain.file_parser import (
    normalize_supplied_parts_item_cd,
    parse_receipt_file,
    parse_supplied_parts_qty,
)
from apps.receipt_comparison.domain.records import MariReceiptRow, ReceiptFileRow
from apps.gonenkukumi.infrastructure.oracle.customers import (
    customer_code_digit_pattern,
    list_customers_by_digit_length,
)
from apps.receipt_comparison.models import (
    ReceiptComparisonType,
    ReceiptFlag,
    SuppliedPartsComparisonResult,
    SuppliedPartsFileImport,
    SuppliedPartsReceiptSupplier,
    SuppliedPartsReceivingSetting,
    SuppliedPartsSubcontractor,
)
from apps.receipt_comparison.type_registry import customer_digit_length
from tests.test_receipt_comparison import assert_results_head_button_order


@pytest.fixture
def production_user(db):
    user = get_user_model().objects.create_user(username="supplied-receipt-user")
    group, _ = Group.objects.get_or_create(name="一般ユーザー")
    user.groups.add(group)
    PortalMenuGroupAccess.objects.create(user=user, group_key="production")
    return user


@pytest.fixture
def admin_user(db):
    user = get_user_model().objects.create_user(username="supplied-receipt-admin")
    group, _ = Group.objects.get_or_create(name="管理者")
    user.groups.add(group)
    PortalMenuGroupAccess.objects.create(user=user, group_key="production")
    return user


@pytest.fixture
def supplied_parts_supplier(db):
    supplier = SuppliedPartsReceiptSupplier.objects.create(
        customer_code="191",
        name="サンプル得意先E",
    )
    SuppliedPartsSubcontractor.objects.create(
        supplier=supplier,
        vendor_code="106",
    )
    SuppliedPartsSubcontractor.objects.create(
        supplier=supplier,
        vendor_code="9990",
        vendor_name="サンプル仕入先E",
    )
    SuppliedPartsReceivingSetting.objects.create(supplier=supplier, delivery_place="1234567890")
    SuppliedPartsReceivingSetting.objects.create(supplier=supplier, delivery_place="2305231010")
    return supplier


def test_customer_digit_length_for_supplied_parts():
    assert customer_digit_length(ReceiptComparisonType.SUPPLIED_PARTS) == 3
    assert customer_digit_length(ReceiptComparisonType.FINISHED_PRODUCT) == 3


def test_list_receipt_customers_oracle_regex_pattern_uses_single_backslash():
    assert customer_code_digit_pattern(3) == "^\\d{3}$"
    assert customer_code_digit_pattern(3).count("\\") == 1


def test_list_receipt_customers_filters_by_digit_length(monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")

    finished_customers = list_customers_by_digit_length(digit_length=3)
    supplied_customers = list_customers_by_digit_length(digit_length=3)

    assert all(len(row["custCode"]) == 3 for row in finished_customers)
    assert all(len(row["custCode"]) == 3 for row in supplied_customers)
    assert any(row["custCode"] == "191" for row in supplied_customers)
    assert not any(row["custCode"] == "1001" for row in finished_customers)


def test_supplied_parts_txt_rejects_non_txt_extension():
    with pytest.raises(ValueError, match="txt"):
        parse_receipt_file(
            comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
            file_name="receipt.csv",
            content=b"x",
        )


def test_supplied_parts_txt_matches_customer_code():
    content = "x,9001,2026/06/01,1234567890,x,10\n".encode("cp932")

    rows = parse_receipt_file(
        comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
        file_name="receipt.txt",
        content=content,
        subcontractor_codes=["9001", "9101"],
        exclusion=True,
    )

    assert len(rows) == 1
    assert rows[0].supplier_name == "9001"


def test_supplied_parts_txt_matches_vendor_code():
    content = "x,9101,2026/06/01,1234567890,x,10\n".encode("cp932")

    rows = parse_receipt_file(
        comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
        file_name="receipt.txt",
        content=content,
        subcontractor_codes=["9001", "9101"],
        exclusion=True,
    )

    assert len(rows) == 1
    assert rows[0].supplier_name == "9101"


def test_supplied_parts_txt_skips_unknown_partner_code():
    content = "x,OTHER,2026/06/01,1234567890,x,10\n".encode("cp932")

    rows = parse_receipt_file(
        comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
        file_name="receipt.txt",
        content=content,
        subcontractor_codes=["9001"],
        exclusion=True,
    )

    assert rows == []


def test_supplied_parts_txt_skips_when_subcontractor_codes_empty():
    content = "x,9001,2026/06/01,1234567890,x,10\n".encode("cp932")

    rows = parse_receipt_file(
        comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
        file_name="receipt.txt",
        content=content,
        subcontractor_codes=[],
        exclusion=True,
    )

    assert rows == []


def test_supplied_parts_txt_skips_when_receiving_places_empty_and_exclusion_off():
    content = "x,9001,2026/06/01,1234567890,x,10\n".encode("cp932")

    rows = parse_receipt_file(
        comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
        file_name="receipt.txt",
        content=content,
        subcontractor_codes=["9001"],
        receiving_places=[],
        exclusion=False,
    )

    assert rows == []


def test_supplied_parts_txt_exclusion_on_skips_matching_place():
    content = "x,9001,2026/06/01,1234567890,x,10\n".encode("cp932")

    rows = parse_receipt_file(
        comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
        file_name="receipt.txt",
        content=content,
        subcontractor_codes=["9001"],
        receiving_places=["1234567890"],
        exclusion=True,
    )

    assert rows == []


def test_supplied_parts_txt_exclusion_off_requires_matching_place():
    content = "x,9001,2026/06/01,1234567890,x,10\n".encode("cp932")

    rows = parse_receipt_file(
        comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
        file_name="receipt.txt",
        content=content,
        subcontractor_codes=["9001"],
        receiving_places=["1234567890"],
        exclusion=False,
    )

    assert len(rows) == 1

    skipped = parse_receipt_file(
        comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
        file_name="receipt.txt",
        content=content,
        subcontractor_codes=["9001"],
        receiving_places=["9999999999"],
        exclusion=False,
    )
    assert skipped == []


def test_normalize_supplied_parts_item_cd_strips_suffix():
    assert normalize_supplied_parts_item_cd("123456789012345") == "1234567890"
    assert normalize_supplied_parts_item_cd("1234567890") == "1234567890"
    assert normalize_supplied_parts_item_cd("1234-567890-12345") == "1234567890"


def test_supplied_parts_txt_skips_non_ten_digit_item():
    content = "x,9001,2026/06/01,123456789012345,x,10\n".encode("cp932")

    rows = parse_receipt_file(
        comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
        file_name="receipt.txt",
        content=content,
        subcontractor_codes=["9001"],
        exclusion=True,
    )

    assert rows == []


def test_supplied_parts_txt_matches_place_before_length_check():
    content = "x,9001,2026/06/01,123456789012345,x,10\n".encode("cp932")

    rows = parse_receipt_file(
        comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
        file_name="receipt.txt",
        content=content,
        subcontractor_codes=["9001"],
        receiving_places=["123456789012345"],
        exclusion=False,
    )

    assert rows == []


def test_supplied_parts_txt_requires_exact_partner_code():
    content = "x,09001,2026/06/01,1234567890,x,10\n".encode("cp932")

    rows = parse_receipt_file(
        comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
        file_name="receipt.txt",
        content=content,
        subcontractor_codes=["9001"],
        exclusion=True,
    )

    assert rows == []


def test_parse_supplied_parts_qty_accepts_decimal_string():
    assert parse_supplied_parts_qty("1800.00") == 1800
    assert parse_supplied_parts_qty("1011.00") == 1011
    assert parse_supplied_parts_qty("10") == 10
    assert parse_supplied_parts_qty("0") == 0
    assert parse_supplied_parts_qty("-1.00") == -1


def test_parse_supplied_parts_qty_skips_invalid():
    assert parse_supplied_parts_qty("abc") is None
    assert parse_supplied_parts_qty("") is None


def test_supplied_parts_txt_accepts_ten_digit_item_with_decimal_qty():
    content = "x,106,26/05/27,2305231010,x,1011.00,x\n".encode("cp932")

    rows = parse_receipt_file(
        comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
        file_name="receipt.txt",
        content=content,
        subcontractor_codes=["106"],
        exclusion=True,
    )

    assert len(rows) == 1
    assert rows[0].item_cd == "2305231010"
    assert rows[0].qty == "1011"
    assert rows[0].delivery_month_day == "0527"


def test_supplied_parts_txt_accepts_parent_customer_code_in_column_two():
    content = "x,191,26/05/27,2305231010,x,1011.00\n".encode("cp932")

    rows = parse_receipt_file(
        comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
        file_name="receipt.txt",
        content=content,
        subcontractor_codes=["9990"],
        parent_customer_code="191",
        exclusion=True,
    )

    assert len(rows) == 1
    assert rows[0].item_cd == "2305231010"
    assert rows[0].supplier_name == "191"


@pytest.mark.django_db
def test_supplied_parts_compare_fills_file_values_when_mari_matches(
    client, production_user, supplied_parts_supplier, monkeypatch
):
    def fake_fetch_mari_rows(**kwargs):
        return [
            MariReceiptRow(item_cd="2305231010", ship_date="2026/05/19", ship_qty="1800", delivery_place="WH1"),
        ]

    monkeypatch.setattr("apps.receipt_comparison.views.fetch_mari_rows", fake_fetch_mari_rows)
    client.force_login(production_user)
    sample = (
        Path(__file__).resolve().parent / "fixtures" / "supplied_parts_material_sample.txt"
    ).read_bytes()
    upload = SimpleUploadedFile("receipt.txt", sample, content_type="text/plain")

    compare_response = client.post(
        "/app/production/receipt-comparison?type=supplied-parts",
        {
            "type": "supplied-parts",
            "supplier_id": str(supplied_parts_supplier.id),
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
            "action": "compare",
            "receipt_file": upload,
        },
    )

    pending_page = client.get(compare_response["Location"])
    pending_html = pending_page.content.decode("utf-8")
    assert "（未登録）" in pending_html
    assert ">2305231010</td>" in pending_html
    assert ">1800</td>" in pending_html
    assert "106" in pending_html


def test_supplied_parts_txt_parses_realistic_material_sample():
    sample = (
        Path(__file__).resolve().parent / "fixtures" / "supplied_parts_material_sample.txt"
    ).read_bytes()

    rows = parse_receipt_file(
        comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
        file_name="receipt.txt",
        content=sample,
        subcontractor_codes=["106", "9990"],
        exclusion=True,
    )

    assert len(rows) == 1
    assert rows[0].item_cd == "2305231010"
    assert rows[0].qty == "1800"


def test_supplied_parts_txt_skips_non_digit_item():
    content = "x,9001,2026/06/01,ABCDE,x,10\n".encode("cp932")

    rows = parse_receipt_file(
        comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
        file_name="receipt.txt",
        content=content,
        subcontractor_codes=["9001"],
        exclusion=True,
    )

    assert rows == []


def test_supplied_parts_txt_skips_short_digit_item():
    content = "x,9001,2026/06/01,12345,x,10\n".encode("cp932")

    rows = parse_receipt_file(
        comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
        file_name="receipt.txt",
        content=content,
        subcontractor_codes=["9001"],
        exclusion=True,
    )

    assert rows == []


def test_supplied_parts_txt_converts_date_qty_and_cancel_qty():
    content = "x,9001,2026/06/01,1234567890,x,10\n".encode("cp932")

    rows = parse_receipt_file(
        comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
        file_name="receipt.txt",
        content=content,
        subcontractor_codes=["9001"],
        exclusion=True,
    )

    assert rows == [
        ReceiptFileRow(
            item_cd="1234567890",
            delivery_month_day="0601",
            qty="10",
            cancel_qty="0",
            supplier_name="9001",
        )
    ]


def test_supplied_parts_txt_uses_right_four_digits_for_short_date():
    content = "x,9001,06,1234567890,x,10\n".encode("cp932")

    rows = parse_receipt_file(
        comparison_type=ReceiptComparisonType.SUPPLIED_PARTS,
        file_name="receipt.txt",
        content=content,
        subcontractor_codes=["9001"],
        exclusion=True,
    )

    assert rows[0].delivery_month_day == "06"


@pytest.mark.django_db
def test_supplied_parts_compare_warns_when_file_has_no_matching_rows(
    client, production_user, supplied_parts_supplier, monkeypatch
):
    monkeypatch.setattr("apps.receipt_comparison.views.fetch_mari_rows", lambda **kwargs: [])
    client.force_login(production_user)
    upload = SimpleUploadedFile(
        "receipt.txt",
        "x,OTHER,2026/06/01,123456789012345,x,10\n".encode("cp932"),
        content_type="text/plain",
    )

    compare_response = client.post(
        "/app/production/receipt-comparison?type=supplied-parts",
        {
            "type": "supplied-parts",
            "supplier_id": str(supplied_parts_supplier.id),
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
            "action": "compare",
            "receipt_file": upload,
        },
        follow=True,
    )

    assert compare_response.status_code == 200
    assert "比較対象行を読み取れませんでした" in compare_response.content.decode("utf-8")


@pytest.mark.django_db
def test_supplied_parts_compare_shows_receipt_only_row_when_mari_empty(
    client, production_user, supplied_parts_supplier, monkeypatch
):
    monkeypatch.setattr("apps.receipt_comparison.views.fetch_mari_rows", lambda **kwargs: [])
    client.force_login(production_user)
    upload = SimpleUploadedFile(
        "receipt.txt",
        "x,106,2026/06/01,1234567890,x,10\n".encode("cp932"),
        content_type="text/plain",
    )

    compare_response = client.post(
        "/app/production/receipt-comparison?type=supplied-parts",
        {
            "type": "supplied-parts",
            "supplier_id": str(supplied_parts_supplier.id),
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
            "action": "compare",
            "receipt_file": upload,
        },
    )

    pending_page = client.get(compare_response["Location"])
    pending_html = pending_page.content.decode("utf-8")
    assert "1234567890" in pending_html
    assert "（未登録）" in pending_html


@pytest.mark.django_db
def test_supplied_parts_compare_does_not_save_until_register(
    client, production_user, supplied_parts_supplier, monkeypatch
):
    def fake_fetch_mari_rows(**kwargs):
        return [MariReceiptRow(item_cd="1234567890", ship_date="2026/06/01", ship_qty="10", delivery_place="WH1")]

    monkeypatch.setattr("apps.receipt_comparison.views.fetch_mari_rows", fake_fetch_mari_rows)
    client.force_login(production_user)
    upload = SimpleUploadedFile(
        "receipt.txt",
        "x,106,2026/06/01,1234567890,x,10\n".encode("cp932"),
        content_type="text/plain",
    )

    compare_response = client.post(
        "/app/production/receipt-comparison?type=supplied-parts",
        {
            "type": "supplied-parts",
            "supplier_id": str(supplied_parts_supplier.id),
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
            "action": "compare",
            "receipt_file": upload,
        },
    )

    assert compare_response.status_code == 302
    assert SuppliedPartsComparisonResult.objects.filter(supplier=supplied_parts_supplier).count() == 0

    pending_page = client.get(compare_response["Location"])
    pending_html = pending_page.content.decode("utf-8")
    assert "（未登録）" in pending_html
    assert "比較しました" not in pending_html
    assert 'name="action" value="register"' in pending_html
    assert 'class="receipt-results-head-actions"' in pending_html
    assert "CSV</a>" in pending_html
    assert_results_head_button_order(pending_html, has_register=True)
    assert "取引先名" in pending_html or "supplier_name" in pending_html or "106" in pending_html

    register_response = client.post(
        compare_response["Location"],
        {
            "type": "supplied-parts",
            "supplier_id": str(supplied_parts_supplier.id),
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
            "action": "register",
            "receipt_flag_pending_0": str(ReceiptFlag.OK),
            "remarks_pending_0": "",
        },
    )

    assert register_response.status_code == 302
    result = SuppliedPartsComparisonResult.objects.get(supplier=supplied_parts_supplier)
    assert result.receipt_flag == ReceiptFlag.OK
    assert result.mari_item_cd == "1234567890"
    assert result.supplier_item_cd == "1234567890"
    assert result.supplier_name == "106"

    saved_page = client.get(register_response["Location"])
    saved_html = saved_page.content.decode("utf-8")
    assert "比較結果を登録しました" not in saved_html
    assert "（未登録）" not in saved_html


@pytest.mark.django_db
def test_compare_without_file_shows_error_message(client, production_user, supplied_parts_supplier):
    client.force_login(production_user)
    response = client.post(
        "/app/production/receipt-comparison?type=supplied-parts",
        {
            "type": "supplied-parts",
            "supplier_id": str(supplied_parts_supplier.id),
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
            "action": "compare",
        },
        follow=True,
    )

    assert response.status_code == 200
    assert "受領書データを選択してください" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_supplied_parts_can_register_and_export(client, production_user, supplied_parts_supplier, monkeypatch):
    def fake_fetch_mari_rows(**kwargs):
        return [MariReceiptRow(item_cd="1234567890", ship_date="2026/06/01", ship_qty="10", delivery_place="WH1")]

    monkeypatch.setattr("apps.receipt_comparison.views.fetch_mari_rows", fake_fetch_mari_rows)
    client.force_login(production_user)
    upload = SimpleUploadedFile(
        "receipt.txt",
        "x,106,2026/06/01,1234567890,x,10\n".encode("cp932"),
        content_type="text/plain",
    )

    compare_response = client.post(
        "/app/production/receipt-comparison?type=supplied-parts",
        {
            "type": "supplied-parts",
            "supplier_id": str(supplied_parts_supplier.id),
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
            "action": "compare",
            "receipt_file": upload,
        },
    )
    client.post(
        compare_response["Location"],
        {
            "type": "supplied-parts",
            "supplier_id": str(supplied_parts_supplier.id),
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
            "action": "register",
            "receipt_flag_pending_0": str(ReceiptFlag.OK),
            "remarks_pending_0": "",
        },
    )

    export = client.get(
        "/app/production/receipt-comparison/export"
        f"?type=supplied-parts&supplier_id={supplied_parts_supplier.id}"
        "&start_date=2026-06-01&end_date=2026-06-30&sort=receipt_flag&dir=asc"
    )

    assert export.status_code == 200
    assert "text/csv" in export["Content-Type"]
    body = export.content.decode("cp932")
    assert "1234567890" in body
    assert "106" in body


@pytest.mark.django_db
def test_supplied_parts_settings_requires_three_digit_customer(client, admin_user, monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")
    client.force_login(admin_user)

    response = client.post(
        "/app/production/receipt-comparison/settings?type=supplied-parts",
        {
            "type": "supplied-parts",
            "action": "add_supplier",
            "customer_code": "1001",
        },
        follow=True,
    )

    assert response.status_code == 200
    assert not SuppliedPartsReceiptSupplier.objects.filter(customer_code="1001").exists()


@pytest.mark.django_db
def test_supplied_parts_settings_can_create_supplier(client, admin_user, monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")
    client.force_login(admin_user)

    response = client.post(
        "/app/production/receipt-comparison/settings?type=supplied-parts",
        {
            "type": "supplied-parts",
            "action": "add_supplier",
            "customer_code": "191",
        },
    )

    assert response.status_code == 302
    supplier = SuppliedPartsReceiptSupplier.objects.get(customer_code="191")
    assert supplier.name == "サンプル得意先E"


@pytest.mark.django_db
def test_supplied_parts_settings_rejects_non_four_digit_subcontractor(
    client, admin_user, supplied_parts_supplier
):
    client.force_login(admin_user)
    before_count = SuppliedPartsSubcontractor.objects.filter(supplier=supplied_parts_supplier).count()

    response = client.post(
        "/app/production/receipt-comparison/settings?type=supplied-parts",
        {
            "type": "supplied-parts",
            "action": "add_subcontractor",
            "supplier_id": str(supplied_parts_supplier.id),
            "vendor_code": "12",
        },
        follow=True,
    )

    assert response.status_code == 200
    assert SuppliedPartsSubcontractor.objects.filter(supplier=supplied_parts_supplier).count() == before_count
    assert not SuppliedPartsSubcontractor.objects.filter(
        supplier=supplied_parts_supplier,
        vendor_code="12",
    ).exists()


@pytest.mark.django_db
def test_supplied_parts_settings_can_add_and_delete_subcontractor(
    client, admin_user, supplied_parts_supplier, monkeypatch
):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")
    client.force_login(admin_user)

    add_response = client.post(
        "/app/production/receipt-comparison/settings?type=supplied-parts",
        {
            "type": "supplied-parts",
            "action": "add_subcontractor",
            "supplier_id": str(supplied_parts_supplier.id),
            "vendor_code": "9106",
        },
    )
    assert add_response.status_code == 302
    subcontractor = SuppliedPartsSubcontractor.objects.get(supplier=supplied_parts_supplier, vendor_code="9106")
    assert subcontractor.vendor_name == "サンプル仕入先D"

    delete_response = client.post(
        "/app/production/receipt-comparison/settings?type=supplied-parts",
        {
            "type": "supplied-parts",
            "action": "delete_subcontractor",
            "supplier_id": str(supplied_parts_supplier.id),
            "subcontractor_id": str(subcontractor.id),
        },
    )
    assert delete_response.status_code == 302
    assert not SuppliedPartsSubcontractor.objects.filter(id=subcontractor.id).exists()


@pytest.mark.django_db
def test_supplied_parts_settings_list_shows_subcontractor_column(
    client, admin_user, supplied_parts_supplier, monkeypatch
):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")
    client.force_login(admin_user)

    response = client.get("/app/production/receipt-comparison/settings?type=supplied-parts")

    html = response.content.decode("utf-8")
    assert "Oracle 購買取引先" not in html
    assert "追加取引先" not in html
    assert "191" in html
    assert "106" in html
    assert "9990 - サンプル仕入先E" in html
    assert ">子取引先</th>" in html
    assert 'receipt-supplier-exclusion-field' in html
    assert '<th scope="row">得意先</th>' not in html
    assert 'receipt-supplier-readonly-value' not in html
    assert 'receipt-supplier-table--supplied' in html
    assert supplied_parts_supplier.customer_code in html
    assert "得意先追加" in html
    assert "取引先追加" not in html
    assert "設定した品番を除外する" in html
    assert "設定した受入/納品場所を除外する" not in html
    assert ">品番</th>" in html
    assert "子取引先" in html
    assert "購買取引先コード" not in html
    assert ">コード</th>" in html
    assert "MARI取得・受領TXTの2列目照合に使用します。" not in html
    assert "portal-vendor-select--receipt" in html


@pytest.mark.django_db
def test_supplied_parts_subcontractor_add_form_layout_classes(
    client, admin_user, supplied_parts_supplier, monkeypatch
):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")
    client.force_login(admin_user)

    response = client.get(
        "/app/production/receipt-comparison/settings"
        f"?type=supplied-parts&supplier_id={supplied_parts_supplier.id}"
    )

    html = response.content.decode("utf-8")
    assert 'class="receipt-inline-form receipt-subcontractor-add-form"' in html
    assert 'name="action" value="add_subcontractor"' in html
    assert "receipt-subcontractor-vendor-field" in html


def test_subcontractor_add_form_css_aligns_select_with_button():
    css_path = Path(__file__).resolve().parents[1] / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")
    assert ".receipt-subcontractor-add-form.receipt-inline-form" in css
    assert "align-items: flex-end" in css
    assert ".receipt-subcontractor-add-form button[type=\"submit\"]" in css


@pytest.mark.django_db
def test_subcontractor_display_label_with_and_without_name():
    supplier = SuppliedPartsReceiptSupplier.objects.create(customer_code="191", name="テスト得意先")
    named = SuppliedPartsSubcontractor.objects.create(
        supplier=supplier,
        vendor_code="9990",
        vendor_name="サンプル仕入先E",
    )
    unnamed = SuppliedPartsSubcontractor.objects.create(
        supplier=supplier,
        vendor_code="106",
    )

    assert named.display_label == "9990 - サンプル仕入先E"
    assert unnamed.display_label == "106"


@pytest.mark.django_db
def test_supplied_parts_subcontractor_dialog_shows_vendor_name_column(
    client, admin_user, supplied_parts_supplier, monkeypatch
):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")
    client.force_login(admin_user)

    response = client.get(
        "/app/production/receipt-comparison/settings"
        f"?type=supplied-parts&supplier_id={supplied_parts_supplier.id}"
    )

    html = response.content.decode("utf-8")
    assert ">購買取引先名</th>" in html
    assert "サンプル仕入先E" in html
