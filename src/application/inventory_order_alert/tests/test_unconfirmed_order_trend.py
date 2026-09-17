"""内示推移（V-219）のテスト（test-design.md TC-SFV-D-070〜075）。

当月残（基準日以降の所要日）＋翌月〜翌々々月の固定 4 件。数量が負なら 0。
"""

from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.unconfirmed_order_trend import (
    UNCONFIRMED_ORDER_TREND_LENGTH,
    build_unconfirmed_order_trend,
    unconfirmed_order_window_end,
)

AS_OF = date(2026, 9, 15)


def _months(trend: list[dict[str, object]]) -> list[str]:
    return [str(point["month"]) for point in trend]


def _qtys(trend: list[dict[str, object]]) -> list[int]:
    return [int(point["qty"]) for point in trend]


# --- TC-SFV-D-070: 当月残＋3 か月の固定 4 件 ---


def test_d070_current_month_remaining_plus_three_months():
    trend = build_unconfirmed_order_trend(
        [(date(2026, 9, 20), 100), (date(2026, 10, 5), 200), (date(2026, 11, 1), 300), (date(2026, 12, 31), 400)],
        as_of_date=AS_OF,
    )

    assert trend == [
        {"month": "2026-09", "qty": 100},
        {"month": "2026-10", "qty": 200},
        {"month": "2026-11", "qty": 300},
        {"month": "2026-12", "qty": 400},
    ]
    assert len(trend) == UNCONFIRMED_ORDER_TREND_LENGTH == 4


def test_d070_same_month_details_are_summed():
    trend = build_unconfirmed_order_trend(
        [(date(2026, 10, 5), 200), (date(2026, 10, 25), 50)],
        as_of_date=AS_OF,
    )

    assert _qtys(trend) == [0, 250, 0, 0]


# --- TC-SFV-D-071: 当月の基準日より前の所要日は当月残に含めない ---


def test_d071_current_month_before_as_of_is_excluded_and_boundary_is_included():
    trend = build_unconfirmed_order_trend(
        [(date(2026, 9, 10), 50), (date(2026, 9, 15), 60)],
        as_of_date=AS_OF,
    )

    assert _qtys(trend)[0] == 60


# --- TC-SFV-D-072: 窓の外（4 か月目以降）は無視 ---


def test_d072_fourth_month_onwards_is_ignored():
    trend = build_unconfirmed_order_trend(
        [(date(2027, 1, 5), 999), (date(2026, 12, 31), 1)],
        as_of_date=AS_OF,
    )

    assert _qtys(trend) == [0, 0, 0, 1]


def test_d072_window_end_is_first_day_of_the_fourth_month():
    assert unconfirmed_order_window_end(AS_OF) == date(2027, 1, 1)
    assert unconfirmed_order_window_end(date(2026, 11, 20)) == date(2027, 3, 1)
    assert unconfirmed_order_window_end(date(2026, 1, 31)) == date(2026, 5, 1)


# --- TC-SFV-D-073: 内示がない月は 0、明細なしは全 0 ---


def test_d073_no_details_gives_four_zero_months():
    trend = build_unconfirmed_order_trend([], as_of_date=AS_OF)

    assert _months(trend) == ["2026-09", "2026-10", "2026-11", "2026-12"]
    assert _qtys(trend) == [0, 0, 0, 0]


# --- TC-SFV-D-074: 負の数量は 0 として扱う ---


def test_d074_negative_quantity_is_treated_as_zero():
    trend = build_unconfirmed_order_trend(
        [(date(2026, 10, 5), -100), (date(2026, 10, 6), 30)],
        as_of_date=AS_OF,
    )

    assert _qtys(trend)[1] == 30


# --- TC-SFV-D-075: 年またぎ ---


def test_d075_window_crosses_year_end():
    trend = build_unconfirmed_order_trend([(date(2027, 2, 1), 5)], as_of_date=date(2026, 11, 20))

    assert _months(trend) == ["2026-11", "2026-12", "2027-01", "2027-02"]
    assert _qtys(trend) == [0, 0, 0, 5]
