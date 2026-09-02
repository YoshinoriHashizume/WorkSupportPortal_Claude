"""得意先 x 得意先品番ごとの月次出荷推移（V-216）の集計ロジック（design.md 4.2）。"""

from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.dates import add_calendar_months


def build_monthly_shipment_trend(
    shipments: list[tuple[date, int]],
    *,
    as_of_date: date,
    months: int = 24,
) -> list[dict[str, object]]:
    """出荷明細を、as_of_date の月を含む直近 months か月ぶんの月次集計にする。

    出荷実績がない月も 0 として含め、常に固定長 months 件を古い順で返す。
    range 外の出荷明細は無視する。
    """
    totals: dict[str, int] = {}
    for ship_date, qty in shipments:
        key = f"{ship_date.year:04d}-{ship_date.month:02d}"
        totals[key] = totals.get(key, 0) + qty

    as_of_month_first = date(as_of_date.year, as_of_date.month, 1)
    oldest_month_first = add_calendar_months(as_of_month_first, -(months - 1))

    result: list[dict[str, object]] = []
    for offset in range(months):
        month_first = add_calendar_months(oldest_month_first, offset)
        key = f"{month_first.year:04d}-{month_first.month:02d}"
        result.append({"month": key, "qty": totals.get(key, 0)})
    return result
