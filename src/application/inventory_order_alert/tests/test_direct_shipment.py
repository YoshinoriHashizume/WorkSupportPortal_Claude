"""直送仕入先（V-240）・直送品（T-212）の domain テスト。

spec/12_direct-shipment-exclusion test-design.md TC-DSE-D-001〜045。
"""

from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal

import pytest

from application.inventory_order_alert.domain.value_objects.app_settings import (
    AppSettings,
    parse_settings_payload,
    settings_payload,
)
from application.inventory_order_alert.domain.value_objects.demand_forecast import attach_demand_forecast
from application.inventory_order_alert.domain.value_objects.direct_shipment import (
    DEFAULT_DIRECT_SHIPMENT_SUPPLIERS,
    DirectShipmentSuppliers,
    exclude_direct_shipment_items,
    is_direct_shipment,
)
from application.inventory_order_alert.domain.value_objects.stockout_risk import attach_response_class

AS_OF = date(2026, 9, 15)
SUPPLIERS = DirectShipmentSuppliers.parse(["9100", "9250"])


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "cust_code": "308",
        "item_cd": "15D126-0020",
        "level1_item_cd": "15D126-0020-9100",
        "level1_vend_cd": "9100",
        "level1_vend_name": "丸栄豊田",
        "stock_qty": "",
    }
    row.update(overrides)
    return row


def _normal_row(**overrides: object) -> dict[str, object]:
    """直送品でない行（在庫あり・内示あり。在庫が動く）。"""
    row = _row(
        cust_code="100",
        item_cd="062432-0680",
        level1_item_cd="062432-0680-9146",
        level1_vend_cd="9146",
        level1_vend_name="通常仕入先",
        stock_qty="1200",
        shipment_trend=[{"month": f"M{index:02d}", "qty": 100} for index in range(24)],
        unconfirmed_order_trend=[
            {"month": "2026-09", "qty": 0},
            {"month": "2026-10", "qty": 100},
            {"month": "2026-11", "qty": 100},
            {"month": "2026-12", "qty": 100},
        ],
    )
    row.update(overrides)
    return row


# --- DirectShipmentSuppliers ----------------------------------------------------


def test_d001_parse_strips_and_sorts_codes():
    assert DirectShipmentSuppliers.parse(["9250", " 9100 ", "9200"]).codes == ("9100", "9200", "9250")


def test_d002_parse_accepts_zero_codes():
    suppliers = DirectShipmentSuppliers.parse([])

    assert suppliers.is_empty is True
    assert suppliers.codes == ()


@pytest.mark.parametrize("values", [["9100", ""], ["  "]])
def test_d003_parse_rejects_empty_code(values):
    with pytest.raises(ValueError, match="直送仕入先に空の仕入先コードは登録できません。"):
        DirectShipmentSuppliers.parse(values)


def test_d004_parse_rejects_duplicates_after_stripping():
    with pytest.raises(ValueError, match="直送仕入先に同じ仕入先コードが重複しています: 9100"):
        DirectShipmentSuppliers.parse(["9100", " 9100"])


def test_d005_parse_accepts_20_chars_and_rejects_21_chars():
    assert DirectShipmentSuppliers.parse(["A" * 20]).codes == ("A" * 20,)
    with pytest.raises(ValueError, match="仕入先コードは 20 文字以内で指定してください。"):
        DirectShipmentSuppliers.parse(["A" * 21])


def test_d006_from_stored_drops_invalid_entries():
    suppliers = DirectShipmentSuppliers.from_stored(["9100", "", 1, None, "9100", " 9250 "])

    assert suppliers.codes == ("9100", "9250")


@pytest.mark.parametrize("value", ["9100", None, {}])
def test_d007_from_stored_reads_non_list_as_empty(value):
    assert DirectShipmentSuppliers.from_stored(value).is_empty is True


def test_d008_added_since_returns_only_new_codes():
    new = DirectShipmentSuppliers.parse(["9100", "9250"])
    old = DirectShipmentSuppliers.parse(["9100", "9200"])

    assert new.added_since(old) == ("9250",)


def test_d009_equal_by_codes_and_immutable():
    suppliers = DirectShipmentSuppliers.parse(["9200", "9100"])

    assert suppliers == DirectShipmentSuppliers.parse(["9100", "9200"])
    assert suppliers.contains(" 9100 ") is True
    assert suppliers.contains("9250") is False
    with pytest.raises(FrozenInstanceError):
        suppliers.codes = ()  # type: ignore[misc]


def test_d010_default_suppliers_are_three_codes():
    assert DEFAULT_DIRECT_SHIPMENT_SUPPLIERS.codes == ("9100", "9200", "9250")


# --- is_direct_shipment ---------------------------------------------------------


def test_d020_all_direct_suppliers_and_no_slims_stock_is_direct_shipment():
    assert is_direct_shipment([_row(), _row(cust_code="191")], SUPPLIERS) is True


def test_d021_none_stock_counts_as_empty():
    assert is_direct_shipment([_row(stock_qty=None)], SUPPLIERS) is True


@pytest.mark.parametrize("zero", [0, Decimal("0")])
def test_d022_zero_stock_is_not_empty(zero):
    assert is_direct_shipment([_row(stock_qty=zero), _row(cust_code="191")], SUPPLIERS) is False


def test_d023_slims_stock_present_is_not_direct_shipment():
    assert is_direct_shipment([_row(stock_qty=120), _row(cust_code="191")], SUPPLIERS) is False


def test_d024_mixed_suppliers_is_not_direct_shipment():
    rows = [_row(), _row(level1_item_cd="15D126-0020-9146", level1_vend_cd="9146")]

    assert is_direct_shipment(rows, SUPPLIERS) is False


def test_d025_row_without_supplier_is_not_direct_shipment():
    rows = [_row(), _row(level1_item_cd="", level1_vend_cd="")]

    assert is_direct_shipment(rows, SUPPLIERS) is False


def test_d026_supplier_code_is_compared_after_stripping():
    assert is_direct_shipment([_row(level1_vend_cd=" 9100 ")], SUPPLIERS) is True


def test_d027_no_direct_suppliers_means_no_direct_shipment():
    assert is_direct_shipment([_row()], DirectShipmentSuppliers.parse([])) is False


def test_d028_no_rows_is_not_direct_shipment():
    assert is_direct_shipment([], SUPPLIERS) is False


# --- exclude_direct_shipment_items ----------------------------------------------


def _mixed_rows() -> list[dict[str, object]]:
    return [
        _row(cust_code="100", item_cd="062432-0680", level1_item_cd="062432-0680-9146", level1_vend_cd="9146", stock_qty=11165),
        _row(cust_code="308"),
        _row(cust_code="191"),
        _row(cust_code="100", item_cd="079351-0810", level1_item_cd="079351-0810-9133", level1_vend_cd="9133"),
    ]


def test_d030_excludes_only_direct_shipment_unit_and_keeps_order():
    rows = _mixed_rows()

    result = exclude_direct_shipment_items(rows, SUPPLIERS)

    assert result.kept_rows == [rows[0], rows[3]]
    assert result.excluded_row_count == 2
    assert result.excluded_unit_count == 1


def test_d031_items_sharing_supplier_item_are_excluded_together():
    rows = [
        _row(item_cd="X", level1_item_cd="SHARED"),
        _row(item_cd="Y", level1_item_cd="SHARED"),
    ]

    result = exclude_direct_shipment_items(rows, SUPPLIERS)

    assert result.kept_rows == []
    assert result.excluded_row_count == 2
    assert result.excluded_unit_count == 1


def test_d032_unit_with_slims_stock_on_one_item_is_kept_entirely():
    rows = [
        _row(item_cd="X", level1_item_cd="SHARED"),
        _row(item_cd="Y", level1_item_cd="SHARED", stock_qty=10),
    ]

    result = exclude_direct_shipment_items(rows, SUPPLIERS)

    assert result.kept_rows == rows
    assert result.excluded_row_count == 0


def test_d033_rows_without_item_cd_are_judged_individually():
    direct = _row(item_cd="")
    normal = _row(item_cd="", level1_vend_cd="9146")

    result = exclude_direct_shipment_items([direct, normal], SUPPLIERS)

    assert result.kept_rows == [normal]
    assert result.excluded_row_count == 1
    assert result.excluded_unit_count == 1


def test_d034_no_direct_suppliers_returns_input_as_is():
    rows = _mixed_rows()

    result = exclude_direct_shipment_items(rows, DirectShipmentSuppliers.parse([]))

    assert result.kept_rows == rows
    assert result.excluded_row_count == 0
    assert result.excluded_unit_count == 0


def test_d035_does_not_mutate_input():
    rows = _mixed_rows()
    before = copy.deepcopy(rows)

    exclude_direct_shipment_items(rows, SUPPLIERS)

    assert rows == before


def test_d036_remaining_units_are_judged_the_same_as_without_exclusion():
    rows = [_normal_row(), _row(), _row(cust_code="191")]

    def judge(target):
        return attach_response_class(attach_demand_forecast(target, AS_OF), AS_OF)

    without = [row for row in judge(rows) if row["item_cd"] == "062432-0680"]
    with_exclusion = judge(exclude_direct_shipment_items(rows, SUPPLIERS).kept_rows)

    keys = (
        "stockout_date",
        "order_deadline",
        "response_class",
        "demand_forecast_stock_total",
        "reconciliation_unit_key",
    )
    assert [{key: row.get(key) for key in keys} for row in with_exclusion] == [
        {key: row.get(key) for key in keys} for row in without
    ]
    assert with_exclusion == without


# --- 設定の JSON 変換 -------------------------------------------------------------


def test_d040_default_app_settings_has_default_direct_suppliers():
    assert AppSettings().direct_shipment_suppliers == DEFAULT_DIRECT_SHIPMENT_SUPPLIERS


def test_d041_settings_payload_includes_direct_supplier_codes():
    assert settings_payload(AppSettings())["directShipmentSupplierCodes"] == ["9100", "9200", "9250"]


def test_d042_missing_key_keeps_current_suppliers():
    current = AppSettings(direct_shipment_suppliers=DirectShipmentSuppliers.parse(["9100"]))

    parsed = parse_settings_payload({"warningDays": 100}, current=current)

    assert parsed.direct_shipment_suppliers.codes == ("9100",)


def test_d043_payload_replaces_whole_list():
    parsed = parse_settings_payload({"directShipmentSupplierCodes": ["9250"]})

    assert parsed.direct_shipment_suppliers.codes == ("9250",)


def test_d044_empty_list_clears_suppliers():
    parsed = parse_settings_payload({"directShipmentSupplierCodes": []})

    assert parsed.direct_shipment_suppliers.is_empty is True


@pytest.mark.parametrize("value", ["9100", [9100], [None]])
def test_d045_non_list_or_non_string_is_rejected(value):
    with pytest.raises(ValueError, match="直送仕入先は仕入先コードの配列で指定してください。"):
        parse_settings_payload({"directShipmentSupplierCodes": value})
