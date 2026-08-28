from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    QUADRANT_DORMANT_STOCK,
    QUADRANT_EXCESS_STOCK_RISK,
    QUADRANT_NORMAL_FLOW,
    QUADRANT_SUPPLY_RISK,
)
from application.inventory_order_alert.domain.value_objects.row_counts import RowCounts, count_rows

QUADRANT_UNKNOWN = "謎"
ROWS_EMPTY: list[dict[str, object]] = []
REMOVED_FIELDS = ("critical", "warning", "warning_ship", "warning_incoming", "alert_none", "alert")


def _row(quadrant: str, confirmation_status: str = "未確認") -> dict[str, object]:
    return {"flow_quadrant": quadrant, "confirmation_status": confirmation_status}


def _two_of_each_quadrant() -> list[dict[str, object]]:
    return [
        _row(QUADRANT_SUPPLY_RISK),
        _row(QUADRANT_SUPPLY_RISK),
        _row(QUADRANT_DORMANT_STOCK),
        _row(QUADRANT_DORMANT_STOCK),
        _row(QUADRANT_EXCESS_STOCK_RISK),
        _row(QUADRANT_EXCESS_STOCK_RISK),
        _row(QUADRANT_NORMAL_FLOW),
        _row(QUADRANT_NORMAL_FLOW),
    ]


def test_count_rows_counts_each_flow_quadrant_separately():
    rows = _two_of_each_quadrant()

    counts = count_rows(rows)

    assert counts.supply_risk == 2
    assert counts.dormant_stock == 2
    assert counts.excess_stock_risk == 2
    assert counts.normal_flow == 2


def test_count_rows_attention_equals_sum_of_three_risk_quadrants():
    rows = _two_of_each_quadrant()

    counts = count_rows(rows)

    assert counts.attention == 6


def test_count_rows_flow_quadrant_counts_sum_to_total():
    rows = [
        _row(QUADRANT_SUPPLY_RISK),
        _row(QUADRANT_DORMANT_STOCK),
        _row(QUADRANT_DORMANT_STOCK),
        _row(QUADRANT_NORMAL_FLOW),
        _row(QUADRANT_EXCESS_STOCK_RISK),
    ]

    counts = count_rows(rows)

    assert (
        counts.supply_risk + counts.dormant_stock + counts.excess_stock_risk + counts.normal_flow
        == counts.total
    )


def test_count_rows_includes_confirmed_rows_in_flow_quadrant_counts():
    rows = [
        _row(QUADRANT_SUPPLY_RISK, confirmation_status="確認済み"),
        _row(QUADRANT_SUPPLY_RISK, confirmation_status="未確認"),
    ]

    counts = count_rows(rows)

    assert counts.supply_risk == 2
    assert counts.confirmed == 1
    assert counts.unconfirmed == 1


def test_count_rows_left_and_right_totals_match():
    rows = [
        _row(QUADRANT_SUPPLY_RISK, confirmation_status="確認済み"),
        _row(QUADRANT_DORMANT_STOCK, confirmation_status="確認中"),
        _row(QUADRANT_EXCESS_STOCK_RISK, confirmation_status="未確認"),
        _row(QUADRANT_NORMAL_FLOW, confirmation_status="未確認"),
    ]

    counts = count_rows(rows)

    quadrant_total = (
        counts.supply_risk + counts.dormant_stock + counts.excess_stock_risk + counts.normal_flow
    )
    confirmation_total = counts.confirmed + counts.in_progress + counts.unconfirmed
    assert quadrant_total == confirmation_total


def test_count_rows_returns_all_zero_for_empty_rows():
    counts = count_rows(ROWS_EMPTY)

    assert counts == RowCounts()
    assert counts.total == 0
    assert counts.attention == 0


def test_count_rows_counts_unknown_flow_quadrant_as_normal_flow():
    rows = [_row(QUADRANT_UNKNOWN)]

    counts = count_rows(rows)

    assert counts.normal_flow == 1
    assert counts.attention == 0


def test_row_counts_has_no_critical_or_warning_fields():
    counts = RowCounts()

    for field_name in REMOVED_FIELDS:
        assert not hasattr(counts, field_name)
