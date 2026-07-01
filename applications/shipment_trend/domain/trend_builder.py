from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from applications.shipment_trend.domain.trend_metrics import compute_trend_metrics


@dataclass(frozen=True)
class MonthlyShipmentRecord:
    cust_code: str
    item_cd: str
    cust_chrg_psn_cd: str
    year_month: str
    ship_qty: int


def build_trend_rows(
    records: list[MonthlyShipmentRecord],
    customer_names: dict[str, str],
    *,
    as_of_date: date,
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], dict[str, object]] = {}
    for record in records:
        key = (record.cust_code, record.item_cd)
        if key not in grouped:
            grouped[key] = {
                "cust_code": record.cust_code,
                "item_cd": record.item_cd,
                "cust_chrg_psn_cd": record.cust_chrg_psn_cd,
                "monthly": {},
            }
        entry = grouped[key]
        if record.cust_chrg_psn_cd:
            entry["cust_chrg_psn_cd"] = record.cust_chrg_psn_cd
        monthly: dict[str, int] = entry["monthly"]  # type: ignore[assignment]
        monthly[record.year_month] = monthly.get(record.year_month, 0) + record.ship_qty

    rows: list[dict[str, object]] = []
    for (cust_code, item_cd), entry in sorted(grouped.items()):
        monthly: dict[str, int] = entry["monthly"]  # type: ignore[assignment]
        metrics = compute_trend_metrics(monthly, as_of_date)
        rows.append(
            {
                "cust_code": cust_code,
                "cust_name": customer_names.get(cust_code, ""),
                "cust_chrg_psn_cd": str(entry.get("cust_chrg_psn_cd") or "").strip(),
                "item_cd": item_cd,
                "monthly": monthly,
                **metrics,
            }
        )
    return rows
