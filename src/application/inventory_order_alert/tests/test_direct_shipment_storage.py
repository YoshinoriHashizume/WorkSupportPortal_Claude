"""直送仕入先（V-240）の保存と、取込から集計スナップショット保存までの直送品（T-212）の除外。

spec/12_direct-shipment-exclusion test-design.md TC-DSE-I-001〜005・I-020〜023。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings
from application.inventory_order_alert.domain.value_objects.direct_shipment import DirectShipmentSuppliers
from application.inventory_order_alert.infrastructure.oracle.summary_aggregation import run_summary_aggregation
from application.inventory_order_alert.infrastructure.persistence.settings_repository import (
    load_app_settings,
    save_app_settings,
)
from application.inventory_order_alert.infrastructure.persistence.summary_repository import load_latest_summary
from application.inventory_order_alert.models import (
    InventoryOrderAlertConfirmation,
    InventoryOrderAlertConfirmationMemoEntry,
    InventoryOrderAlertSettings,
    InventoryOrderAlertSummarySnapshot,
    SlimsStockImport,
    default_direct_shipment_supplier_codes,
)
from application.inventory_order_alert.use_cases.import_stock import ImportStock

AGGREGATION = "application.inventory_order_alert.infrastructure.oracle.summary_aggregation"


# --- I-001〜005: 設定の保存 -------------------------------------------------------


@pytest.mark.django_db
def test_i001_new_settings_row_has_default_direct_suppliers():
    InventoryOrderAlertSettings.objects.all().delete()

    assert load_app_settings().direct_shipment_suppliers.codes == ("9100", "9200", "9250")


def test_i002_model_default_and_migration_point_to_default_codes():
    from importlib import import_module

    field = InventoryOrderAlertSettings._meta.get_field("direct_shipment_supplier_codes")
    assert field.default is default_direct_shipment_supplier_codes
    assert default_direct_shipment_supplier_codes() == ["9100", "9200", "9250"]

    migration = import_module("application.inventory_order_alert.migrations.0016_direct_shipment_suppliers").Migration
    [operation] = migration.operations
    assert operation.name == "direct_shipment_supplier_codes"
    assert operation.field.default is default_direct_shipment_supplier_codes


@pytest.mark.django_db
def test_i003_saved_direct_suppliers_are_read_back_with_updater():
    admin = get_user_model().objects.create_user(username="10002")
    before = InventoryOrderAlertSettings.objects.get_or_create(pk=1)[0].updated_at

    saved = save_app_settings(
        warning_days=365,
        stock_stale_days=7,
        direct_shipment_suppliers=DirectShipmentSuppliers.parse(["9250"]),
        updated_by=admin,
    )

    row = InventoryOrderAlertSettings.objects.get(pk=1)
    assert saved.direct_shipment_suppliers.codes == ("9250",)
    assert load_app_settings().direct_shipment_suppliers.codes == ("9250",)
    assert row.updated_by == admin
    assert row.updated_at >= before


@pytest.mark.django_db
def test_i004_save_without_direct_suppliers_keeps_value():
    InventoryOrderAlertSettings.objects.update_or_create(pk=1, defaults={"direct_shipment_supplier_codes": ["9100"]})

    save_app_settings(warning_days=100, stock_stale_days=7)

    assert load_app_settings().direct_shipment_suppliers.codes == ("9100",)


@pytest.mark.django_db
@pytest.mark.parametrize(("stored", "expected"), [("abc", ()), ([1, "", "9100"], ("9100",))])
def test_i005_broken_stored_value_is_read_safely(stored, expected):
    InventoryOrderAlertSettings.objects.update_or_create(pk=1, defaults={"direct_shipment_supplier_codes": stored})

    assert load_app_settings().direct_shipment_suppliers.codes == expected


# --- I-020〜023: 取込から保存まで ------------------------------------------------


def _direct_row() -> dict[str, object]:
    return {
        "cust_code": "308",
        "item_cd": "15D126-0020",
        "level1_item_cd": "15D126-0020-9100",
        "level1_vend_cd": "9100",
        "stock_qty": "",
        "flow_quadrant": "通常流動品",
    }


def _normal_row() -> dict[str, object]:
    return {
        "cust_code": "100",
        "item_cd": "062432-0680",
        "level1_item_cd": "062432-0680-9146",
        "level1_vend_cd": "9146",
        "stock_qty": "11165",
        "flow_quadrant": "通常流動品",
    }


def _run_import(codes: list[str]) -> MagicMock:
    """直送仕入先を `codes` にして取込の集計 → 後処理 → 保存を実行し、偽の接続を返す。"""
    settings = AppSettings(direct_shipment_suppliers=DirectShipmentSuppliers.parse(codes))
    captured: dict[str, object] = {}

    def fake_import(text, *, user=None, file_name="", enrich_rows=None):
        captured["enrich_rows"] = enrich_rows
        return None

    ImportStock(fake_import, lambda: settings).execute(b"x")
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=2)
    connection = MagicMock()

    def fake_build_list_rows(conn, query, *, stock_lines=None, stock_as_of_date=None, warnings=None):
        conn.cursor()  # 集計の問い合わせ 1 回分
        return [_direct_row(), _normal_row()]

    with (
        patch(f"{AGGREGATION}.oracle_connection") as oracle_connection,
        patch(f"{AGGREGATION}.build_list_rows", side_effect=fake_build_list_rows),
    ):
        oracle_connection.return_value.__enter__.return_value = connection
        error, _, _ = run_summary_aggregation(import_record, [], enrich_rows=captured["enrich_rows"])
    assert error == ""
    return connection


def _latest_snapshot() -> InventoryOrderAlertSummarySnapshot:
    return InventoryOrderAlertSummarySnapshot.objects.order_by("-created_at", "-pk").first()


def _confirmation_in_progress() -> InventoryOrderAlertConfirmation:
    confirmation = InventoryOrderAlertConfirmation.objects.create(
        cust_code="308",
        item_cd="15D126-0020",
        status="in_progress",
        # 再取込後の流動区分と同じにする（悪化すると既存の仕組みで未確認に戻るため。本件とは別の振る舞い）
        confirmed_flow_quadrant="打ち切り候補",
        confirmed_by="10002",
    )
    InventoryOrderAlertConfirmationMemoEntry.objects.create(confirmation=confirmation, content="仕入先に確認中")
    return confirmation


@pytest.mark.django_db
def test_i020_direct_shipment_rows_are_not_stored_nor_counted():
    _run_import(["9100"])

    snapshot = _latest_snapshot()
    assert [row["item_cd"] for row in snapshot.rows] == ["062432-0680"]
    assert snapshot.total_count == 1


@pytest.mark.django_db
def test_i021_confirmation_of_direct_shipment_item_is_kept():
    confirmation = _confirmation_in_progress()

    _run_import(["9100"])

    confirmation.refresh_from_db()
    assert confirmation.status == "in_progress"
    assert confirmation.memo_entries.count() == 1


@pytest.mark.django_db
def test_i022_removing_supplier_brings_rows_back_with_confirmation():
    _confirmation_in_progress()
    _run_import(["9100"])

    _run_import([])

    summary = load_latest_summary()
    rows = {row["item_cd"]: row for row in summary.rows}
    assert "15D126-0020" in rows
    assert rows["15D126-0020"]["confirmation_status"] == "確認中"


@pytest.mark.django_db
def test_i023_exclusion_does_not_add_oracle_queries():
    with_suppliers = _run_import(["9100"]).cursor.call_count
    without_suppliers = _run_import([]).cursor.call_count

    assert with_suppliers == without_suppliers == 1
