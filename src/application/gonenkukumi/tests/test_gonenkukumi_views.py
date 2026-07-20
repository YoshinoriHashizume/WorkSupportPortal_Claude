import json
import re
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

from application.gonenkukumi.domain.value_objects.errors import OracleQueryError
from application.gonenkukumi.models import GonenKukumiSearchHistory
from application.portal.models import PortalMenuGroupAccess, UserFavoriteMenu


@pytest.fixture
def user(db):
    user = get_user_model().objects.create_user(username="tester@example.local")
    production_group, _ = Group.objects.get_or_create(name="一般ユーザー")
    user.groups.add(production_group)
    PortalMenuGroupAccess.objects.create(user=user, group_key="production")
    return user


@pytest.fixture(autouse=True)
def oracle_mock(monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")


@pytest.mark.django_db
def test_search_api_requires_login(client):
    response = client.post("/api/gonenkukumi/search", data={}, content_type="application/json")
    assert response.status_code == 401


@pytest.mark.django_db
def test_search_api_saves_history(client, user):
    client.force_login(user)
    response = client.post(
        "/api/gonenkukumi/search",
        data=json.dumps({"custCode": "101", "custItem": "ITEM-001", "yearMonth": "2026-05", "optionChange": "*"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["result"]["blocks"][0]["meta"]["teban"] == 1
    assert payload["result"]["blocks"][0]["meta"]["anzen"] == 0

    history_response = client.get("/api/gonenkukumi/history")
    assert history_response.status_code == 200
    assert history_response.json()["histories"][0]["custCode"] == "101"


@pytest.mark.django_db
def test_history_api_returns_latest_per_search_condition(client, user):
    old_history = GonenKukumiSearchHistory.objects.create(
        user=user,
        cust_code="191",
        cust_item="235677-0050",
        option_change="*",
        year_month="2026-05",
    )
    latest_history = GonenKukumiSearchHistory.objects.create(
        user=user,
        cust_code="191",
        cust_item="235677-0050",
        option_change="*",
        year_month="2026-05",
    )
    other_history = GonenKukumiSearchHistory.objects.create(
        user=user,
        cust_code="191",
        cust_item="235677-0050",
        option_change="A1",
        year_month="2026-05",
    )

    client.force_login(user)
    response = client.get("/api/gonenkukumi/history")

    assert response.status_code == 200
    histories = response.json()["histories"]
    ids = [item["id"] for item in histories]
    assert str(latest_history.id) in ids
    assert str(old_history.id) not in ids
    assert str(other_history.id) in ids
    assert len(histories) == 2


@pytest.mark.django_db
def test_search_page_defaults_to_empty_and_current_month(client, user):
    client.force_login(user)
    response = client.get("/app/production/five-year-nine")
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    current_month = timezone.localdate().strftime("%Y-%m")
    current_month_display = current_month.replace("-", "/")
    assert 'name="custCode"' in html
    assert 'class="portal-customer-select portal-customer-select--gonen"' in html
    assert 'data-customers-api="/api/gonenkukumi/customers"' in html
    assert "/static/js/portal-customer-select.js" in html
    assert 'id="customer-name-display"' not in html
    assert ">得意先<" in html
    assert "得意先コード" not in html.split("検索履歴")[0]
    assert 'name="custItem" value=""' in html
    assert f'name="yearMonth"' in html
    assert f'value="{current_month_display}"' in html
    assert 'name="optionChange" value="*"' in html
    assert "品目任意変換値" in html
    assert "設変値" not in html
    assert html.index("得意先品目") < html.index("品目任意変換値") < html.index("検索年月")
    assert 'class="favorite-toggle portal-title-favorite"' in html
    assert 'data-menu-key="five-year-nine"' in html
    assert "♡" in html


@pytest.mark.django_db
def test_search_page_shows_favorite_button_as_active(client, user):
    UserFavoriteMenu.objects.create(user=user, menu_key="five-year-nine", sort_order=0)
    client.force_login(user)

    response = client.get("/app/production/five-year-nine")

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert 'class="favorite-toggle portal-title-favorite is-favorite"' in html
    assert "♥" in html


@pytest.mark.django_db
def test_search_page_defaults_to_latest_history(client, user):
    GonenKukumiSearchHistory.objects.create(
        user=user,
        cust_code="191",
        cust_item="235677-0050",
        option_change="*",
        year_month="2026-05",
    )
    client.force_login(user)
    response = client.get("/app/production/five-year-nine")
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert 'name="custCode"' in html
    assert 'data-selected="191"' in html
    assert 'name="custItem" value="235677-0050"' in html
    assert 'name="yearMonth"' in html
    assert 'value="2026/05"' in html


@pytest.mark.django_db
def test_search_page_shows_mock_notice_when_oracle_mock_enabled(client, user, monkeypatch):
    monkeypatch.setenv("ORACLE_USE_MOCK", "true")
    client.force_login(user)
    response = client.get("/app/production/five-year-nine")
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "Oracle モックモード" in html
    assert "サンプル得意先A" in html


@pytest.mark.django_db
def test_search_page_renders_customer_options_server_side(client, user):
    client.force_login(user)
    response = client.get("/app/production/five-year-nine")
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "101 - サンプル得意先A" in html
    assert 'value="101"' in html
    assert 'data-customers-api="/api/gonenkukumi/customers"' in html


@pytest.mark.django_db
def test_customer_suggestions_match_code_prefix(client, user):
    client.force_login(user)
    preload_response = client.get("/api/gonenkukumi/customers")
    assert preload_response.status_code == 200
    preload_codes = [item["custCode"] for item in preload_response.json()["customers"]]
    assert {"119", "191"}.issubset(set(preload_codes))

    response = client.get("/api/gonenkukumi/customers?q=19")
    assert response.status_code == 200
    codes = [item["custCode"] for item in response.json()["customers"]]
    assert "191" in codes
    assert "119" not in codes


@pytest.mark.django_db
def test_cust_item_suggestions_preload_all_for_customer(client, user):
    client.force_login(user)
    response = client.get("/api/gonenkukumi/cust-items?custCode=101")
    assert response.status_code == 200
    items = [item["custItem"] for item in response.json()["items"]]
    assert items == ["ITEM-001", "ITEM-002"]


@pytest.mark.django_db
def test_search_api_hides_internal_naisak_not_found_code(client, user, monkeypatch):
    def raise_not_found(_params):
        raise OracleQueryError("NAISAK_NOT_FOUND")

    monkeypatch.setattr("application.gonenkukumi.infrastructure.oracle.client.run_gonenkukumi_oracle_search", raise_not_found)
    client.force_login(user)
    response = client.post(
        "/api/gonenkukumi/search",
        data=json.dumps({"custCode": "101", "custItem": "UNKNOWN", "yearMonth": "2026-05", "optionChange": "*"}),
        content_type="application/json",
    )

    assert response.status_code == 404
    message = response.json()["error"]["message"]
    assert "NAISAK_NOT_FOUND" not in message
    assert "内作品番が見つかりません" in message


def fake_monthly_result(params):
    return {
        "success": True,
        "custCode": params.cust_code,
        "customerName": "サンプル得意先A",
        "custItem": params.cust_item,
        "optionChange": params.option_change,
        "yearMonth": params.year_month,
        "asOfDate": params.as_of_date.isoformat(),
        "internalItemCd": "MOCK-ITEM",
        "days": list(range(1, 32)),
        "activeDays": 31,
        "holidayDays": [],
        "blocks": [
            {
                "kind": "customer",
                "label": "得意先 101",
                "theme": {"bg": "#dcfce7", "border": "#86efac", "outerBorder": "#22c55e"},
                "meta": {"custCode": "101", "custItem": "ITEM-001", "customerName": "サンプル得意先A"},
                "rows": [{"item": "受注", "values": [1 for _ in range(31)], "total": 31, "balance": None}],
            },
            {
                "kind": "supplier",
                "label": "仕入先 V001",
                "theme": {"bg": "#dff5ff", "border": "#93c5fd", "outerBorder": "#3b82f6"},
                "meta": {"kaiso": 1, "itemCd": "PART-001", "vendCd": "V001", "vendName": "サンプル仕入先"},
                "rows": [
                    {"item": "月初発注", "values": [1 for _ in range(31)], "total": 31, "balance": None},
                    {"item": "所要量", "values": [2 for _ in range(31)], "total": 62, "balance": None},
                    {"item": "確定発注", "values": [3 for _ in range(31)], "total": 93, "balance": None},
                    {"item": "入荷実績", "values": [4 for _ in range(31)], "total": 124, "balance": None},
                    {"item": "本日在庫", "values": [5 for _ in range(31)], "total": 155, "balance": None},
                ],
            },
        ],
    }


@pytest.mark.django_db
def test_result_page_initially_shows_base_month_and_add_buttons(client, user, monkeypatch):
    requested_months = []

    def fake_search(params):
        requested_months.append(params.year_month)
        return fake_monthly_result(params)

    monkeypatch.setattr("application.gonenkukumi.infrastructure.oracle.client.run_gonenkukumi_oracle_search", fake_search)
    client.force_login(user)

    response = client.get("/app/production/five-year-nine/result?custCode=101&custItem=ITEM-001&yearMonth=2026-05&optionChange=*")

    assert response.status_code == 200
    assert requested_months == ["2026-05"]
    html = response.content.decode("utf-8")
    assert "前月を追加" in html
    assert "次月を追加" in html
    assert html.count('class="next-month-panel"') == 2
    assert "検索年月 <strong>2026/05</strong>" in html
    assert "検索年月 <strong>2026/05</strong><em>（基準）</em>" not in html
    assert "所要量" in html


@pytest.mark.django_db
def test_result_page_adds_requested_months_inside_each_block(client, user, monkeypatch):
    requested_months = []

    def fake_search(params):
        requested_months.append(params.year_month)
        return fake_monthly_result(params)

    monkeypatch.setattr("application.gonenkukumi.infrastructure.oracle.client.run_gonenkukumi_oracle_search", fake_search)
    client.force_login(user)

    response = client.get(
        "/app/production/five-year-nine/result"
        "?custCode=101&custItem=ITEM-001&yearMonth=2026-05&optionChange=*"
        "&months=2026-04,2026-05,2026-06"
    )

    assert response.status_code == 200
    assert requested_months == ["2026-04", "2026-05", "2026-06"]
    html = response.content.decode("utf-8")
    assert html.count('class="next-month-panel"') == 6
    assert "検索年月 <strong>2026/04</strong><em>（前月）</em>" in html
    assert "検索年月 <strong>2026/05</strong>" in html
    assert "検索年月 <strong>2026/05</strong><em>（基準）</em>" not in html
    assert "検索年月 <strong>2026/06</strong><em>（次月）</em>" in html


@pytest.mark.django_db
def test_result_page_uses_named_adjacent_two_month_labels(client, user, monkeypatch):
    def fake_search(params):
        return fake_monthly_result(params)

    monkeypatch.setattr("application.gonenkukumi.infrastructure.oracle.client.run_gonenkukumi_oracle_search", fake_search)
    client.force_login(user)

    response = client.get(
        "/app/production/five-year-nine/result"
        "?custCode=101&custItem=ITEM-001&yearMonth=2026-05&optionChange=*"
        "&months=2026-02,2026-03,2026-04,2026-05,2026-06,2026-07,2026-08"
    )

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "検索年月 <strong>2026/02</strong><em>（3か月前）</em>" in html
    assert "検索年月 <strong>2026/03</strong><em>（前々月）</em>" in html
    assert "検索年月 <strong>2026/04</strong><em>（前月）</em>" in html
    assert "検索年月 <strong>2026/06</strong><em>（次月）</em>" in html
    assert "検索年月 <strong>2026/07</strong><em>（次々月）</em>" in html
    assert "検索年月 <strong>2026/08</strong><em>（3か月後）</em>" in html


@pytest.mark.django_db
def test_result_page_includes_balance_in_total_and_keeps_stock_out_of_day_one(client, user, monkeypatch):
    def fake_search(params):
        result = fake_monthly_result(params)
        result["blocks"][0]["rows"] = [
            {"item": "確定受注", "values": [1000, *([0] * 30)], "total": 1500, "balance": 500},
                {"item": "本日在庫", "values": [0 for _ in range(31)], "total": 999, "balance": None},
        ]
        return result

    monkeypatch.setattr("application.gonenkukumi.infrastructure.oracle.client.run_gonenkukumi_oracle_search", fake_search)
    client.force_login(user)

    response = client.get("/app/production/five-year-nine/result?custCode=101&custItem=ITEM-001&yearMonth=2026-05&optionChange=*")

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert re.search(
        r"<th>確定受注</th>\s*"
        r'<td class="qty row-total">1,500</td>\s*'
        r'<td class="qty">500</td>\s*'
        r'<td class="qty [^"]*">1,000</td>',
        html,
    )
    assert re.search(
        r"<th>本日在庫</th>\s*"
        r'<td class="qty row-total">999</td>\s*'
        r'<td class="qty"></td>\s*'
        r'<td class="qty [^"]*"></td>',
        html,
    )


@pytest.mark.django_db
def test_export_returns_xlsx(client, user):
    client.force_login(user)
    response = client.get("/api/gonenkukumi/export?custCode=101&custItem=ITEM-001&yearMonth=2026-05&optionChange=*")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert re.match(r'attachment; filename="101_ITEM-001_2026_05_\d{14}\.xlsx"', response["Content-Disposition"])


@pytest.mark.django_db
def test_export_uses_requested_months(client, user, monkeypatch):
    requested_months = []

    def fake_search(params):
        requested_months.append(params.year_month)
        return fake_monthly_result(params)

    monkeypatch.setattr("application.gonenkukumi.infrastructure.oracle.client.run_gonenkukumi_oracle_search", fake_search)
    client.force_login(user)

    response = client.get(
        "/api/gonenkukumi/export"
        "?custCode=101&custItem=ITEM-001&yearMonth=2026-05&optionChange=*"
        "&months=2026-04,2026-05,2026-06"
    )

    assert response.status_code == 200
    assert requested_months == ["2026-04", "2026-05", "2026-06"]


def test_result_page_table_row_height_css():
    css = (Path(__file__).resolve().parents[3] / "static" / "css" / "app.css").read_text(encoding="utf-8")
    assert "--gonen-result-row-height: 26px" in css
    assert "--gonen-result-font-size: 13px" in css
    assert "--gonen-result-qty-font-size: 12px" in css
    grid_rule = css.split(".next-report-grid th,\n.next-report-grid td {")[1].split("}")[0]
    assert "min-height: var(--gonen-result-row-height)" in grid_rule
    assert "font-size: var(--gonen-result-font-size)" in css.split(".next-report-grid {")[1].split("}")[0]
    assert "font-size: var(--gonen-result-qty-font-size)" in css.split(".next-report-grid .qty {")[1].split("}")[0]
    bare_content_rule = css.split(".bare-result-page .content {")[1].split("}")[0]
    assert "overflow: visible" in bare_content_rule
    assert "max-height: none" in bare_content_rule
    portal_bare_rule = css.split("body.portal-app-page.bare-result-page {")[1].split("}")[0]
    assert "overflow-y: auto" in portal_bare_rule
    portal_bare_content_rule = css.split("body.portal-app-page.bare-result-page .content {")[1].split("}")[0]
    assert "display: block" in portal_bare_content_rule
    assert "max-height: none" in portal_bare_content_rule
    assert "overflow: visible" in portal_bare_content_rule
    segment_rule = css.split(".next-segment {")[1].split("}")[0]
    assert "overflow: visible" in segment_rule
    assert "clamp(8px" not in css.split(".next-report-grid {")[1].split("}")[0]


@pytest.mark.django_db
def test_search_page_uses_viewport_fitted_layout():
    css = (Path(__file__).resolve().parents[3] / "static" / "css" / "app.css").read_text(encoding="utf-8")
    assert "body.portal-app-page .portal-main" in css
    assert "body.portal-app-page .layout" in css
    assert "body.portal-app-page .content > .gonen-search" in css
    assert ".gonen-search" in css
    assert ".gonen-search-body" in css
    body_rule = css.split(".receipt-settings-body,\n.gonen-search-body {")[1].split("}")[0]
    assert "grid-template-columns: minmax(280px, 380px) minmax(0, 1fr)" in body_rule
    assert "gap: 24px" in body_rule
    assert "height: 100%" in body_rule
    gonen_search_rule = css.split(".gonen-search-page .gonen-search {")[1].split("}")[0]
    assert "grid-template-rows: auto minmax(0, 1fr)" in gonen_search_rule
    assert "padding-bottom: var(--gonen-history-bottom-gap)" in gonen_search_rule
    assert "--gonen-history-bottom-gap: 16px" in css
    history_card_rule = css.split(".gonen-history-list-card {")[1].split("}")[0]
    assert "height: 100%" in history_card_rule
    assert "overflow: hidden" in history_card_rule
    search_card_rule = css.split(".gonen-search-card {")[1].split("}")[0]
    assert "padding: 16px 18px" in search_card_rule
    assert "overflow: visible" in search_card_rule
    assert "var(--portal-control-height)" in css.split(".gonen-search-page .gonen-search-card input:not([type=\"hidden\"]),")[1].split("}")[0]
    assert ".gonen-search-shell" not in css
    assert ".gonen-history-card" not in css
    assert ".history-table-wrap" not in css
    history_th_rule = css.split(".gonen-history-list-card .db-table th {")[1].split("}")[0]
    assert "position: sticky" in history_th_rule
    assert "top: 0" in history_th_rule
    gonen_content_rule = css.split("body.portal-app-page.gonen-search-page .content {")[1].split("}")[0]
    assert "overflow: hidden" in gonen_content_rule


@pytest.mark.django_db
def test_search_page_uses_gonen_search_body_class(client, user):
    client.force_login(user)
    response = client.get("/app/production/five-year-nine")
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "portal-app-page" in html
    assert "gonen-search-page" in html
    assert 'class="gonen-search"' in html
    assert 'class="portal-section-head gonen-search-head"' in html
    assert 'class="portal-page-description"' in html
    assert "得意先品目の内示・受注・出荷・仕入・入荷の推移を検索します。" in html
    assert 'class="gonen-search-body"' in html
    assert 'class="gonen-search-sidebar"' in html
    assert 'class="gonen-setting-form card gonen-search-card"' in html
    assert 'class="db-table-card gonen-history-list-card"' in html
    assert 'class="db-table-wrap"' in html
    assert 'class="db-table gonen-history-table"' in html
