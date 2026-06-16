from __future__ import annotations

from apps.receipt_comparison.domain.comparison import ComparisonRow
from apps.receipt_comparison.models import ReceiptFlag
from apps.receipt_comparison.services.comparison_sort import quantity_sort_key, resolve_sort_params, sort_display_rows
from apps.receipt_comparison.services.pending_comparison import DisplayRow, comparison_row_from_dict, comparison_row_to_dict


def test_comparison_row_roundtrip_dict():
    row = ComparisonRow(
        existing_id=5,
        receipt_flag=ReceiptFlag.OK,
        mari_item_cd="AB-001",
        mari_date="2026/06/01",
        mari_qty="10",
        supplier_item_cd="AB001",
        supplier_delivery_month_day="0601",
        supplier_qty="10",
        remarks="memo",
    )

    restored = comparison_row_from_dict(comparison_row_to_dict(row))

    assert restored.existing_id == 5
    assert restored.receipt_flag == ReceiptFlag.OK
    assert restored.mari_item_cd == "AB-001"
    assert restored.remarks == "memo"


def test_sort_display_rows_by_mari_item_cd_desc():
    rows = [
        DisplayRow(None, 0, ReceiptFlag.NG, "B-002", "", "", "", "", "", "", "", "", ""),
        DisplayRow(None, 1, ReceiptFlag.NG, "A-001", "", "", "", "", "", "", "", "", ""),
    ]

    sorted_rows = sort_display_rows(rows, "mari_item_cd", "desc")

    assert [row.mari_item_cd for row in sorted_rows] == ["B-002", "A-001"]


def test_sort_display_rows_by_mari_qty_handles_empty_and_numeric():
    rows = [
        DisplayRow(None, 0, ReceiptFlag.NG, "", "", "10", "", "", "", "", "", "", ""),
        DisplayRow(None, 1, ReceiptFlag.NG, "", "", "", "", "", "", "", "", "", ""),
        DisplayRow(None, 2, ReceiptFlag.NG, "", "", "2", "", "", "", "", "", "", ""),
    ]

    sorted_rows = sort_display_rows(rows, "mari_qty", "asc")

    assert [row.mari_qty for row in sorted_rows] == ["", "2", "10"]


def test_resolve_sort_params_uses_result_on_initial_display():
    sort_key, sort_direction = resolve_sort_params(sort_key="", sort_direction="", reset_to_default=True)

    assert sort_key == "receipt_flag"
    assert sort_direction == "asc"


def test_resolve_sort_params_keeps_selected_column():
    sort_key, sort_direction = resolve_sort_params(
        sort_key="mari_item_cd",
        sort_direction="desc",
        reset_to_default=False,
    )

    assert sort_key == "mari_item_cd"
    assert sort_direction == "desc"


def test_quantity_sort_key_returns_comparable_tuple():
    assert quantity_sort_key("2") < quantity_sort_key("10")
    assert quantity_sort_key("") < quantity_sort_key("10")
    assert quantity_sort_key("abc") > quantity_sort_key("10")
