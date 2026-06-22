from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.inventory_order_alert.application.confirmation_save_result import build_confirmation_save_result
from apps.inventory_order_alert.application.list_filter import ListFilterParams
from apps.inventory_order_alert.application.memo_history import add_confirmation_memo, parse_memo_entry_payload
from apps.inventory_order_alert.application.save_confirmation import ConfirmationInput, save_confirmation
from apps.inventory_order_alert.application.summary_storage import store_summary_snapshot
from apps.inventory_order_alert.models import ConfirmationStatus, SlimsStockImport
from apps.portal.models import PortalMenuGroupAccess


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
        "alert_level": "重点",
        "confirmation_status": "未確認",
        "last_incoming_date": "",
        "last_ship_date": "2026/06/10",
        "post_shipment_count": 2,
    }
    row.update(overrides)
    return row


@pytest.mark.django_db
def test_build_confirmation_save_result_returns_row_class_and_counts(production_user):
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=2)
    store_summary_snapshot(
        import_record,
        [
            _sample_row(),
            _sample_row(cust_code="112", item_cd="ITEM-B", last_incoming_date="2024/05/01", last_ship_date="", post_shipment_count=0),
        ],
        as_of_date=date(2026, 6, 17),
    )
    input_data = ConfirmationInput(
        cust_code="112",
        item_cd="ITEM-A",
        status=ConfirmationStatus.CONFIRMED,
    )
    save_confirmation(input_data, confirmed_by=production_user.username)

    result = build_confirmation_save_result(input_data, filter_params=ListFilterParams())

    assert result["ok"] is True
    assert result["confirmationStatusKey"] == ConfirmationStatus.CONFIRMED
    assert result["alertRowClass"] == "確認済"
    assert result["counts"]["critical"] == 1
    assert result["counts"]["warningIncoming"] == 1
    assert result["counts"]["unconfirmed"] == 1
