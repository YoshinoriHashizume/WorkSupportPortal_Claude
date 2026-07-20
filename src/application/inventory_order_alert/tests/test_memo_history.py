from __future__ import annotations

from datetime import date, datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

from application.inventory_order_alert.domain.value_objects.confirmation import (
    format_memo_history_csv,
    parse_memo_entry_payload,
)
from application.inventory_order_alert.domain.value_objects.confirmation import MemoEntryRecord
from application.inventory_order_alert.infrastructure.persistence.confirmation_repository import (
    add_confirmation_memo,
    list_confirmation_memos,
)
from application.inventory_order_alert.models import (
    ConfirmationStatus,
    InventoryOrderAlertConfirmation,
)
from application.portal.models import PortalMenuGroupAccess


@pytest.fixture
def production_user(db):
    user = get_user_model().objects.create_user(username="10002", last_name="生産", first_name="担当")
    admin_group, _ = Group.objects.get_or_create(name="管理者")
    user.groups.add(admin_group)
    PortalMenuGroupAccess.objects.get_or_create(user=user, group_key="production")
    return user


def test_parse_memo_entry_payload_requires_content():
    with pytest.raises(ValueError, match="メモ内容"):
        parse_memo_entry_payload({"custCode": "112", "itemCd": "ITEM-A", "content": "  "})


@pytest.mark.django_db
def test_add_confirmation_memo_appends_history_and_syncs_latest(production_user):
    first = add_confirmation_memo(
        cust_code="112",
        item_cd="ITEM-A",
        content="1件目",
        created_by=production_user.username,
    )
    second = add_confirmation_memo(
        cust_code="112",
        item_cd="ITEM-A",
        content="2件目",
        created_by=production_user.username,
    )

    memos = list_confirmation_memos(cust_code="112", item_cd="ITEM-A")
    assert len(memos) == 2
    assert memos[0]["content"] == "2件目"
    assert memos[1]["content"] == "1件目"
    assert memos[0]["createdBy"] == "生産担当"

    confirmation = InventoryOrderAlertConfirmation.objects.get(cust_code="112", item_cd="ITEM-A")
    assert confirmation.memo == "2件目"
    assert confirmation.status == ConfirmationStatus.UNCONFIRMED
    assert first.created_at <= second.created_at


@pytest.mark.django_db
def test_format_memo_history_csv_joins_entries_newest_first():
    entry1 = MemoEntryRecord(
        created_at=timezone.make_aware(datetime(2026, 6, 19, 10, 30)),
        created_by="10001",
        content="回答待ち",
    )
    entry2 = MemoEntryRecord(
        created_at=timezone.make_aware(datetime(2026, 6, 19, 11, 0)),
        created_by="10002",
        content="発注可",
    )

    history = format_memo_history_csv(
        [entry2, entry1],
        author_names={"10001": "確認担当", "10002": "登録担当"},
    )
    assert history.startswith("2026/06/19 11:00 登録担当: 発注可")
    assert history.endswith("2026/06/19 10:30 確認担当: 回答待ち")
    assert " | " in history


@pytest.mark.django_db
def test_api_list_and_add_confirmation_memos(client, production_user):
    client.force_login(production_user)
    list_response = client.get(
        "/api/inventory-order-alert/confirmation/memos",
        {"custCode": "112", "itemCd": "ITEM-A"},
    )
    assert list_response.status_code == 200
    assert list_response.json()["memos"] == []

    add_response = client.post(
        "/api/inventory-order-alert/confirmation/memos",
        data='{"custCode":"112","itemCd":"ITEM-A","content":"仕入先確認済み"}',
        content_type="application/json",
    )
    payload = add_response.json()
    assert add_response.status_code == 200
    assert payload["ok"] is True
    assert payload["memo"]["content"] == "仕入先確認済み"
    assert payload["memo"]["createdBy"] == "生産担当"

    list_response = client.get(
        "/api/inventory-order-alert/confirmation/memos",
        {"custCode": "112", "itemCd": "ITEM-A"},
    )
    assert len(list_response.json()["memos"]) == 1
