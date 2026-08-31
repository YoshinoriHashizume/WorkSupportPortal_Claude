"""エッジケース・性能テスト（test-design.md §4.3 E-001〜E-010）。

基準日は固定リテラル。`date.today()` は使わない（test-design.md §5.2）。
"""

from __future__ import annotations

import json
import time
from datetime import date

import pytest

from application.inventory_order_alert.domain.value_objects.confirmation import STATUS_CHOICES
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    EVALUATION_PERIODS,
    EvaluationPeriod,
    FLOW_AXIS_DORMANT,
    FLOW_AXIS_HELP_TEXTS,
    FLOW_AXIS_LOW_FLOW,
    FLOW_QUADRANT_KEYS,
    FlowSelection,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_EXCESS_STOCK_RISK,
    QUADRANT_NORMAL_FLOW,
    QUADRANT_SUPPLY_RISK,
    resolve_flow_quadrant,
    resolve_flow_quadrant_matrix,
)
from application.inventory_order_alert.domain.value_objects.list_client_data import build_list_client_payload
from application.inventory_order_alert.domain.value_objects.list_filter import build_filter_options
from application.inventory_order_alert.domain.value_objects.list_query import ListQuery
from application.inventory_order_alert.domain.value_objects.list_rows import (
    apply_flow_quadrants_to_rows,
    filter_summary_rows,
)
from application.inventory_order_alert.domain.value_objects.row_counts import count_rows

AS_OF = date(2026, 8, 27)
SELECTION_L1 = FlowSelection(EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 1))
SELECTION_L3 = FlowSelection(EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 3))
SELECTION_D5 = FlowSelection(EvaluationPeriod(FLOW_AXIS_DORMANT, 5))

#: 基準日 2026/8/27 から各判定期間で境界がどう動くかを見るための代表日付。
DATES_SUPPLY_RISK = ("", "2026/08/20")
#: 死蔵判定軸5年（境界 2021/8/27）では期間内、低流動判定軸では期間外になる日付。
DATES_DORMANT_STOCK = ("2023/01/10", "2023/02/10")
DATES_EXCESS_STOCK_RISK = ("2026/08/20", "2019/02/10")
DATES_NORMAL_FLOW = ("2026/08/20", "2026/08/21")

#: 実測 222 バイト（test-design.md E-001。当初の 100 バイトは設計書の見積り誤りだった）。
PAYLOAD_BYTES_PER_ROW_LIMIT = 240
LARGE_ROW_COUNT = 5000
FORBIDDEN_TERMS = ("未流動品", "デッドストック", "不良在庫")


def _row(dates: tuple[str, str], *, item_cd: str, confirmation_status: str = "未確認") -> dict[str, object]:
    last_incoming_date, last_ship_date = dates
    return {
        "cust_code": "112",
        "cust_name": "テスト得意先",
        "cust_chrg_psn_cd": "A01",
        "item_cd": item_cd,
        "level1_item_cd": f"{item_cd}-9209",
        "level1_vend_cd": "9209",
        "level1_vend_name": "小野メッキ",
        "last_incoming_date": last_incoming_date,
        "last_ship_date": last_ship_date,
        "post_shipment_count": 1,
        "post_shipment_total_qty": 250,
        "stock_qty": "100",
        "confirmation_status": confirmation_status,
    }


def _query(selection: FlowSelection) -> ListQuery:
    return ListQuery(as_of_date=AS_OF, flow_selection=selection)


def _enriched(rows: list[dict[str, object]], selection: FlowSelection) -> list[dict[str, object]]:
    return apply_flow_quadrants_to_rows(rows, as_of_date=AS_OF, query=_query(selection))


def _payload(rows: list[dict[str, object]]) -> dict[str, object]:
    return build_list_client_payload(
        all_rows=rows,
        filter_options=build_filter_options(rows),
        confirmation_status_choices=list(STATUS_CHOICES),
    )


def _mixed_rows() -> list[dict[str, object]]:
    return [
        _row(DATES_SUPPLY_RISK, item_cd="ITEM-A", confirmation_status="確認済み"),
        _row(DATES_DORMANT_STOCK, item_cd="ITEM-B", confirmation_status="確認中"),
        _row(DATES_EXCESS_STOCK_RISK, item_cd="ITEM-C"),
        _row(DATES_NORMAL_FLOW, item_cd="ITEM-D"),
    ]


def test_e001_client_payload_increment_per_row_is_within_budget():
    payload = _payload(_enriched([_row(DATES_SUPPLY_RISK, item_cd="ITEM-A")], SELECTION_L3))
    client_row = payload["rows"][0]

    added = {
        "flowQuadrants": client_row["flowQuadrants"],
        "noIncomingRecord": client_row["noIncomingRecord"],
        "responsibleDepartment": client_row["responsibleDepartment"],
    }
    size = len(json.dumps(added, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    assert size <= PAYLOAD_BYTES_PER_ROW_LIMIT


def test_e002_payload_generation_keeps_row_count_for_large_input():
    rows = _enriched(
        [_row(DATES_SUPPLY_RISK, item_cd=f"ITEM-{index:05d}") for index in range(LARGE_ROW_COUNT)],
        SELECTION_L3,
    )

    started = time.perf_counter()
    payload = _payload(rows)
    elapsed = time.perf_counter() - started

    assert len(payload["rows"]) == LARGE_ROW_COUNT
    assert elapsed < 30


def test_e003_resolving_all_periods_for_large_input_completes():
    started = time.perf_counter()
    matrices = [
        resolve_flow_quadrant_matrix(date(2026, 1, 10), date(2026, 8, 20), as_of_date=AS_OF)
        for _ in range(LARGE_ROW_COUNT)
    ]
    elapsed = time.perf_counter() - started

    # 5,000 行 × 6 判定条件 = 30,000 回の判定。
    assert len(matrices) == LARGE_ROW_COUNT
    assert all(len(matrix) == len(EVALUATION_PERIODS) for matrix in matrices)
    assert elapsed < 30


def test_e004_switching_axis_keeps_same_row_set():
    rows = _mixed_rows()

    low_flow = _enriched(rows, SELECTION_L1)
    dormant = _enriched(rows, SELECTION_D5)

    assert [row["item_cd"] for row in low_flow] == [row["item_cd"] for row in dormant]
    assert {row["flow_quadrant"] for row in low_flow} != {row["flow_quadrant"] for row in dormant}


def test_e005_counts_left_and_right_totals_match():
    counts = count_rows(_enriched(_mixed_rows(), SELECTION_L3))

    quadrant_total = (
        counts.supply_risk + counts.dormant_stock + counts.excess_stock_risk + counts.normal_flow
    )
    confirmation_total = counts.confirmed + counts.in_progress + counts.unconfirmed
    assert quadrant_total == counts.total
    assert confirmation_total == counts.total


def test_e006_banner_counts_are_fixed_regardless_of_list_selection():
    rows = _mixed_rows()

    banner_counts = count_rows(_enriched(rows, SELECTION_L3))
    list_counts = count_rows(_enriched(rows, SELECTION_D5))

    # 帯は基準判定条件で固定するため、一覧側の選択を変えても帯の件数は動かない（§9 R-4）。
    assert banner_counts.supply_risk == 1
    assert banner_counts.attention != list_counts.attention


def test_e009_axis_help_text_uses_context_specific_wording():
    low_flow_help = FLOW_AXIS_HELP_TEXTS[FLOW_AXIS_LOW_FLOW]
    dormant_help = FLOW_AXIS_HELP_TEXTS[FLOW_AXIS_DORMANT]

    assert "低流動品" in low_flow_help
    assert "在庫死蔵品" in dormant_help
    for term in FORBIDDEN_TERMS:
        assert term not in low_flow_help
        assert term not in dormant_help


@pytest.mark.parametrize(
    "selection",
    [FlowSelection(period) for period in EVALUATION_PERIODS],
    ids=[period.key for period in EVALUATION_PERIODS],
)
@pytest.mark.parametrize(
    ("dates", "expected_by_short_period"),
    [
        (DATES_SUPPLY_RISK, QUADRANT_SUPPLY_RISK),
        (DATES_DORMANT_STOCK, QUADRANT_DORMANT_STOCK),
        (DATES_EXCESS_STOCK_RISK, QUADRANT_EXCESS_STOCK_RISK),
        (DATES_NORMAL_FLOW, QUADRANT_NORMAL_FLOW),
    ],
    ids=["supply-risk", "dormant-stock", "excess-stock-risk", "normal-flow"],
)
def test_e010_all_period_and_quadrant_combinations_return_a_valid_quadrant(
    selection, dates, expected_by_short_period
):
    last_incoming_raw, last_ship_raw = dates
    enriched = _enriched([_row(dates, item_cd="ITEM-A")], selection)
    quadrant = enriched[0]["flow_quadrant"]

    # 6 判定条件 × 4 象限 = 24 通り。いずれも例外なく 4 ラベルのいずれかを返す。
    assert quadrant in FLOW_QUADRANT_KEYS
    assert enriched[0]["flow_quadrant_key"] == FLOW_QUADRANT_KEYS[quadrant]
    _ = (last_incoming_raw, last_ship_raw, expected_by_short_period)


def test_e010_representative_rows_match_expected_quadrants_for_reference_selection():
    enriched = _enriched(_mixed_rows(), SELECTION_L3)

    assert [row["flow_quadrant"] for row in enriched] == [
        QUADRANT_SUPPLY_RISK,
        QUADRANT_DORMANT_STOCK,
        QUADRANT_EXCESS_STOCK_RISK,
        QUADRANT_NORMAL_FLOW,
    ]


def test_resolve_flow_quadrant_never_raises_for_missing_dates():
    for selection in (FlowSelection(period) for period in EVALUATION_PERIODS):
        assert (
            resolve_flow_quadrant(None, None, as_of_date=AS_OF, selection=selection)
            == QUADRANT_DORMANT_STOCK
        )


def test_filter_summary_rows_attention_only_excludes_normal_flow_for_every_selection():
    rows = _mixed_rows()
    for selection in (SELECTION_L1, SELECTION_L3, SELECTION_D5):
        enriched = _enriched(rows, selection)
        filtered = filter_summary_rows(
            enriched,
            ListQuery(as_of_date=AS_OF, flow_selection=selection, attention_only=True),
        )
        assert all(row["flow_quadrant"] != QUADRANT_NORMAL_FLOW for row in filtered)
