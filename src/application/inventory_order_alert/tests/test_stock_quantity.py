from __future__ import annotations

import pytest

from application.inventory_order_alert.domain.value_objects.stock_quantity import (
    STOCK_NOT_FETCHED,
    format_stock_quantity,
    is_stock_fetched,
)

MARI_STOCK_KEY = "mari_stock_qty"


def test_format_stock_quantity_returns_number_for_positive_value():
    assert format_stock_quantity(100) == "100"


def test_format_stock_quantity_returns_zero_for_zero_value():
    # 在庫が 0 であることと、突合先に品番が無いことは別物
    assert format_stock_quantity(0) == "0"


def test_format_stock_quantity_returns_empty_for_missing_item():
    # 突合先に品番が無い場合は空。0 にしない
    assert format_stock_quantity("") == ""


def test_format_stock_quantity_returns_marker_when_not_fetched():
    assert format_stock_quantity(100, fetched=False) == STOCK_NOT_FETCHED


def test_format_stock_quantity_returns_negative_value_as_is():
    # 基幹の値を加工しない
    assert format_stock_quantity(-5) == "-5"


def test_format_stock_quantity_adds_thousand_separator():
    assert format_stock_quantity(12345) == "12,345"


def test_format_stock_quantity_accepts_decimal():
    # SLIMS はバラ数で小数を許容する
    assert format_stock_quantity("10.5") == "10.5"


def test_is_stock_fetched_returns_false_when_key_absent():
    assert is_stock_fetched({"stock_qty": 100}, MARI_STOCK_KEY) is False


def test_is_stock_fetched_returns_true_when_key_present_and_empty():
    # 該当なし（キーあり・空）は「取得済み」である
    assert is_stock_fetched({MARI_STOCK_KEY: ""}, MARI_STOCK_KEY) is True


def test_is_stock_fetched_returns_true_when_value_is_zero():
    assert is_stock_fetched({MARI_STOCK_KEY: 0}, MARI_STOCK_KEY) is True


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({MARI_STOCK_KEY: 100}, "100"),
        ({MARI_STOCK_KEY: ""}, ""),
        ({"stock_qty": 100}, STOCK_NOT_FETCHED),
    ],
    ids=["値あり", "該当なし", "未取得"],
)
def test_three_states_are_mutually_distinguishable(row, expected):
    fetched = is_stock_fetched(row, MARI_STOCK_KEY)

    assert format_stock_quantity(row.get(MARI_STOCK_KEY, ""), fetched=fetched) == expected
