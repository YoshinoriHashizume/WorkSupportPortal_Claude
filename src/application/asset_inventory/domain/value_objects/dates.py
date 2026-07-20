from __future__ import annotations

from datetime import date, datetime


def parse_inventory_datetime(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def parse_asset_acquisition_date(value: str) -> date | None:
    text = (value or "").strip()
    if not text:
        return None
    for fmt in (
        "%Y/%m/%d",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def format_asset_acquisition_date_display(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    parsed = parse_asset_acquisition_date(text)
    if parsed is not None:
        return parsed.strftime("%Y/%m/%d")
    return text
