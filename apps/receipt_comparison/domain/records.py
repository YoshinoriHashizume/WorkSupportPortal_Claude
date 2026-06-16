from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReceiptFileRow:
    item_cd: str
    delivery_month_day: str
    qty: str
    cancel_qty: str = ""
    supplier_name: str = ""


@dataclass(frozen=True)
class MariReceiptRow:
    item_cd: str
    ship_date: str
    ship_qty: str
    delivery_place: str = ""
