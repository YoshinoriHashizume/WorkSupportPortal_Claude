from __future__ import annotations

from django import template

from application.inventory_order_alert.domain.value_objects.flow_quadrant import QUADRANT_NORMAL_FLOW
from application.inventory_order_alert.domain.value_objects.format_display import format_cell_display
from application.inventory_order_alert.domain.value_objects.list_client_data import STOCK_COLUMNS
from application.inventory_order_alert.domain.value_objects.row_display import display_flow_quadrant, row_alert_class
from application.inventory_order_alert.domain.value_objects.stock_quantity import (
    format_stock_quantity,
    is_stock_fetched,
)

register = template.Library()


@register.filter(name="ioa_display")
def ioa_display(row: dict[str, object], column: str) -> str:
    if not isinstance(row, dict):
        return ""
    if column == "flow_quadrant":
        return display_flow_quadrant(row)
    if column in STOCK_COLUMNS:
        # サーバ描画と JS 描画で未取得の表示を揃える(design.md §4.2)。
        return format_stock_quantity(row.get(column, ""), fetched=is_stock_fetched(row, column))
    return format_cell_display(row.get(column, ""), column)


@register.filter(name="ioa_row_alert_class")
def ioa_row_alert_class(row: dict[str, object]) -> str:
    if not isinstance(row, dict):
        return QUADRANT_NORMAL_FLOW
    return row_alert_class(row)
