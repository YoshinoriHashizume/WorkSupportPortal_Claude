from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from application.inventory_order_alert.infrastructure.persistence.summary_repository import load_latest_summary
from application.inventory_order_alert.infrastructure.persistence.summary_row_codec import (
    row_to_storable,
)
from application.inventory_order_alert.infrastructure.persistence.summary_snapshot_repository import store_summary_snapshot
from application.inventory_order_alert.models import ConfirmationStatus, InventoryOrderAlertConfirmation
from application.inventory_order_alert.models import InventoryOrderAlertSummarySnapshot, SlimsStockImport


def _sample_row() -> dict[str, object]:
    return {
        "cust_code": "100",
        "cust_name": "テスト得意先",
        "item_cd": "43522-D1020-00",
        "level1_item_cd": "43522-D1020-00",
        "level1_vend_cd": "9209",
        "level1_vend_name": "仕入先",
        "last_incoming_date": "",
        "last_ship_date": "2026/06/15",
        "post_shipment_count": 1,
        "post_shipment_total_qty": 250,
        "stock_qty": Decimal("100"),
        "stock_location_summary": "2D0-03-5",
        "stock_location_detail": "2D0-03-5=100",
        "stock_as_of_label": "2026年6月17日時点の在庫",
        "mari_stock_qty": 95,
        "confirmation_status": "未確認",
    }


def _legacy_row() -> dict[str, object]:
    """本機能の導入前に作られたスナップショットの行（MARI 在庫のキーが無い）。"""
    row = _sample_row()
    del row["mari_stock_qty"]
    return row


@pytest.mark.django_db
def test_row_to_storable_serializes_decimal():
    stored = row_to_storable(_sample_row())
    assert stored["stock_qty"] == "100"


@pytest.mark.django_db
def test_store_and_load_latest_summary():
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=3)
    rows = [_sample_row()]
    store_summary_snapshot(import_record, rows, as_of_date=date(2026, 6, 17))

    summary = load_latest_summary()
    assert summary is not None
    assert summary.total_count == 1
    assert summary.critical_count == 1
    assert summary.rows[0]["flow_quadrant"] == "供給リスク品"
    assert summary.rows[0]["item_cd"] == "43522-D1020-00"
    assert summary.stock_info is not None
    assert summary.stock_info.file_name == "sample.csv"


@pytest.mark.django_db
def test_snapshot_roundtrip_keeps_mari_stock_qty():
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_row()], as_of_date=date(2026, 6, 17))

    summary = load_latest_summary()

    assert summary.rows[0]["mari_stock_qty"] == 95


@pytest.mark.django_db
def test_snapshot_roundtrip_keeps_zero_mari_stock_qty():
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(
        import_record, [_sample_row() | {"mari_stock_qty": 0}], as_of_date=date(2026, 6, 17)
    )

    summary = load_latest_summary()

    # 在庫 0 は空にしない
    assert summary.rows[0]["mari_stock_qty"] == 0


@pytest.mark.django_db
def test_legacy_snapshot_row_has_no_mari_stock_key():
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_legacy_row()], as_of_date=date(2026, 6, 17))

    summary = load_latest_summary()

    # キーを作らないことで「未取得」を保つ。None や空で埋めると「該当なし」と区別できなくなる
    assert "mari_stock_qty" not in summary.rows[0]


@pytest.mark.django_db
def test_legacy_snapshot_does_not_raise_on_load():
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_legacy_row()], as_of_date=date(2026, 6, 17))

    summary = load_latest_summary()

    assert summary is not None
    assert summary.rows[0]["item_cd"] == "43522-D1020-00"


@pytest.mark.django_db
def test_TC_SHC_I_007_snapshot_roundtrip_keeps_shipment_trend():
    row = _sample_row() | {
        "shipment_trend": [{"month": "2026-06", "qty": 120}, {"month": "2026-05", "qty": 0}],
    }
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [row], as_of_date=date(2026, 6, 17))

    summary = load_latest_summary()

    trend = summary.rows[0]["shipment_trend"]
    assert len(trend) == 2
    assert trend[0] == {"month": "2026-06", "qty": 120}
    # int のまま復元される（Decimal 化されない）
    assert isinstance(trend[0]["qty"], int)


@pytest.mark.django_db
def test_TC_SHC_I_008_legacy_snapshot_without_shipment_trend_does_not_raise():
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_legacy_row()], as_of_date=date(2026, 6, 17))

    summary = load_latest_summary()

    assert summary is not None
    assert summary.rows[0].get("shipment_trend") is None


@pytest.mark.django_db
def test_snapshot_schema_has_no_new_column():
    columns = {field.name for field in InventoryOrderAlertSummarySnapshot._meta.get_fields()}

    # MARI 在庫は rows(JSONField) の要素に持たせる。カラムは増やさない
    assert "mari_stock_qty" not in columns


@pytest.mark.django_db
def test_load_latest_summary_refreshes_confirmation_status():
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_row()], as_of_date=date(2026, 6, 17))
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="100",
        item_cd="43522-D1020-00",
        status=ConfirmationStatus.CONFIRMED,
        confirmed_by="10001",
    )

    summary = load_latest_summary()
    assert summary is not None
    assert summary.rows[0]["confirmation_status"] == "確認済み"


@pytest.mark.django_db
def test_load_latest_summary_returns_aggregation_error():
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    InventoryOrderAlertSummarySnapshot.objects.create(
        import_record=import_record,
        as_of_date=date(2026, 6, 17),
        rows=[],
        aggregation_error="Oracle 接続失敗",
    )

    summary = load_latest_summary()
    assert summary is not None
    assert summary.aggregation_error == "Oracle 接続失敗"
    assert summary.rows == []
