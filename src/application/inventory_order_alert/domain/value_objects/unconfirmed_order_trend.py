"""内示推移（V-219）の集計（05 design §4.4）。

内示受注の明細（所要日, 数量）を、当月残（基準日以降の所要日）＋翌月〜翌々々月の
固定 4 件に束ねる。出荷推移（V-216）と同じ ``{"month": "YYYY-MM", "qty": int}`` 形式。
"""

from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.dates import add_calendar_months

#: 当月残＋3 か月。
UNCONFIRMED_ORDER_TREND_LENGTH = 4


def _month_key(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def unconfirmed_order_window_end(as_of_date: date) -> date:
    """窓の終端（翌々々月の翌月 1 日。この日を含まない）。Oracle クエリの ``:window_end`` にも使う。"""
    month_first = date(as_of_date.year, as_of_date.month, 1)
    return add_calendar_months(month_first, UNCONFIRMED_ORDER_TREND_LENGTH)


def build_unconfirmed_order_trend(
    orders: list[tuple[date, int]],
    *,
    as_of_date: date,
) -> list[dict[str, object]]:
    """当月残（as_of_date 以降）＋翌月〜翌々々月の固定 4 件。数量が負なら 0、窓の外は無視。"""
    window_end = unconfirmed_order_window_end(as_of_date)
    totals: dict[str, int] = {}
    for required_date, qty in orders:
        if required_date < as_of_date or required_date >= window_end:
            continue
        totals[_month_key(required_date)] = totals.get(_month_key(required_date), 0) + max(int(qty), 0)

    month_first = date(as_of_date.year, as_of_date.month, 1)
    return [
        {"month": _month_key(add_calendar_months(month_first, offset)), "qty": totals.get(_month_key(add_calendar_months(month_first, offset)), 0)}
        for offset in range(UNCONFIRMED_ORDER_TREND_LENGTH)
    ]
