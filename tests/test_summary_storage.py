from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.inventory_order_alert.application.summary_storage import (
    load_latest_summary,
    row_to_storable,
    store_summary_snapshot,
)
from apps.inventory_order_alert.models import ConfirmationStatus, InventoryOrderAlertConfirmation
from apps.inventory_order_alert.models import InventoryOrderAlertSummarySnapshot, SlimsStockImport


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
        "alert_level": "重点",
        "confirmation_status": "未確認",
    }


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
    assert summary.rows[0]["alert_level"] == "重点"
    assert summary.rows[0]["item_cd"] == "43522-D1020-00"
    assert summary.stock_info is not None
    assert summary.stock_info.file_name == "sample.csv"


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
