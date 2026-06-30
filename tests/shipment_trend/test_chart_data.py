from __future__ import annotations

from datetime import date

from apps.shipment_trend.domain.app_settings import AppSettings
from apps.shipment_trend.domain.chart_data import build_chart_payload


def test_build_chart_payload_includes_all_fiscal_years():
    row = {
        "cust_code": "101",
        "cust_name": "テスト得意先",
        "cust_chrg_psn_cd": "A01",
        "item_cd": "ITEM-1",
        "monthly": {
            "2023-04": 100,
            "2024-04": 80,
            "2025-04": 200,
        },
    }
    payload = build_chart_payload(
        row,
        as_of_date=date(2025, 6, 1),
        settings=AppSettings(decrease_threshold_pct=20, increase_threshold_pct=20),
    )
    assert payload["custCode"] == "101"
    assert payload["custName"] == "テスト得意先"
    assert payload["custChrgPsnCd"] == "A01"
    assert len(payload["fiscalYears"]) == 3
    assert payload["fiscalYears"][0]["fiscalYear"] == 2023
    assert payload["fiscalYears"][2]["isCurrentYear"] is True
    assert payload["fiscalYears"][2]["fyWithForecastTotal"] >= payload["fiscalYears"][2]["fyTotal"]
