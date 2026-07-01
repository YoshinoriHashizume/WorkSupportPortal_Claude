from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]

APPS_WITH_TESTS = (
    "asset_inventory",
    "gonenkukumi",
    "identity",
    "inventory_order_alert",
    "portal",
    "receipt_comparison",
    "shipment_trend",
)


def test_pytest_ini_uses_apps_and_config_testpaths():
    content = (ROOT / "pytest.ini").read_text(encoding="utf-8")
    assert "testpaths = applications config" in content


def test_root_conftest_exists():
    assert (ROOT / "conftest.py").is_file()


def test_legacy_top_level_tests_dir_is_removed():
    legacy = ROOT / "tests"
    if legacy.is_dir():
        py_files = list(legacy.rglob("test_*.py"))
        assert py_files == [], f"legacy tests remain: {py_files[:5]}"


@pytest.mark.parametrize("app_name", APPS_WITH_TESTS)
def test_each_app_has_tests_package(app_name: str):
    tests_dir = ROOT / "applications" / app_name / "tests"
    assert tests_dir.is_dir(), app_name
    test_files = list(tests_dir.glob("test_*.py"))
    assert test_files, f"{app_name} has no test_*.py"


def test_inventory_order_alert_fixture_location():
    fixture = (
        ROOT
        / "applications"
        / "inventory_order_alert"
        / "tests"
        / "fixtures"
        / "slims_stock_sample_wkatqt.csv"
    )
    assert fixture.is_file()
