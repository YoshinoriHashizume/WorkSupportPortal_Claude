from __future__ import annotations

from datetime import date
from decimal import Decimal

from application.inventory_order_alert.domain.value_objects.dates import format_stock_as_of_label
from application.inventory_order_alert.domain.value_objects.slims_stock import (
    SlimsStockLocationLine,
    aggregate_location_lines,
    build_location_summary,
    format_location_detail_csv,
    group_locations_by_item,
    total_stock_qty,
)


def attach_stock_fields(
    rows: list[dict[str, object]],
    stock_lines: list[SlimsStockLocationLine] | None,
    *,
    stock_as_of_date: date | None = None,
) -> list[dict[str, object]]:
    if not stock_lines:
        return [dict(row) for row in rows]

    grouped = group_locations_by_item(stock_lines)
    stock_label = format_stock_as_of_label(stock_as_of_date) if stock_as_of_date else ""
    enriched: list[dict[str, object]] = []
    for row in rows:
        copied = dict(row)
        item_cd = str(copied.get("item_cd") or "")
        raw_locations = grouped.get(item_cd, [])
        if raw_locations:
            aggregated_locations = aggregate_location_lines(raw_locations)
            copied["stock_qty"] = total_stock_qty(raw_locations)
            copied["stock_location_summary"] = build_location_summary(aggregated_locations)
            copied["stock_location_detail"] = format_location_detail_csv(raw_locations)
        else:
            copied["stock_qty"] = ""
            copied["stock_location_summary"] = ""
            copied["stock_location_detail"] = ""
        copied["stock_as_of_label"] = stock_label
        enriched.append(copied)
    return enriched


def normalize_stock_qty(value: object) -> str:
    if value == "" or value is None:
        return ""
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return str(int(value))
        return format(value, "f").rstrip("0").rstrip(".")
    return str(value)
