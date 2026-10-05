from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from application.inventory_order_alert.interfaces.wiring import save_confirmation_usecase
from application.inventory_order_alert.infrastructure.persistence.summary_snapshot_repository import store_summary_snapshot
from application.inventory_order_alert.models import (
    ConfirmationStatus,
    InventoryOrderAlertConfirmation,
    SlimsStockImport,
)
from application.portal.models import PortalMenuGroupAccess


@pytest.fixture
def production_user(db):
    user = get_user_model().objects.create_user(username="10002", last_name="生産", first_name="担当")
    admin_group, _ = Group.objects.get_or_create(name="管理者")
    user.groups.add(admin_group)
    PortalMenuGroupAccess.objects.get_or_create(user=user, group_key="production")
    return user


def _sample_row(**overrides):
    row = {
        "cust_code": "112",
        "item_cd": "ITEM-A",
        "confirmation_status": "未確認",
        "last_incoming_date": "",
        "last_ship_date": "2026/06/10",
        "post_shipment_count": 2,
    }
    row.update(overrides)
    return row


@pytest.mark.django_db
def test_save_confirmation_usecase_returns_row_class_and_counts(production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=2)
    store_summary_snapshot(
        import_record,
        [
            _sample_row(),
            _sample_row(
                cust_code="112",
                item_cd="ITEM-B",
                last_incoming_date="2024/05/01",
                last_ship_date="",
                post_shipment_count=0,
            ),
        ],
        as_of_date=date(2026, 6, 17),
    )
    result = save_confirmation_usecase().execute(
        {
            "custCode": "112",
            "itemCd": "ITEM-A",
            "status": "confirmed",
        },
        confirmed_by=production_user.username,
    )

    assert result["ok"] is True
    assert result["confirmationStatusKey"] == ConfirmationStatus.CONFIRMED
    assert result["alertRowClass"] == "確認済"
    assert result["counts"]["lowFlowNoIncoming"] == 1
    assert result["counts"]["dormantStock"] == 1
    assert result["counts"]["attention"] == 2
    assert result["counts"]["unconfirmed"] == 1
    assert result["counts"]["confirmed"] == 1


@pytest.mark.django_db
def test_save_confirmation_records_flow_quadrant_from_reference_selection(production_user):
    """一覧で判定期間 5 年を選択中でも、保存される流動区分は既定の 1 年基準（05 design §6.5）。"""
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [_sample_row()], as_of_date=date(2026, 6, 17))

    save_confirmation_usecase().execute(
        {
            "custCode": "112",
            "itemCd": "ITEM-A",
            "status": "confirmed",
            "period": "5",
        },
        confirmed_by=production_user.username,
    )

    confirmation = InventoryOrderAlertConfirmation.objects.get(cust_code="112", item_cd="ITEM-A")
    assert confirmation.confirmed_flow_quadrant == "低流動品（入荷なし）"
