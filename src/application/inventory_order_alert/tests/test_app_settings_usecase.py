from __future__ import annotations

import pytest

from application.inventory_order_alert.domain.value_objects.app_settings import (
    AppSettings,
    parse_settings_payload,
    settings_payload,
)
from application.inventory_order_alert.infrastructure.persistence.settings_repository import (
    load_app_settings,
    save_app_settings,
)
from application.inventory_order_alert.use_cases.app_settings import AppSettingsUseCase


def test_parse_settings_payload_accepts_valid_values():
    parsed = parse_settings_payload(
        {"warningDays": 400, "criticalEnabled": False, "stockStaleDays": 14}
    )
    assert parsed.warning_days == 400
    assert parsed.critical_enabled is False
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
        {"criticalEnabled": "yes"},
        {"criticalEnabled": 1},
        "not-a-dict",
    ],
)
def test_parse_settings_payload_rejects_invalid_types(payload):
    with pytest.raises(ValueError):
        parse_settings_payload(payload)


def test_parse_settings_payload_accepts_numeric_strings():
    # 画面のフォーム送信は文字列で届くため、数値文字列は受け付ける
    assert parse_settings_payload({"stockStaleDays": "14"}).stock_stale_days == 14
    assert parse_settings_payload({"criticalEnabled": "false"}).critical_enabled is False


def test_parse_settings_payload_keeps_current_values_for_missing_keys():
    current = AppSettings(warning_days=730, critical_enabled=False, stock_stale_days=3)
    parsed = parse_settings_payload({"stockStaleDays": 10}, current=current)
    assert parsed.warning_days == 730
    assert parsed.critical_enabled is False
    assert parsed.stock_stale_days == 10


def test_settings_payload_exposes_all_keys():
    assert settings_payload(AppSettings()) == {
        "warningDays": 365,
        "warningShipmentMonths": 12,
        "warningIncomingMonths": 12,
        "criticalEnabled": True,
        "stockStaleDays": 7,
    }


@pytest.mark.django_db
def test_save_app_settings_persists_values():
    saved = save_app_settings(warning_days=730, critical_enabled=False, stock_stale_days=3)
    assert saved.warning_days == 730
    assert saved.critical_enabled is False
    assert saved.stock_stale_days == 3
    assert load_app_settings() == saved


@pytest.mark.django_db
def test_save_app_settings_keeps_warning_months():
    before = load_app_settings()
    saved = save_app_settings(warning_days=400, critical_enabled=True, stock_stale_days=5)
    assert saved.warning_shipment_months == before.warning_shipment_months
    assert saved.warning_incoming_months == before.warning_incoming_months


@pytest.mark.django_db
def test_app_settings_usecase_load_and_save():
    use_case = AppSettingsUseCase(load_app_settings, save_app_settings)
    assert use_case.load_payload()["stockStaleDays"] == 7

    result = use_case.save({"stockStaleDays": 21, "criticalEnabled": False})
    assert result["stockStaleDays"] == 21
    assert result["criticalEnabled"] is False
    assert result["warningDays"] == 365


@pytest.mark.django_db
def test_app_settings_usecase_rejects_invalid_payload():
    use_case = AppSettingsUseCase(load_app_settings, save_app_settings)
    with pytest.raises(ValueError):
        use_case.save({"stockStaleDays": 999})
