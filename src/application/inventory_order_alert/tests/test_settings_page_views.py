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


# --- 07 第 2 段階: 直近入荷の日数（REQ-FQR-F-008） ---------------------------


@pytest.mark.django_db
def test_fqr_f008_settings_page_shows_recent_incoming_days(client, admin_user):
    InventoryOrderAlertSettings.objects.update_or_create(pk=1, defaults={"recent_incoming_days": 45})
    client.force_login(admin_user)

    html = client.get(SETTINGS_PAGE_URL).content.decode("utf-8")

    assert 'id="ioa-setting-recent-incoming-days"' in html
    assert 'name="recentIncomingDays"' in html
    assert 'value="45"' in html
    assert 'min="1" max="90"' in html
    # 判定期間（一覧で切り替え）と混同しないよう用途を書く
    assert "一覧で切り替える判定期間とは別の設定です" in html


@pytest.mark.django_db
def test_fqr_f008_api_settings_put_updates_recent_incoming_days(client, admin_user):
    client.force_login(admin_user)

    response = client.put(
        SETTINGS_API_URL,
        data=json.dumps({"recentIncomingDays": 60}),
        content_type="application/json",
    )

    assert response.json()["settings"]["recentIncomingDays"] == 60
    assert InventoryOrderAlertSettings.objects.get(pk=1).recent_incoming_days == 60


@pytest.mark.django_db
def test_fqr_f008_api_settings_rejects_out_of_range_recent_incoming_days(client, admin_user):
    client.force_login(admin_user)

    response = client.put(
        SETTINGS_API_URL,
        data=json.dumps({"recentIncomingDays": 91}),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert InventoryOrderAlertSettings.objects.get(pk=1).recent_incoming_days == 30


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
    assert set(payload["settings"]) == {
        "warningDays",
        "stockStaleDays",
        "defaultLeadTimeDays",
        "recentIncomingDays",
        # 11 TC-JS-A-003
        "judgementHorizonDays",
        "staleOrderDays",
        # 12 TC-DSE-V-004
        "directShipmentSupplierCodes",
    }


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


# --- spec/12 TC-DSE-V-001〜010: 直送仕入先（V-240） ------------------------------

from application.inventory_order_alert.domain.value_objects.errors import VendorLookupUnavailableError  # noqa: E402
from application.inventory_order_alert.interfaces import wiring  # noqa: E402

DSE_NAMES = {"9100": "丸栄豊田", "9200": "テクノス工場", "9250": "丸栄豊田（福岡）"}


def _dse_lookup(monkeypatch, names=None, *, unavailable=False):
    def lookup(codes):
        if unavailable:
            raise VendorLookupUnavailableError()
        return {code: name for code, name in (names or {}).items() if code in codes}

    monkeypatch.setattr(wiring, "lookup_vendor_names", lookup)


def _dse_codes() -> list[str]:
    row, _ = InventoryOrderAlertSettings.objects.get_or_create(pk=1)
    return row.direct_shipment_supplier_codes


@pytest.mark.django_db
def test_dse_v001_settings_page_shows_direct_suppliers_with_names(client, admin_user, monkeypatch):
    _dse_lookup(monkeypatch, DSE_NAMES)
    client.force_login(admin_user)

    response = client.get(SETTINGS_PAGE_URL)
    html = response.content.decode("utf-8")

    assert response.status_code == 200
    assert "直送仕入先" in html
    for code, name in DSE_NAMES.items():
        assert f'data-code="{code}"' in html
        assert name in html
    assert "次回の SLIMS 在庫 CSV 取込から反映" in html


@pytest.mark.django_db
def test_dse_v002_settings_page_opens_when_vendor_master_is_unavailable(client, admin_user, monkeypatch):
    _dse_lookup(monkeypatch, unavailable=True)
    client.force_login(admin_user)

    response = client.get(SETTINGS_PAGE_URL)

    assert response.status_code == 200
    assert "（仕入先名を取得できません）" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_dse_v003_settings_page_marks_code_missing_from_vendor_master(client, admin_user, monkeypatch):
    InventoryOrderAlertSettings.objects.update_or_create(pk=1, defaults={"direct_shipment_supplier_codes": ["8888"]})
    _dse_lookup(monkeypatch, {})
    client.force_login(admin_user)

    html = client.get(SETTINGS_PAGE_URL).content.decode("utf-8")

    assert "（仕入先マスタに見つかりません）" in html


@pytest.mark.django_db
def test_dse_v004_api_get_includes_direct_supplier_codes_and_names(client, admin_user, monkeypatch):
    _dse_lookup(monkeypatch, DSE_NAMES)
    client.force_login(admin_user)

    payload = client.get(SETTINGS_API_URL).json()

    assert payload["settings"]["directShipmentSupplierCodes"] == ["9100", "9200", "9250"]
    assert payload["directShipmentSuppliers"][0] == {"code": "9100", "name": "丸栄豊田", "status": "found"}


@pytest.mark.django_db
def test_dse_v005_api_put_saves_direct_suppliers(client, admin_user, monkeypatch):
    _dse_lookup(monkeypatch, DSE_NAMES)
    client.force_login(admin_user)

    response = client.put(
        SETTINGS_API_URL,
        data=json.dumps({"directShipmentSupplierCodes": ["9100", "9250"]}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["settings"]["directShipmentSupplierCodes"] == ["9100", "9250"]
    assert client.get(SETTINGS_API_URL).json()["settings"]["directShipmentSupplierCodes"] == ["9100", "9250"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("codes", "message"),
    [
        (["9100", "9100"], "直送仕入先に同じ仕入先コードが重複しています: 9100"),
        ([""], "直送仕入先に空の仕入先コードは登録できません。"),
        ("9100", "直送仕入先は仕入先コードの配列で指定してください。"),
    ],
)
def test_dse_v006_invalid_direct_suppliers_are_400(client, admin_user, monkeypatch, codes, message):
    _dse_lookup(monkeypatch, DSE_NAMES)
    client.force_login(admin_user)

    response = client.put(
        SETTINGS_API_URL,
        data=json.dumps({"directShipmentSupplierCodes": codes}),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["message"] == message
    assert _dse_codes() == ["9100", "9200", "9250"]


@pytest.mark.django_db
def test_dse_v007_unknown_vendor_code_is_400(client, admin_user, monkeypatch):
    _dse_lookup(monkeypatch, {})
    client.force_login(admin_user)

    response = client.put(
        SETTINGS_API_URL,
        data=json.dumps({"directShipmentSupplierCodes": ["9999"]}),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["message"] == "仕入先マスタに存在しない仕入先コードです: 9999"


@pytest.mark.django_db
def test_dse_v008_unavailable_vendor_master_is_503_and_nothing_saved(client, admin_user, monkeypatch):
    _dse_lookup(monkeypatch, unavailable=True)
    client.force_login(admin_user)

    response = client.put(
        SETTINGS_API_URL,
        data=json.dumps({"warningDays": 100, "directShipmentSupplierCodes": ["9100", "9999"]}),
        content_type="application/json",
    )

    assert response.status_code == 503
    assert response.json()["message"].startswith("基幹に接続できないため")
    row = InventoryOrderAlertSettings.objects.get(pk=1)
    assert row.direct_shipment_supplier_codes == ["9100", "9200", "9250"]
    assert row.warning_days == 365


@pytest.mark.django_db
def test_dse_v009_general_user_cannot_use_direct_supplier_settings(client, general_user, monkeypatch):
    _dse_lookup(monkeypatch, DSE_NAMES)
    client.force_login(general_user)

    assert client.get(SETTINGS_PAGE_URL).status_code == 403
    assert client.get(SETTINGS_API_URL).status_code == 403
    response = client.put(
        SETTINGS_API_URL,
        data=json.dumps({"directShipmentSupplierCodes": []}),
        content_type="application/json",
    )
    assert response.status_code == 403
    assert _dse_codes() == ["9100", "9200", "9250"]


@pytest.mark.django_db
def test_dse_v010_snapshot_stored_before_this_feature_shows_all_rows(client, admin_user):
    from application.inventory_order_alert.models import InventoryOrderAlertSummarySnapshot, SlimsStockImport

    import_record = SlimsStockImport.objects.create(file_name="old.csv", row_count=1)
    InventoryOrderAlertSummarySnapshot.objects.create(
        import_record=import_record,
        as_of_date=import_record.imported_at.date(),
        rows=[
            {
                "cust_code": "308",
                "item_cd": "15D126-0020",
                "level1_item_cd": "15D126-0020-9100",
                "level1_vend_cd": "9100",
                "stock_qty": "",
                "flow_quadrant": "打ち切り候補",
            }
        ],
        total_count=1,
    )
    client.force_login(admin_user)

    response = client.get("/api/inventory-order-alert/summary")

    assert response.status_code == 200
    assert [row["item_cd"] for row in response.json()["rows"]] == ["15D126-0020"]
