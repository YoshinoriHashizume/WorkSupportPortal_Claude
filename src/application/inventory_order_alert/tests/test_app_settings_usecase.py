from __future__ import annotations

import pytest

from application.inventory_order_alert.domain.value_objects import app_settings as app_settings_module
from application.inventory_order_alert.domain.value_objects.app_settings import (
    AppSettings,
    parse_settings_payload,
    settings_payload,
)
from application.inventory_order_alert.domain.value_objects.flow_quadrant import FlowThresholds
from application.inventory_order_alert.infrastructure.persistence.settings_repository import (
    load_app_settings,
    save_app_settings,
)
from application.inventory_order_alert.use_cases.app_settings import AppSettingsUseCase

#: 旧アラートレベル方式でのみ使っていた設定項目（design.md §6.5 の削除対象）。
REMOVED_SETTING_FIELDS = ("warning_shipment_months", "warning_incoming_months", "critical_enabled")
REMOVED_PAYLOAD_KEYS = ("warningShipmentMonths", "warningIncomingMonths", "criticalEnabled")
REMOVED_MODULE_ATTRIBUTES = (
    "AlertSettingsInput",
    "parse_alert_settings_payload",
    "clamp_warning_months",
    "MIN_WARNING_MONTHS",
    "MAX_WARNING_MONTHS",
)


def test_app_settings_has_no_warning_month_or_critical_enabled_fields():
    settings = AppSettings()

    for field_name in REMOVED_SETTING_FIELDS:
        assert not hasattr(settings, field_name)


def test_app_settings_keeps_warning_days_and_stock_stale_days():
    settings = AppSettings()

    assert settings.warning_days == 365
    assert settings.stock_stale_days == 7


def test_parse_settings_payload_ignores_critical_enabled_key():
    parsed = parse_settings_payload({"criticalEnabled": True})

    assert parsed.warning_days == AppSettings().warning_days
    assert not hasattr(parsed, "critical_enabled")


def test_settings_payload_has_no_warning_month_or_critical_enabled_keys():
    payload = settings_payload(AppSettings())

    for key in REMOVED_PAYLOAD_KEYS:
        assert key not in payload


def test_app_settings_module_has_no_alert_settings_input():
    for attribute in REMOVED_MODULE_ATTRIBUTES:
        assert not hasattr(app_settings_module, attribute)


def test_parse_settings_payload_accepts_valid_values():
    parsed = parse_settings_payload({"warningDays": 400, "stockStaleDays": 14})
    assert parsed.warning_days == 400
    assert parsed.stock_stale_days == 14


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"warningDays": 1}, 1),
        ({"warningDays": 3650}, 3650),
    ],
)
def test_parse_settings_payload_accepts_boundary_warning_days(payload, expected):
    assert parse_settings_payload(payload).warning_days == expected


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"stockStaleDays": 1}, 1),
        ({"stockStaleDays": 365}, 365),
    ],
)
def test_parse_settings_payload_accepts_boundary_stock_stale_days(payload, expected):
    assert parse_settings_payload(payload).stock_stale_days == expected


@pytest.mark.parametrize(
    "payload",
    [
        {"warningDays": 0},
        {"warningDays": 3651},
        {"stockStaleDays": 0},
        {"stockStaleDays": 366},
    ],
)
def test_parse_settings_payload_rejects_out_of_range(payload):
    with pytest.raises(ValueError):
        parse_settings_payload(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"warningDays": "abc"},
        {"warningDays": None},
        {"warningDays": True},
        "not-a-dict",
    ],
)
def test_parse_settings_payload_rejects_invalid_types(payload):
    with pytest.raises(ValueError):
        parse_settings_payload(payload)


def test_parse_settings_payload_accepts_numeric_strings():
    # 画面のフォーム送信は文字列で届くため、数値文字列は受け付ける
    assert parse_settings_payload({"stockStaleDays": "14"}).stock_stale_days == 14


def test_parse_settings_payload_keeps_current_values_for_missing_keys():
    current = AppSettings(warning_days=730, stock_stale_days=3)
    parsed = parse_settings_payload({"stockStaleDays": 10}, current=current)
    assert parsed.warning_days == 730
    assert parsed.stock_stale_days == 10


def test_settings_payload_exposes_all_keys():
    assert settings_payload(AppSettings()) == {
        "warningDays": 365,
        "stockStaleDays": 7,
        "safetyDays": 14,
        "defaultLeadTimeDays": 5,
        "watchMonths": 6,
        # 07 第 2 段階: 直近入荷の窓（REQ-FQR-F-008）
        "recentIncomingDays": 30,
    }


@pytest.mark.django_db
def test_save_app_settings_persists_values():
    saved = save_app_settings(warning_days=730, stock_stale_days=3)
    assert saved.warning_days == 730
    assert saved.stock_stale_days == 3
    assert load_app_settings() == saved


@pytest.mark.django_db
def test_app_settings_usecase_load_and_save():
    use_case = AppSettingsUseCase(load_app_settings, save_app_settings)
    assert use_case.load_payload()["stockStaleDays"] == 7

    result = use_case.save({"stockStaleDays": 21})
    assert result["stockStaleDays"] == 21
    assert result["warningDays"] == 365


@pytest.mark.django_db
def test_app_settings_usecase_rejects_invalid_payload():
    use_case = AppSettingsUseCase(load_app_settings, save_app_settings)
    with pytest.raises(ValueError):
        use_case.save({"stockStaleDays": 999})


# --- 06_stockout-risk: TC-SOR-D-054 設定 VO（安全日数・既定リードタイム・監視期間） ---

import pytest  # noqa: E402

from application.inventory_order_alert.domain.value_objects.app_settings import (  # noqa: E402
    parse_settings_payload,
    settings_payload,
)


def test_d054_stockout_risk_settings_defaults():
    settings = AppSettings()

    assert settings.safety_days == 14
    assert settings.default_lead_time_days == 5
    assert settings.watch_months == 6
    risk = settings.to_stockout_risk_settings()
    assert (risk.safety_days, risk.default_lead_time_days, risk.watch_months) == (14, 5, 6)


@pytest.mark.parametrize(
    "kwargs",
    [{"safety_days": 0}, {"safety_days": 61}, {"default_lead_time_days": 0}, {"default_lead_time_days": 61}, {"watch_months": 0}, {"watch_months": 13}],
)
def test_d054_out_of_range_values_are_rejected(kwargs):
    with pytest.raises(ValueError):
        AppSettings(**kwargs)


def test_d054_settings_payload_round_trip():
    payload = settings_payload(AppSettings(safety_days=30, default_lead_time_days=7, watch_months=3))

    assert payload["safetyDays"] == 30
    assert payload["defaultLeadTimeDays"] == 7
    assert payload["watchMonths"] == 3

    parsed = parse_settings_payload({"safetyDays": 21, "watchMonths": 9}, current=AppSettings())
    assert (parsed.safety_days, parsed.default_lead_time_days, parsed.watch_months) == (21, 5, 9)

    with pytest.raises(ValueError):
        parse_settings_payload({"safetyDays": 99}, current=AppSettings())


# --- 07_flow-quadrant-refinement 第 2 段階: 直近入荷の窓（REQ-FQR-F-008） ---


def test_fqr_f008_recent_incoming_days_default_and_thresholds():
    settings = AppSettings()

    assert settings.recent_incoming_days == 30
    assert settings.to_flow_thresholds().recent_incoming_days == 30
    assert settings.to_flow_thresholds() == FlowThresholds(recent_incoming_days=30)


@pytest.mark.parametrize("value", [0, 91])
def test_fqr_f008_out_of_range_recent_incoming_days_is_rejected(value):
    with pytest.raises(ValueError):
        AppSettings(recent_incoming_days=value)


def test_fqr_f008_settings_payload_round_trip():
    payload = settings_payload(AppSettings(recent_incoming_days=45))

    assert payload["recentIncomingDays"] == 45

    parsed = parse_settings_payload({"recentIncomingDays": 60}, current=AppSettings())
    assert parsed.recent_incoming_days == 60
    # 未指定なら現在値を引き継ぐ
    assert parse_settings_payload({}, current=AppSettings(recent_incoming_days=45)).recent_incoming_days == 45

    with pytest.raises(ValueError):
        parse_settings_payload({"recentIncomingDays": 91}, current=AppSettings())


def test_fqr_f008_demand_window_months_is_not_a_setting():
    """需要の窓は需要の判定を内示のみに改めた時点で撤去した（REQ-FQR-F-008）。"""
    assert not hasattr(AppSettings(), "demand_window_months")
    assert "demandWindowMonths" not in settings_payload(AppSettings())
