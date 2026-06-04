from __future__ import annotations

from numbers import Number

from django import template

register = template.Library()


@register.filter
def quantity(value: object) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, Number):
        return "" if value == 0 else f"{value:,.0f}"
    try:
        number = int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return str(value)
    return "" if number == 0 else f"{number:,}"


@register.filter
def date_slash(value: object) -> str:
    return str(value or "").replace("-", "/")
