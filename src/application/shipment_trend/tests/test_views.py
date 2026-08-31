from __future__ import annotations

import json
from datetime import date
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client

from application.portal.models import PortalMenuGroupAccess
from application.shipment_trend.domain.value_objects.summary import SummaryLoadResult
from application.shipment_trend.models import ShipmentTrendBaselineYear, ShipmentTrendRefresh, ShipmentTrendSummarySnapshot


@pytest.fixture
def auth_client(db):
    user_model = get_user_model()
    user = user_model.objects.create_user(username="st-user", password="pass")
    admin_group, _ = Group.objects.get_or_create(name="管理者")
    user.groups.add(admin_group)
    PortalMenuGroupAccess.objects.create(user=user, group_key="sales")
    client = Client()
    assert client.login(username="st-user", password="pass")
    return client


@pytest.fixture
def snapshot_row():
    return {
        "cust_code": "101",
        "cust_name": "テスト",
        "cust_chrg_psn_cd": "A01",
        "item_cd": "ITEM-1",
        "monthly": {"2024-04": 100, "2025-04": 150},
        "first_fiscal_year": 2024,
        "current_fiscal_year": 2025,
        "first_fy_total": 100,
        "current_fy_total": 150,
        "change_qty": 50,
        "change_rate_pct": 50.0,
    }


def _create_snapshot(rows: list[dict[str, object]], as_of_date: date = date(2025, 6, 1)) -> None:
    refresh = ShipmentTrendRefresh.objects.create()
    ShipmentTrendSummarySnapshot.objects.create(
        refresh_record=refresh,
        as_of_date=as_of_date,
        rows=rows,
        total_count=len(rows),
    )


def test_list_page_requires_login(db):
    response = Client().get("/app/sales/shipment-trend")
    assert response.status_code == 302


def test_list_page_without_snapshot(auth_client):
    response = auth_client.get("/app/sales/shipment-trend")
    html = response.content.decode()
    assert response.status_code == 200
    assert "データ更新" in html
    assert 'id="st-refresh-overlay"' in html
    assert "Oracle から出荷データを集計中" in html


def test_api_chart_data(auth_client, snapshot_row):
    _create_snapshot([snapshot_row])
    response = auth_client.get("/api/shipment-trend/chart?custCode=101&itemCd=ITEM-1")
    assert response.status_code == 200
    body = json.loads(response.content)
    assert body["ok"] is True
    assert body["chart"]["itemCd"] == "ITEM-1"
    assert len(body["chart"]["points"]) > 0
    assert len(body["chart"]["fiscalYears"]) == 2
    assert body["chart"]["custName"] == "テスト"
    assert body["chart"]["regression"] is not None


@patch("application.shipment_trend.interfaces.wiring.load_latest_summary")
def test_export_csv_with_item_cd_filter(mock_load, auth_client, snapshot_row):
    row2 = {**snapshot_row, "item_cd": "ITEM-2"}
    mock_load.return_value = SummaryLoadResult(
        rows=[snapshot_row, row2],
        as_of_date=date(2025, 6, 1),
        aggregation_error="",
        total_count=2,
        refreshed_at=date(2025, 6, 1),
    )
    response = auth_client.get("/app/sales/shipment-trend/export.csv?item_cd=ITEM-1")
    assert response.status_code == 200
    body = response.content.decode("utf-8-sig")
    assert "ITEM-1" in body
    assert "ITEM-2" not in body


@patch("application.shipment_trend.interfaces.wiring.load_latest_summary")
def test_export_csv(mock_load, auth_client, snapshot_row):
    mock_load.return_value = SummaryLoadResult(
        rows=[snapshot_row],
        as_of_date=date(2025, 6, 1),
        aggregation_error="",
        total_count=1,
        refreshed_at=date(2025, 6, 1),
    )
    response = auth_client.get("/app/sales/shipment-trend/export.csv")
    assert response.status_code == 200
    assert "text/csv" in response["Content-Type"]
    assert "ITEM-1" in response.content.decode("utf-8-sig")


def test_api_baseline_year_put_and_delete(auth_client, snapshot_row):
    row = {
        **snapshot_row,
        "monthly": {"2023-04": 10, "2024-04": 100, "2025-04": 150},
    }
    _create_snapshot([row])
    put_response = auth_client.put(
        "/api/shipment-trend/baseline-year",
        data=json.dumps({"custCode": "101", "itemCd": "ITEM-1", "baselineYear": 2024}),
        content_type="application/json",
    )
    assert put_response.status_code == 200, put_response.content
    put_body = json.loads(put_response.content)
    assert put_body["ok"] is True
    assert put_body["baselineYear"] == 2024
    assert ShipmentTrendBaselineYear.objects.filter(cust_code="101", item_cd="ITEM-1").exists()

    chart_response = auth_client.get("/api/shipment-trend/chart?custCode=101&itemCd=ITEM-1")
    chart_body = json.loads(chart_response.content)
    assert chart_body["chart"]["baselineIsManual"] is True
    assert chart_body["chart"]["baselineFiscalYear"] == 2024
    assert chart_body["chart"]["regression"] is not None

    reject = auth_client.put(
        "/api/shipment-trend/baseline-year",
        data=json.dumps({"custCode": "101", "itemCd": "ITEM-1", "baselineYear": 2099}),
        content_type="application/json",
    )
    assert reject.status_code == 400

    delete_response = auth_client.delete(
        "/api/shipment-trend/baseline-year",
        data=json.dumps({"custCode": "101", "itemCd": "ITEM-1"}),
        content_type="application/json",
    )
    assert delete_response.status_code == 200
    assert not ShipmentTrendBaselineYear.objects.filter(cust_code="101", item_cd="ITEM-1").exists()
