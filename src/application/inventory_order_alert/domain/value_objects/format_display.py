from __future__ import annotations

from decimal import Decimal

QUANTITY_COLUMNS = frozenset(
    {"post_shipment_count", "post_shipment_total_qty", "stock_qty", "mari_stock_qty"}
)


def format_quantity_display(value: object) -> str:
    if value == "" or value is None:
        return ""
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return f"{int(value):,}"
        normalized = format(value, "f").rstrip("0").rstrip(".")
        if "." in normalized:
            whole, frac = normalized.split(".", 1)
            return f"{int(whole):,}.{frac}"
        return f"{int(normalized):,}"
    text = str(value).replace(",", "").strip()
    if not text:
        return ""
    if "." in text:
        whole, frac = text.split(".", 1)
        return f"{int(whole):,}.{frac}"
    return f"{int(text):,}"


def format_cell_display(value: object, column: str) -> str:
    if column in QUANTITY_COLUMNS:
        return format_quantity_display(value)
    if value is None:
        return ""
    return str(value)
