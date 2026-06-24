from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.inventory_order_alert.usecase.usecase_portal_dashboard import DashboardBannerContext
from apps.inventory_order_alert.composition import portal_dashboard_usecase
from apps.inventory_order_alert.infrastructure.persistence.summary_snapshot_repository import store_summary_snapshot
from apps.inventory_order_alert.models import SlimsStockImport


def _sample_row(alert_level: str = "重点") -> dict[str, object]:
    row = {
        "cust_code": "100",
        "cust_name": "テスト得意先",
        "item_cd": "43522-D1020-00",
        "level1_item_cd": "43522-D1020-00",
        "level1_vend_cd": "9209",
        "level1_vend_name": "仕入先",
        "last_incoming_date": "",
        "last_ship_date": "2026/06/15",
        "post_shipment_count": 1,
        "post_shipment_total_qty": 10,
        "stock_qty": "100",
        "stock_as_of_label": "2026年6月17日時点の在庫",
        "confirmation_status": "未確認",
        "alert_level": alert_level,
    }
    if alert_level == "警告（出荷あり）":
        row["last_incoming_date"] = "2022/01/31"
        row["last_ship_date"] = "2025/02/01"
        row["post_shipment_count"] = 2
    elif alert_level == "アラート無し":
        row["last_incoming_date"] = "2026/05/01"
        row["post_shipment_count"] = 1
    return row


@pytest.mark.django_db
def test_load_dashboard_banner_context_from_summary_snapshot():
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=3)
    store_summary_snapshot(
        import_record,
        [_sample_row("重点"), _sample_row("警告（出荷あり）"), _sample_row("アラート無し")],
        as_of_date=date(2026, 6, 17),
    )

    banner = portal_dashboard_usecase().execute()

    assert banner.critical == 1
    assert banner.warning_ship == 1
    assert banner.warning == 1
    assert banner.unconfirmed == 3
    assert banner.stock_as_of_label.endswith("時点の在庫")
    assert banner.tone == "critical"
    assert not banner.error_message


@pytest.mark.django_db
def test_load_dashboard_banner_context_without_import():
    banner = portal_dashboard_usecase().execute()

    assert banner.critical == 0
    assert banner.warning == 0
    assert not banner.has_stock_data


@pytest.mark.django_db
def test_load_dashboard_banner_context_shows_error_when_aggregation_failed():
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)
    store_summary_snapshot(import_record, [], as_of_date=date(2026, 6, 17), aggregation_error="Oracle 未設定")

    banner = portal_dashboard_usecase().execute()

    assert banner.error_message
    assert banner.has_stock_data is True
    assert banner.tone == "neutral"
