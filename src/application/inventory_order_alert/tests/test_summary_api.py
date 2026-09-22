from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings
from application.inventory_order_alert.domain.value_objects.slims_stock import SlimsStockLocationLine
from application.inventory_order_alert.domain.value_objects.summary import StockImportInfo, SummaryLoadResult
from application.inventory_order_alert.use_cases.portal_dashboard import PortalDashboard
from application.inventory_order_alert.use_cases.summary_api import (
    DashboardSummary,
    StockLocations,
    SummaryApi,
    Vendors,
)

AS_OF = date(2026, 6, 17)


def _stock_info(**overrides: object) -> StockImportInfo:
    return StockImportInfo(
        imported_at=datetime(2026, 6, 17, 9, 0, 0),
        row_count=2,
        file_name="slims.csv",
        stock_as_of_date=AS_OF,
        stock_as_of_label="2026年6月17日時点の在庫",
        summary_row_count=2,
        **overrides,
    )


def _row(**overrides: object) -> dict[str, object]:
    return {
        "cust_code": "112",
        "cust_name": "テスト得意先",
        "item_cd": "90249-10112",
        "level1_vend_cd": "9209",
        "level1_vend_name": "小野メッキ",
        "last_incoming_date": "",
        "last_ship_date": "2026/06/15",
        "post_shipment_count": 1,
        "post_shipment_total_qty": 250,
        "stock_qty": Decimal("100"),
        "confirmation_status": "未確認",
    } | overrides


def _summary(rows: list[dict[str, object]], **overrides: object) -> SummaryLoadResult:
    return SummaryLoadResult(
        rows=rows,
        stock_info=_stock_info(),
        as_of_date=AS_OF,
        aggregation_error="",
        total_count=len(rows),
        critical_count=0,
        warning_count=0,
        **overrides,
    )


def _settings(**overrides: object) -> AppSettings:
    return AppSettings(**overrides)


# --- §8.1 summary -----------------------------------------------------------


def test_summary_api_returns_rows_counts_and_stock_import():
    summary = _summary([_row()])
    result = SummaryApi(lambda: summary, lambda: _settings()).execute({}, today=AS_OF)

    assert result["ok"] is True
    assert result["counts"]["total"] == len(result["rows"])
    assert result["stockImport"]["stockAsOfLabel"] == "2026年6月17日時点の在庫"
    assert result["stockImport"]["rowCount"] == 2
    assert result["stockImport"]["isStale"] is False


def test_summary_api_returns_json_serializable_values():
    summary = _summary([_row()])
    result = SummaryApi(lambda: summary, lambda: _settings()).execute({}, today=AS_OF)

    assert result["rows"][0]["stock_qty"] == 100
    assert not isinstance(result["rows"][0]["stock_qty"], Decimal)


def test_summary_api_returns_empty_result_without_snapshot():
    result = SummaryApi(lambda: None, lambda: _settings()).execute({}, today=AS_OF)

    assert result["rows"] == []
    assert result["counts"]["total"] == 0
    assert result["stockImport"] is None


def test_summary_api_merge_query_with_settings_does_not_override_flow_selection():
    """判定期間は利用者がクエリで選ぶ値であり、設定値で上書きしない（05 design §6.1）。"""
    summary = _summary([_row(last_incoming_date="", last_ship_date="2026/06/15")])
    result = SummaryApi(lambda: summary, lambda: _settings()).execute({"period": "5"}, today=AS_OF)

    assert result["rows"][0]["flow_quadrant"] == "低流動品（入荷なし）"


def test_summary_api_counts_payload_uses_flow_quadrant_keys():
    summary = _summary([_row(last_incoming_date="", last_ship_date="2026/06/15")])
    result = SummaryApi(lambda: summary, lambda: _settings()).execute({}, today=AS_OF)

    assert set(result["counts"]) == {
        "total",
        "attention",
        # 07 在庫なしの 3 区分（TC-FQR-C-003）
        "stockoutNoIncoming",
        "stockout",
        "discontinuationCandidate",
        "lowFlowNoIncoming",
        "dormantStock",
        "lowFlowNoShipment",
        "normalFlow",
        "unconfirmed",
        # 06 在庫切れリスク
        "danger",
        "caution",
        "watch",
        "noneRisk",
    }
    assert result["counts"]["lowFlowNoIncoming"] == 1


def test_summary_api_attention_only_excludes_normal_flow():
    summary = _summary(
        [
            _row(last_incoming_date="", last_ship_date="2026/06/15"),
            _row(item_cd="90249-99999", last_incoming_date="2026/06/10", last_ship_date="2026/06/15"),
        ]
    )
    result = SummaryApi(lambda: summary, lambda: _settings()).execute(
        {"attentionOnly": "true"}, today=AS_OF
    )

    assert [row["flow_quadrant"] for row in result["rows"]] == ["低流動品（入荷なし）"]


def test_summary_api_reflects_selected_evaluation_period():
    summary = _summary([_row(last_incoming_date="2024/01/10", last_ship_date="2024/02/10")])

    one_year = SummaryApi(lambda: summary, lambda: _settings()).execute({}, today=AS_OF)
    five_years = SummaryApi(lambda: summary, lambda: _settings()).execute({"period": "5"}, today=AS_OF)
    legacy = SummaryApi(lambda: summary, lambda: _settings()).execute({"axis": "dormant", "period": "5"}, today=AS_OF)

    assert one_year["rows"][0]["flow_quadrant"] == "在庫死蔵品"
    assert five_years["rows"][0]["flow_quadrant"] == "通常流動品"
    # 旧 URL の axis は無視され、period の年数だけが効く
    assert legacy["rows"][0]["flow_quadrant"] == "通常流動品"


def test_summary_api_filters_by_vend_code():
    summary = _summary([_row(), _row(level1_vend_cd="8100", item_cd="90249-99999")])
    result = SummaryApi(lambda: summary, lambda: _settings()).execute(
        {"vendCode": "8100", "alertOnly": "false"}, today=AS_OF
    )

    assert [row["level1_vend_cd"] for row in result["rows"]] == ["8100"]


def test_summary_api_hides_confirmed_rows_when_requested():
    summary = _summary(
        [_row(), _row(item_cd="90249-99999", confirmation_status="確認済み")]
    )
    result = SummaryApi(lambda: summary, lambda: _settings()).execute(
        {"hideConfirmed": "true", "alertOnly": "false"}, today=AS_OF
    )

    assert all(row["confirmation_status"] != "確認済み" for row in result["rows"])


def test_summary_api_sorts_by_alert_rank_then_quantity():
    summary = _summary(
        [
            _row(item_cd="A", post_shipment_total_qty=10),
            _row(item_cd="B", post_shipment_total_qty=900),
        ]
    )
    result = SummaryApi(lambda: summary, lambda: _settings()).execute(
        {"alertOnly": "false"}, today=AS_OF
    )

    assert [row["item_cd"] for row in result["rows"]] == ["B", "A"]


def test_summary_api_rejects_invalid_as_of_date():
    summary = _summary([_row()])
    use_case = SummaryApi(lambda: summary, lambda: _settings())
    with pytest.raises(ValueError):
        use_case.execute({"asOfDate": "2026/13/45"}, today=AS_OF)


def test_summary_api_marks_stale_stock_import():
    summary = _summary([_row()])
    result = SummaryApi(lambda: summary, lambda: _settings(stock_stale_days=3)).execute(
        {}, today=date(2026, 6, 30)
    )

    assert result["stockImport"]["isStale"] is True


# --- §8.4 stock-locations ---------------------------------------------------


def _stock_lines() -> list[SlimsStockLocationLine]:
    return [
        SlimsStockLocationLine(item_cd="90249-10112", wloccd="2D0-03-5", stock_qty=Decimal("60")),
        SlimsStockLocationLine(item_cd="90249-10112", wloccd="2D0-03-5", stock_qty=Decimal("30")),
        SlimsStockLocationLine(item_cd="90249-10112", wloccd="2E1-03-4", stock_qty=Decimal("10")),
        SlimsStockLocationLine(item_cd="90249-99999", wloccd="2F1-01-1", stock_qty=Decimal("5")),
    ]


def test_stock_locations_aggregates_same_location():
    use_case = StockLocations(lambda: (_stock_lines(), _stock_info()))
    result = use_case.execute("90249-10112")

    assert result["ok"] is True
    assert result["itemCd"] == "90249-10112"
    assert result["stockAsOfLabel"] == "2026年6月17日時点の在庫"
    assert {entry["wloccd"]: entry["stock_qty"] for entry in result["locations"]} == {
        "2D0-03-5": 90,
        "2E1-03-4": 10,
    }


def test_stock_locations_returns_empty_for_unknown_item():
    use_case = StockLocations(lambda: (_stock_lines(), _stock_info()))
    assert use_case.execute("00000-00000")["locations"] == []


@pytest.mark.parametrize("item_cd", ["", "   "])
def test_stock_locations_requires_item_cd(item_cd):
    use_case = StockLocations(lambda: (_stock_lines(), _stock_info()))
    with pytest.raises(ValueError):
        use_case.execute(item_cd)


# --- §8.9 vendors -----------------------------------------------------------


def test_vendors_are_deduplicated_and_sorted_by_code():
    summary = _summary(
        [
            _row(level1_vend_cd="9209", level1_vend_name="小野メッキ"),
            _row(level1_vend_cd="8100", level1_vend_name="丸英工業"),
            _row(level1_vend_cd="9209", level1_vend_name="小野メッキ"),
            _row(level1_vend_cd="", level1_vend_name=""),
        ]
    )
    result = Vendors(lambda: summary).execute()

    assert result["items"] == [
        {"code": "8100", "name": "丸英工業"},
        {"code": "9209", "name": "小野メッキ"},
    ]


def test_vendors_returns_empty_without_snapshot():
    assert Vendors(lambda: None).execute() == {"ok": True, "items": []}


# --- §8.11 dashboard-summary ------------------------------------------------


def test_dashboard_summary_serializes_counts_and_stock_import():
    summary = _summary([_row()])
    dashboard = PortalDashboard(lambda: summary, lambda: _settings())
    result = DashboardSummary(dashboard, lambda: summary).execute()

    assert result["ok"] is True
    assert set(result["counts"]) == {
        "stockoutNoIncoming",
        "stockout",
        "lowFlowNoIncoming",
        "dormantStock",
        "lowFlowNoShipment",
        "discontinuationCandidate",
        "attention",
        "unconfirmed",
        "danger",
        "caution",
        "watch",
    }
    assert result["stockImport"]["hasData"] is True
    assert result["stockImport"]["stockAsOfLabel"] == "2026年6月17日時点の在庫"
    assert result["stockImport"]["importedAt"] == "2026-06-17T09:00:00"


def test_dashboard_summary_without_stock_data():
    dashboard = PortalDashboard(lambda: None, lambda: _settings())
    result = DashboardSummary(dashboard, lambda: None).execute()

    assert result["counts"] == {
        "stockoutNoIncoming": 0,
        "stockout": 0,
        "lowFlowNoIncoming": 0,
        "dormantStock": 0,
        "lowFlowNoShipment": 0,
        "discontinuationCandidate": 0,
        "attention": 0,
        "unconfirmed": 0,
        "danger": 0,
        "caution": 0,
        "watch": 0,
    }
    assert result["stockImport"]["hasData"] is False
    assert result["stockImport"]["importedAt"] is None


# --- API 経路（§8.1 / §8.4 / §8.9 / §8.11） ---------------------------------


@pytest.fixture
def production_user(db):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group

    from application.portal.models import PortalMenuGroupAccess

    user = get_user_model().objects.create_user(username="10002", last_name="生産", first_name="担当")
    admin_group, _ = Group.objects.get_or_create(name="管理者")
    user.groups.add(admin_group)
    PortalMenuGroupAccess.objects.get_or_create(user=user, group_key="production")
    return user


READ_API_URLS = [
    "/api/inventory-order-alert/summary",
    "/api/inventory-order-alert/vendors",
    "/api/inventory-order-alert/dashboard-summary",
]


@pytest.mark.django_db
@pytest.mark.parametrize("url", READ_API_URLS)
def test_read_apis_respond_without_snapshot(client, production_user, url):
    client.force_login(production_user)
    response = client.get(url)

    assert response.status_code == 200
    assert response.json()["ok"] is True


@pytest.mark.django_db
def test_stock_locations_api_requires_item_cd(client, production_user):
    client.force_login(production_user)
    response = client.get("/api/inventory-order-alert/stock-locations")

    assert response.status_code == 400
    assert response.json()["ok"] is False


@pytest.mark.django_db
def test_summary_api_rejects_invalid_query(client, production_user):
    client.force_login(production_user)
    response = client.get("/api/inventory-order-alert/summary", {"asOfDate": "2026/13/45"})

    assert response.status_code == 400
    assert response.json()["ok"] is False


@pytest.mark.django_db
@pytest.mark.parametrize("url", READ_API_URLS + ["/api/inventory-order-alert/stock-locations"])
def test_read_apis_reject_user_without_menu_access(client, db, url):
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.create_user(username="10004", last_name="他部門", first_name="利用者")
    client.force_login(user)

    assert client.get(url).status_code == 403
