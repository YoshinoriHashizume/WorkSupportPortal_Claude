from __future__ import annotations

from applications.shipment_trend.domain.app_settings import AppSettings, parse_alert_settings_payload
from applications.shipment_trend.domain.list_client_data import build_list_client_payload, row_to_client_dict
from applications.shipment_trend.domain.list_filter import build_filter_options


def _row(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {
        "cust_chrg_psn_cd": "A01",
        "cust_code": "101",
        "cust_name": "テスト",
        "item_cd": "ITEM-1",
        "first_fiscal_year": 2023,
        "first_fy_total": 100,
        "prev_fy_total": 80,
        "current_fy_with_forecast_total": 900,
        "change_rate_pct": -25.0,
        "change_qty": -50,
    }
    base.update(kwargs)
    return base


def test_row_to_client_dict_alert_class():
    settings = AppSettings(decrease_threshold_pct=20, increase_threshold_pct=20)
    client_row = row_to_client_dict(_row(), settings)
    assert client_row["alertRowClass"] == "st-row-decrease-strong"
    assert client_row["display"]["change_rate_pct"] == "-25.00%"
    assert client_row["display"]["first_fiscal_year"] == "2023"
    assert client_row["display"]["first_fy_total"] == "100"
    assert client_row["display"]["prev_fy_total"] == "80"
    assert client_row["display"]["current_fy_with_forecast_total"] == "900"


def test_row_to_client_dict_normalizes_non_finite_rate():
    settings = AppSettings(decrease_threshold_pct=20, increase_threshold_pct=20)
    client_row = row_to_client_dict(_row(change_rate_pct=float("nan")), settings)
    assert client_row["change_rate_pct"] is None


def test_build_list_client_payload():
    rows = [_row(), _row(cust_code="102", item_cd="ITEM-2", change_rate_pct=30.0)]
    options = build_filter_options(rows)
    settings = AppSettings(decrease_threshold_pct=20, increase_threshold_pct=20)
    payload = build_list_client_payload(all_rows=rows, filter_options=options, settings=settings)
    assert len(payload["rows"]) == 2
    assert payload["defaultSortSpecs"][0]["column"] == "change_rate_pct"
    assert payload["defaultSortSpecs"][0]["direction"] == "asc"
    assert payload["itemCdOptions"] == ["ITEM-1", "ITEM-2"]
    assert payload["filterOptions"]["itemCdOptions"] == ["ITEM-1", "ITEM-2"]


def test_parse_alert_settings_payload():
    settings = parse_alert_settings_payload(
        {"decreaseThresholdPct": 15, "increaseThresholdPct": 25},
    )
    assert settings.decrease_threshold_pct == 15
    assert settings.increase_threshold_pct == 25
