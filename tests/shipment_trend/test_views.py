from __future__ import annotations

import json
from datetime import date
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client

from apps.portal.models import PortalMenuGroupAccess
from apps.shipment_trend.domain.summary import SummaryLoadResult
from apps.shipment_trend.models import ShipmentTrendRefresh, ShipmentTrendSummarySnapshot


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


@patch("apps.shipment_trend.infrastructure.persistence.summary_repository.load_latest_summary")
def test_api_chart_data(mock_load, auth_client, snapshot_row):
    refresh = ShipmentTrendRefresh.objects.create()
    ShipmentTrendSummarySnapshot.objects.create(
        refresh_record=refresh,
        as_of_date=date(2025, 6, 1),
        rows=[snapshot_row],
        total_count=1,
    )
    mock_load.return_value = SummaryLoadResult(
        rows=[snapshot_row],
        as_of_date=date(2025, 6, 1),
        aggregation_error="",
        total_count=1,
        refreshed_at=date(2025, 6, 1),
    )
    response = auth_client.get("/api/shipment-trend/chart?custCode=101&itemCd=ITEM-1")
    assert response.status_code == 200
    body = json.loads(response.content)
    assert body["ok"] is True
    assert body["chart"]["itemCd"] == "ITEM-1"
    assert len(body["chart"]["points"]) > 0
    assert len(body["chart"]["fiscalYears"]) == 2
    assert body["chart"]["custName"] == "テスト"


@patch("apps.shipment_trend.infrastructure.persistence.summary_repository.load_latest_summary")
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


@patch("apps.shipment_trend.infrastructure.persistence.summary_repository.load_latest_summary")
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
