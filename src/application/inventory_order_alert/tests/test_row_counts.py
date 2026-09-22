from __future__ import annotations

"""件数サマリのテスト（TC-SFV-D-057）。項目名は新区分（低流動品（入荷なし）/（出荷なし））に追随する。"""

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    FLOW_QUADRANTS,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_INCOMING,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
)
from application.inventory_order_alert.domain.value_objects.row_counts import RowCounts, count_rows

QUADRANT_UNKNOWN = "謎"
ROWS_EMPTY: list[dict[str, object]] = []
REMOVED_FIELDS = (
    "critical",
    "warning",
    "warning_ship",
    "warning_incoming",
    "alert_none",
    "alert",
    "supply_risk",
    "excess_stock_risk",
)


def _row(quadrant: str, confirmation_status: str = "未確認") -> dict[str, object]:
    return {"flow_quadrant": quadrant, "confirmation_status": confirmation_status}


def _two_of_each_quadrant() -> list[dict[str, object]]:
    return [_row(quadrant) for quadrant in FLOW_QUADRANTS for _ in range(2)]


def test_count_rows_counts_each_flow_quadrant_separately():
    rows = _two_of_each_quadrant()

    counts = count_rows(rows)

    assert counts.stockout_no_incoming == 2
    assert counts.stockout == 2
    assert counts.low_flow_no_incoming == 2
    assert counts.dormant_stock == 2
    assert counts.low_flow_no_shipment == 2
    assert counts.discontinuation_candidate == 2
    assert counts.normal_flow == 2


def test_fqr_c001_attention_is_every_quadrant_but_normal_flow():
    """要対応は推奨アクションが空でない区分＝通常流動品以外（07 design §2.7、2026/09/21 明確化）。"""
    counts = count_rows(_two_of_each_quadrant())

    assert counts.attention == counts.total - counts.normal_flow == 12


def test_count_rows_flow_quadrant_counts_sum_to_total():
    rows = [
        _row(QUADRANT_LOW_FLOW_NO_INCOMING),
        _row(QUADRANT_DORMANT_STOCK),
        _row(QUADRANT_DORMANT_STOCK),
        _row(QUADRANT_NORMAL_FLOW),
        _row(QUADRANT_LOW_FLOW_NO_SHIPMENT),
    ]

    counts = count_rows(rows)

    assert (
        counts.low_flow_no_incoming + counts.dormant_stock + counts.low_flow_no_shipment + counts.normal_flow
        == counts.total
    )


def test_count_rows_includes_confirmed_rows_in_flow_quadrant_counts():
    rows = [
        _row(QUADRANT_LOW_FLOW_NO_INCOMING, confirmation_status="確認済み"),
        _row(QUADRANT_LOW_FLOW_NO_INCOMING, confirmation_status="未確認"),
    ]

    counts = count_rows(rows)

    assert counts.low_flow_no_incoming == 2
    assert counts.confirmed == 1
    assert counts.unconfirmed == 1


def test_count_rows_left_and_right_totals_match():
    rows = [
        _row(QUADRANT_LOW_FLOW_NO_INCOMING, confirmation_status="確認済み"),
        _row(QUADRANT_DORMANT_STOCK, confirmation_status="確認中"),
        _row(QUADRANT_LOW_FLOW_NO_SHIPMENT, confirmation_status="未確認"),
        _row(QUADRANT_NORMAL_FLOW, confirmation_status="未確認"),
    ]

    counts = count_rows(rows)

    quadrant_total = (
        counts.low_flow_no_incoming + counts.dormant_stock + counts.low_flow_no_shipment + counts.normal_flow
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


def test_d057_counts_by_quadrant_label_uses_new_names():
    counts = count_rows([_row(quadrant) for quadrant in FLOW_QUADRANTS])

    # ランク順（S-203）の 7 キー
    assert list(counts.by_quadrant) == [
        "欠品（入荷なし）",
        "欠品",
        "低流動品（入荷なし）",
        "在庫死蔵品",
        "低流動品（出荷なし）",
        "打ち切り候補",
        "通常流動品",
    ]
    assert set(counts.by_quadrant.values()) == {1}


def test_fqr_c001_by_quadrant_counts_sum_to_total():
    counts = count_rows(_two_of_each_quadrant())

    assert sum(counts.by_quadrant.values()) == counts.total


def test_d057_legacy_labels_are_counted_under_new_quadrants():
    rows = [_row("供給リスク品"), _row("在庫過剰リスク品"), _row("supply-risk")]

    counts = count_rows(rows)

    assert counts.low_flow_no_incoming == 2
    assert counts.low_flow_no_shipment == 1
    assert counts.normal_flow == 0
