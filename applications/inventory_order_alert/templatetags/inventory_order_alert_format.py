from __future__ import annotations

from django import template

from applications.inventory_order_alert.domain.format_display import format_cell_display
from applications.inventory_order_alert.domain.alert_level import ALERT_NONE
from applications.inventory_order_alert.domain.row_display import display_alert_level, row_alert_class

register = template.Library()


@register.filter(name="ioa_display")
def ioa_display(row: dict[str, object], column: str) -> str:
    if not isinstance(row, dict):
        return ""
    if column == "alert_level":
        return display_alert_level(row)
    return format_cell_display(row.get(column, ""), column)


@register.filter(name="ioa_row_alert_class")
def ioa_row_alert_class(row: dict[str, object]) -> str:
    if not isinstance(row, dict):
        return ALERT_NONE
    return row_alert_class(row)
