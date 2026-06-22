from __future__ import annotations

from decimal import Decimal

from apps.inventory_order_alert.domain.format_display import format_cell_display, format_quantity_display


def test_format_quantity_display_integer_with_commas():
    assert format_quantity_display(250) == "250"
    assert format_quantity_display(1234567) == "1,234,567"
    assert format_quantity_display(Decimal("100")) == "100"


def test_format_quantity_display_empty():
    assert format_quantity_display("") == ""
    assert format_quantity_display(None) == ""


def test_format_cell_display_formats_quantity_columns_only():
    assert format_cell_display(2500, "post_shipment_total_qty") == "2,500"
    assert format_cell_display("90249-10112", "item_cd") == "90249-10112"
