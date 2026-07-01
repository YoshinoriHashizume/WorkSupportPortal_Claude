from __future__ import annotations

import pytest

from applications.inventory_order_alert.domain.dev_data_guard import looks_like_test_import
from config.test_db_guard import assert_pytest_uses_test_database, is_test_database_name


def test_is_test_database_name():
    assert is_test_database_name("test_worksupportportal") is True
    assert is_test_database_name("worksupportportal") is False


def test_assert_pytest_uses_test_database_rejects_dev_db():
    with pytest.raises(RuntimeError, match="test_"):
        assert_pytest_uses_test_database("worksupportportal")


def test_looks_like_test_import_by_file_name():
    assert looks_like_test_import("sample.csv", []) is True
    assert looks_like_test_import("SLIMS_stock_sample.csv", []) is True
    assert looks_like_test_import("SISJB0001003000108848800.csv", []) is False


def test_looks_like_test_import_by_item_pattern():
    rows = [{"item_cd": f"ITEM-{index:02d}"} for index in range(21)]
    assert looks_like_test_import("import.csv", rows) is True
    assert looks_like_test_import("import.csv", [{"item_cd": "90249-10112"}]) is False
