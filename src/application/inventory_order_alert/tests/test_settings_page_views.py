from __future__ import annotations

import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from application.inventory_order_alert.models import InventoryOrderAlertSettings
from application.portal.models import PortalMenuGroupAccess


@pytest.fixture
def admin_user(db):
    user = get_user_model().objects.create_user(username="10002", last_name="生産", first_name="担当")
    admin_group, _ = Group.objects.get_or_create(name="管理者")
    user.groups.add(admin_group)
    PortalMenuGroupAccess.objects.get_or_create(user=user, group_key="production")
    return user


@pytest.fixture
def general_user(db):
    """管理者ではないが、在庫発注アラートのメニューにはアクセスできる利用者。"""
    user = get_user_model().objects.create_user(username="10003", last_name="一般", first_name="利用者")
    PortalMenuGroupAccess.objects.get_or_create(user=user, group_key="production")
    return user


SETTINGS_PAGE_URL = "/app/production/inventory-order-alert/settings"
SETTINGS_API_URL = "/api/inventory-order-alert/settings"


# --- 設定画面 SCR-02（§4.2） -------------------------------------------------


@pytest.mark.django_db
def test_settings_page_shows_current_values_for_admin(client, admin_user):
    InventoryOrderAlertSettings.objects.update_or_create(
        pk=1,
        defaults={"warning_days": 730, "stock_stale_days": 14},
    )
    client.force_login(admin_user)

    response = client.get(SETTINGS_PAGE_URL)
    html = response.content.decode("utf-8")

    assert response.status_code == 200
    assert 'value="730"' in html
    assert 'value="14"' in html


@pytest.mark.django_db
def test_settings_page_shows_confirmation_reset_button(client, admin_user):
    """確認状態リセットは一覧画面から設定画面（SCR-02）へ移した。"""
    client.force_login(admin_user)

    html = client.get(SETTINGS_PAGE_URL).content.decode("utf-8")

    assert 'id="ioa-settings-reset-confirmations"' in html
    assert "確認状態のリセット" in html
    assert "/api/inventory-order-alert/confirmation/reset" in html


@pytest.mark.django_db
def test_settings_page_disables_reset_button_when_nothing_to_reset(client, admin_user):
    client.force_login(admin_user)

    html = client.get(SETTINGS_PAGE_URL).content.decode("utf-8")

    reset_pos = html.index('id="ioa-settings-reset-confirmations"')
    tag_end = html.index(">", reset_pos)
    assert "disabled" in html[reset_pos:tag_end]


@pytest.mark.django_db
def test_settings_page_enables_reset_button_when_resettable_confirmations_exist(client, admin_user):
    from application.inventory_order_alert.models import ConfirmationStatus, InventoryOrderAlertConfirmation

    InventoryOrderAlertConfirmation.objects.create(
        cust_code="112", item_cd="ITEM-A", status=ConfirmationStatus.IN_PROGRESS,
    )
    client.force_login(admin_user)

    html = client.get(SETTINGS_PAGE_URL).content.decode("utf-8")

    reset_pos = html.index('id="ioa-settings-reset-confirmations"')
    tag_end = html.index(">", reset_pos)
    assert "disabled" not in html[reset_pos:tag_end]


@pytest.mark.django_db
def test_settings_page_has_no_warning_month_inputs(client, admin_user):
    client.force_login(admin_user)

    html = client.get(SETTINGS_PAGE_URL).content.decode("utf-8")

    # 警告条件の入力欄と保存経路は撤去した（design.md §6.5）。
    assert "warningShipmentMonths" not in html
    assert "warningIncomingMonths" not in html
    assert "criticalEnabled" not in html
    assert "/api/inventory-order-alert/alert-settings" not in html
    assert "stockStaleDays" in html


@pytest.mark.django_db
def test_settings_page_rejects_general_user(client, general_user):
    client.force_login(general_user)
    response = client.get(SETTINGS_PAGE_URL)

    assert response.status_code == 403


@pytest.mark.django_db
def test_settings_page_requires_login(client):
    response = client.get(SETTINGS_PAGE_URL)

    assert response.status_code in (302, 403)


# --- 設定 API（§8.10） -------------------------------------------------------


@pytest.mark.django_db
def test_api_settings_get_returns_current_settings(client, admin_user):
    client.force_login(admin_user)
    payload = client.get(SETTINGS_API_URL).json()

    assert payload["ok"] is True
    assert set(payload["settings"]) == {"warningDays", "stockStaleDays"}


@pytest.mark.django_db
def test_api_settings_put_updates_and_persists(client, admin_user):
    client.force_login(admin_user)
    response = client.put(
        SETTINGS_API_URL,
        data=json.dumps({"stockStaleDays": 21}),
        content_type="application/json",
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["settings"]["stockStaleDays"] == 21

    settings_row = InventoryOrderAlertSettings.objects.get(pk=1)
    assert settings_row.stock_stale_days == 21
    assert settings_row.updated_by_id == admin_user.pk


@pytest.mark.django_db
def test_api_settings_put_leaves_legacy_columns_untouched(client, admin_user):
    # 残置カラムは保存経路から外れており、値が書き換わらない（design.md §5.3）。
    InventoryOrderAlertSettings.objects.update_or_create(
        pk=1, defaults={"warning_shipment_months": 6, "warning_incoming_months": 18}
    )
    client.force_login(admin_user)
    payload = client.put(
        SETTINGS_API_URL,
        data=json.dumps({"stockStaleDays": 30}),
        content_type="application/json",
    ).json()

    assert payload["settings"]["stockStaleDays"] == 30
    settings_row = InventoryOrderAlertSettings.objects.get(pk=1)
    assert settings_row.warning_shipment_months == 6
    assert settings_row.warning_incoming_months == 18


@pytest.mark.django_db
def test_api_settings_put_rejects_out_of_range_value(client, admin_user):
    client.force_login(admin_user)
    response = client.put(
        SETTINGS_API_URL,
        data=json.dumps({"stockStaleDays": 0}),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["ok"] is False


@pytest.mark.django_db
def test_api_settings_put_rejects_broken_json(client, admin_user):
    client.force_login(admin_user)
    response = client.put(SETTINGS_API_URL, data="{", content_type="application/json")

    assert response.status_code == 400
    assert response.json()["ok"] is False


@pytest.mark.django_db
def test_api_settings_rejects_general_user(client, general_user):
    client.force_login(general_user)

    get_response = client.get(SETTINGS_API_URL)
    put_response = client.put(
        SETTINGS_API_URL,
        data=json.dumps({"stockStaleDays": 30}),
        content_type="application/json",
    )

    assert get_response.status_code == 403
    assert put_response.status_code == 403
    assert get_response.json()["ok"] is False
    assert InventoryOrderAlertSettings.objects.filter(pk=1).count() == 0


@pytest.mark.django_db
def test_api_settings_rejects_post(client, admin_user):
    client.force_login(admin_user)
    response = client.post(SETTINGS_API_URL, data="{}", content_type="application/json")

    assert response.status_code == 405


LIST_PAGE_URL = "/app/production/inventory-order-alert"


@pytest.mark.django_db
def test_list_page_shows_settings_link_for_admin(client, admin_user):
    """設定画面 SCR-02（§4.2）への導線は管理者に表示する。"""
    client.force_login(admin_user)

    response = client.get(LIST_PAGE_URL)

    assert response.status_code == 200
    assert SETTINGS_PAGE_URL in response.content.decode("utf-8")


@pytest.mark.django_db
def test_list_page_hides_settings_link_from_general_user(client, general_user):
    """管理者以外には設定画面への導線を表示しない（開いても 403 になるため）。"""
    client.force_login(general_user)

    response = client.get(LIST_PAGE_URL)

    assert response.status_code == 200
    assert SETTINGS_PAGE_URL not in response.content.decode("utf-8")
