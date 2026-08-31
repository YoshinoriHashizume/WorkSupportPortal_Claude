from __future__ import annotations

from datetime import date


def fiscal_year_of(value: date) -> int:
    """集計年（暦年・1月〜12月）。ラベルは西暦年（例: 2025-06 → 2025年）。"""
    return value.year


def year_month_to_date(year_month: str) -> date:
    year_text, month_text = year_month.split("-", 1)
    return date(int(year_text), int(month_text), 1)


def year_month_label(year_month: str) -> str:
    parsed = year_month_to_date(year_month)
    return f"{parsed.year}年{parsed.month}月"


def add_months(year_month: str, delta: int) -> str:
    parsed = year_month_to_date(year_month)
    month_index = parsed.year * 12 + (parsed.month - 1) + delta
    year = month_index // 12
    month = month_index % 12 + 1
    return f"{year:04d}-{month:02d}"
