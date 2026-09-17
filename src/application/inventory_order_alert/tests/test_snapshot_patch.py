from __future__ import annotations

from datetime import date

import pytest
from django.utils import timezone

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_INCOMING,
)
from application.inventory_order_alert.domain.value_objects.snapshot_patch import parse_patch_date
from application.inventory_order_alert.infrastructure.persistence.summary_snapshot_repository import store_summary_snapshot
from application.inventory_order_alert.interfaces.wiring import patch_snapshot_row_usecase
from application.inventory_order_alert.models import (
    ConfirmationStatus,
    InventoryOrderAlertConfirmation,
    SlimsStockImport,
)

AS_OF = date(2026, 6, 19)


def _sample_row(**overrides: object) -> dict[str, object]:
    return {
        "cust_code": "100",
        "cust_name": "テスト得意先",
        "item_cd": "90249-14011",
        "last_incoming_date": "2024/01/15",
        "last_ship_date": "2024/06/01",
        "post_shipment_count": 0,
        "post_shipment_total_qty": 0,
        **overrides,
    }


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("today", AS_OF),
        ("今日", AS_OF),
        ("2026/06/19", AS_OF),
        ("20260619", AS_OF),
    ],
)
def test_parse_patch_date(value, expected):
    assert parse_patch_date(value, today=AS_OF) == expected


@pytest.mark.django_db
def test_patch_snapshot_row_applies_flow_quadrant_with_reference_selection(monkeypatch):
    monkeypatch.setattr(timezone, "localdate", lambda: AS_OF)
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_row()], as_of_date=AS_OF)

    result = patch_snapshot_row_usecase().execute(
        cust_code="100",
        item_cd="90249-14011",
        last_ship_date=AS_OF,
        post_shipment_count=2,
    )

    # 基準判定条件（低流動判定軸・3か月）で判定される。
    assert result.previous_last_ship_date == "2024/06/01"
    assert result.new_last_ship_date == "2026/06/19"
    assert result.previous_flow_quadrant == QUADRANT_DORMANT_STOCK
    assert result.new_flow_quadrant == QUADRANT_LOW_FLOW_NO_INCOMING


@pytest.mark.django_db
def test_patch_snapshot_row_can_run_reconcile(monkeypatch):
    monkeypatch.setattr(timezone, "localdate", lambda: AS_OF)
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_row()], as_of_date=AS_OF)
    InventoryOrderAlertConfirmation.objects.create(
        cust_code="100",
        item_cd="90249-14011",
        status=ConfirmationStatus.CONFIRMED,
        confirmed_flow_quadrant=QUADRANT_DORMANT_STOCK,
        confirmed_by="10001",
    )

    result = patch_snapshot_row_usecase().execute(
        cust_code="100",
        item_cd="90249-14011",
        last_ship_date=AS_OF,
        post_shipment_count=2,
        run_reconcile=True,
    )

    confirmation = InventoryOrderAlertConfirmation.objects.get(cust_code="100", item_cd="90249-14011")
    assert result.confirmation_reset_count == 1
    assert confirmation.status == ConfirmationStatus.UNCONFIRMED
