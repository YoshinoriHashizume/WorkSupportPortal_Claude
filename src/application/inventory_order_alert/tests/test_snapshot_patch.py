from __future__ import annotations

from datetime import date

import pytest
from django.utils import timezone

from application.inventory_order_alert.interfaces.wiring import patch_snapshot_row_usecase
from application.inventory_order_alert.domain.value_objects.alert_level import ALERT_NONE, ALERT_WARNING_SHIP
from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings
from application.inventory_order_alert.domain.value_objects.snapshot_patch import parse_patch_date
from application.inventory_order_alert.infrastructure.persistence.summary_snapshot_repository import store_summary_snapshot
from application.inventory_order_alert.models import ConfirmationStatus, InventoryOrderAlertConfirmation
from application.inventory_order_alert.models import SlimsStockImport


def _sample_row(**overrides: object) -> dict[str, object]:
    return {
        "cust_code": "100",
        "cust_name": "テスト得意先",
        "item_cd": "90249-14011",
        "last_incoming_date": "2024/01/15",
        "last_ship_date": "2024/06/01",
        "post_shipment_count": 0,
        "post_shipment_total_qty": 0,
        "alert_level": ALERT_NONE,
        **overrides,
    }


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("today", date(2026, 6, 19)),
        ("今日", date(2026, 6, 19)),
        ("2026/06/19", date(2026, 6, 19)),
        ("20260619", date(2026, 6, 19)),
    ],
)
def test_parse_patch_date(value, expected):
    assert parse_patch_date(value, today=date(2026, 6, 19)) == expected


@pytest.mark.django_db
def test_patch_snapshot_row_updates_last_ship_date_and_alert_level(monkeypatch):
    monkeypatch.setattr(timezone, "localdate", lambda: date(2026, 6, 19))
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_row()], as_of_date=date(2026, 6, 19))

    result = patch_snapshot_row_usecase().execute(
        cust_code="100",
        item_cd="90249-14011",
        last_ship_date=date(2026, 6, 19),
        post_shipment_count=2,
        app_settings=AppSettings(),
    )

    assert result.previous_last_ship_date == "2024/06/01"
    assert result.new_last_ship_date == "2026/06/19"
    assert result.previous_alert_level == ALERT_NONE
    assert result.new_alert_level == ALERT_WARNING_SHIP


@pytest.mark.django_db
def test_patch_snapshot_row_can_run_reconcile(monkeypatch):
    monkeypatch.setattr(timezone, "localdate", lambda: date(2026, 6, 19))
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_row()], as_of_date=date(2026, 6, 19))
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="100",
        item_cd="90249-14011",
        status=ConfirmationStatus.CONFIRMED,
        confirmed_alert_level=ALERT_NONE,
        confirmed_by="10001",
    )

    result = patch_snapshot_row_usecase().execute(
        cust_code="100",
        item_cd="90249-14011",
        last_ship_date=date(2026, 6, 19),
        post_shipment_count=2,
        run_reconcile=True,
        app_settings=AppSettings(),
    )

    confirmation = InventoryOrderAlertConfirmation.objects.get(cust_code="100", item_cd="90249-14011")
    assert result.confirmation_reset_count == 1
    assert confirmation.status == ConfirmationStatus.UNCONFIRMED
