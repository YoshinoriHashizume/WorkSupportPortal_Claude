"""判定材料（FlowFacts）と流動区分の理由のテスト（test-design.md TC-FQR-F-001〜009）。

行（得意先 × 得意先品番）から 在庫の有無・需要の有無・直近入荷の有無 を導き、
流動区分（S-203）の判定根拠となる理由を組み立てる（07 design §2.2）。
"""

from __future__ import annotations

from datetime import date

import pytest

from application.inventory_order_alert.domain.value_objects.flow_facts import (
    FLOW_REASON_INCOMING_BELOW_DEMAND,
    FLOW_REASON_NO_INCOMING_RECORD,
    FLOW_REASON_UNCONFIRMED_WITHOUT_SHIPMENT,
    build_flow_facts,
    flow_reasons,
    row_has_demand,
    row_last_incoming_month_qty,
    row_next_month_demand,
    row_recent_incoming,
    row_stock_missing,
)
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    DEFAULT_FLOW_THRESHOLDS,
    QUADRANT_DISCONTINUATION_CANDIDATE,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
    QUADRANT_STOCKOUT,
    QUADRANT_STOCKOUT_NO_INCOMING,
    EvaluationPeriod,
    FlowFacts,
    FlowSelection,
)

#: 07 テスト設計 §1: 基準日は 2026-09-18 固定。直近入荷の境界は 30 日（8/19 は含む、8/18 は含まない）。
AS_OF = date(2026, 9, 18)


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "cust_code": "100",
        "item_cd": "96160-00500",
        "stock_qty": "",
        "demand_forecast_stock_total": 0.0,
        "demand_forecast_basis": "内示",
        "demand_forecast_current_month_remaining": 0,
        "demand_forecast_monthly": [20, 20, 20],
        "demand_forecast_monthly_average": 20.0,
        "last_incoming_date": "2026/08/25",
        "last_ship_date": "2026/09/01",
        "incoming_trend": [{"month": "2026-08", "qty": 10}, {"month": "2026-09", "qty": 0}],
        "unconfirmed_order_trend": [{"month": "2026-09", "qty": 0}] * 4,
    }
    row.update(overrides)
    return row


# --- TC-FQR-F-001: 在庫の有無 ---


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"stock_qty": "", "demand_forecast_stock_total": None}, True),
        ({"stock_qty": "", "demand_forecast_stock_total": 0.0}, True),
        ({"stock_qty": "", "demand_forecast_stock_total": ""}, True),
        ({"stock_qty": "5"}, False),
        ({"stock_qty": "0"}, False),  # SLIMS に行があり在庫 0 は「在庫あり」扱い（TC-FQR-R-006）
        ({"stock_qty": "", "demand_forecast_stock_total": 3.0}, False),  # 単位内の別品番に在庫がある
    ],
)
def test_fqr_f001_row_stock_missing(overrides, expected):
    assert row_stock_missing(_row(**overrides)) is expected


def test_fqr_f001_row_without_stock_key_is_not_stock_missing():
    """在庫数のキーがない旧行は未取得（`－`）であって在庫なしではない。"""
    row = _row()
    del row["stock_qty"]

    assert row_stock_missing(row) is False


# --- TC-FQR-F-002: 需要の有無 ---


@pytest.mark.parametrize(
    ("basis", "expected"),
    [("内示", True), ("なし", False), ("実績ベース", False)],
)
def test_fqr_f002_row_has_demand_uses_basis_when_present(basis, expected):
    assert row_has_demand(_row(demand_forecast_basis=basis)) is expected


def test_fqr_f002_row_has_demand_falls_back_to_unconfirmed_order_trend():
    """需要予測が付く前の行は内示推移（翌月〜翌々々月）で判定する。"""
    row = _row(unconfirmed_order_trend=[{"month": "2026-09", "qty": 0}, {"month": "2026-10", "qty": 30}])
    del row["demand_forecast_basis"]

    assert row_has_demand(row) is True


def test_fqr_f002_row_has_demand_ignores_current_month_and_shipment_trend():
    """当月（先頭）だけの内示・出荷実績は需要ありにしない（出荷は見ない）。"""
    row = _row(
        unconfirmed_order_trend=[{"month": "2026-09", "qty": 50}, {"month": "2026-10", "qty": 0}],
        shipment_trend=[{"month": "2026-07", "qty": 10}, {"month": "2026-08", "qty": 20}, {"month": "2026-09", "qty": 30}],
    )
    del row["demand_forecast_basis"]

    assert row_has_demand(row) is False


# --- TC-FQR-F-006a/006b: 入荷側・需要側の数量 ---


def test_fqr_f006a_row_last_incoming_month_qty_uses_the_month_of_the_last_incoming():
    """最終入荷日が属する月の合計（当月の入荷が 0 でも前月の実績を見る。REQ-FQR-F-005）。"""
    assert row_last_incoming_month_qty(_row(), as_of_date=AS_OF) == 10


def test_fqr_f006a_row_last_incoming_month_qty_is_zero_without_incoming():
    assert row_last_incoming_month_qty(_row(last_incoming_date=""), as_of_date=AS_OF) == 0
    assert row_last_incoming_month_qty(_row(incoming_trend=[]), as_of_date=AS_OF) == 0


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"demand_forecast_monthly": [0, 320, 290]}, 0),
        ({"demand_forecast_monthly": [20, 20, 20]}, 20),
        ({"demand_forecast_basis": "なし", "demand_forecast_monthly": [20, 20, 20]}, 0),
    ],
)
def test_fqr_f006b_row_next_month_demand(overrides, expected):
    assert row_next_month_demand(_row(**overrides)) == expected


# --- TC-FQR-F-003: 判定材料の組み立て ---


def test_fqr_f003_build_flow_facts():
    facts = build_flow_facts(_row(), as_of_date=AS_OF, thresholds=DEFAULT_FLOW_THRESHOLDS)

    assert facts == FlowFacts(
        last_incoming_date=date(2026, 8, 25),
        last_ship_date=date(2026, 9, 1),
        stock_missing=True,
        has_demand=True,
        recent_incoming=True,
    )


def test_fqr_f003_build_flow_facts_recent_incoming_boundary():
    """8/19 は直近 30 日に含み、8/18 は含まない（TC-FQR-Q-009 と同じ境界）。"""
    facts = build_flow_facts(_row(last_incoming_date="2026/08/19"), as_of_date=AS_OF, thresholds=DEFAULT_FLOW_THRESHOLDS)
    assert facts.recent_incoming is True

    facts = build_flow_facts(_row(last_incoming_date="2026/08/18"), as_of_date=AS_OF, thresholds=DEFAULT_FLOW_THRESHOLDS)
    assert facts.recent_incoming is False


def test_fqr_f003_row_recent_incoming_reads_the_row():
    assert row_recent_incoming(_row(), as_of_date=AS_OF, days=30) is True
    assert row_recent_incoming(_row(last_incoming_date=""), as_of_date=AS_OF, days=30) is False


# --- TC-FQR-F-004〜009: 理由 ---


def _reasons(quadrant: str, *, period_years: int = 1, **overrides: object) -> list[str]:
    row = _row(**overrides)
    facts = build_flow_facts(row, as_of_date=AS_OF, thresholds=DEFAULT_FLOW_THRESHOLDS)
    return flow_reasons(row, quadrant, facts, as_of_date=AS_OF, selection=FlowSelection(EvaluationPeriod(period_years)))


def test_fqr_f004_stockout_no_incoming_without_incoming_record():
    assert FLOW_REASON_NO_INCOMING_RECORD in _reasons(QUADRANT_STOCKOUT_NO_INCOMING, last_incoming_date="")
    assert FLOW_REASON_NO_INCOMING_RECORD not in _reasons(QUADRANT_STOCKOUT_NO_INCOMING)


# --- TC-FQR-F-005: 期間内出荷がない欠品（期間判断は判定期間に一本化。用語集 V-211） ---


def test_fqr_f005_stockout_without_shipment_in_period():
    """判定期間 1 年で期間内出荷がなければ理由が付き、期間を広げて出荷が入れば消える。"""
    old_ship = {"last_ship_date": "2025/05/22"}  # 基準日 2026/09/18 の 1 年より前、5 年内

    assert "1年以上出荷なし・経路要確認" in _reasons(QUADRANT_STOCKOUT, **old_ship)
    assert "5年以上出荷なし・経路要確認" not in _reasons(QUADRANT_STOCKOUT, period_years=5, **old_ship)
    # 期間内に出荷があれば付かない（既定の行は最終出荷 2026/09/01）
    assert not [reason for reason in _reasons(QUADRANT_STOCKOUT) if "出荷なし・経路要確認" in reason]


def test_fqr_f005_reason_is_for_both_stockout_quadrants():
    """出荷が基幹に記録されない経路の疑いは直近入荷の有無と関係しないため、欠品 2 区分に付ける。"""
    old_ship = {"last_ship_date": "2025/05/22"}

    assert "1年以上出荷なし・経路要確認" in _reasons(QUADRANT_STOCKOUT_NO_INCOMING, **old_ship)


def test_fqr_f005a_empty_last_ship_date_counts_as_no_shipment_in_period():
    assert "1年以上出荷なし・経路要確認" in _reasons(QUADRANT_STOCKOUT, last_ship_date="")


@pytest.mark.parametrize(
    "quadrant", [QUADRANT_LOW_FLOW_NO_SHIPMENT, QUADRANT_DISCONTINUATION_CANDIDATE, QUADRANT_NORMAL_FLOW]
)
def test_fqr_f005b_reason_is_not_attached_to_other_quadrants(quadrant):
    reasons = _reasons(quadrant, stock_qty="100", last_ship_date="2025/05/22")

    assert not [reason for reason in reasons if "出荷なし・経路要確認" in reason]


def test_fqr_f006_stockout_incoming_below_next_month_demand():
    # 最終入荷 8/25 の月の入荷 10 < 翌月の内示 20 → 理由あり
    assert FLOW_REASON_INCOMING_BELOW_DEMAND in _reasons(QUADRANT_STOCKOUT)
    # 同月の入荷が翌月の内示以上 → 理由なし
    enough = _reasons(QUADRANT_STOCKOUT, incoming_trend=[{"month": "2026-08", "qty": 20}, {"month": "2026-09", "qty": 0}])
    assert FLOW_REASON_INCOMING_BELOW_DEMAND not in enough
    # 翌月の内示が 0（需要は翌々月から）→ 理由なし
    later = _reasons(QUADRANT_STOCKOUT, demand_forecast_monthly=[0, 320, 290])
    assert FLOW_REASON_INCOMING_BELOW_DEMAND not in later


def test_fqr_f006_incoming_below_demand_is_only_for_stockout():
    assert FLOW_REASON_INCOMING_BELOW_DEMAND not in _reasons(QUADRANT_STOCKOUT_NO_INCOMING)


def test_fqr_f007_low_flow_no_shipment_with_unconfirmed_order():
    assert _reasons(QUADRANT_LOW_FLOW_NO_SHIPMENT, stock_qty="100") == [FLOW_REASON_UNCONFIRMED_WITHOUT_SHIPMENT]
    assert _reasons(QUADRANT_LOW_FLOW_NO_SHIPMENT, stock_qty="100", demand_forecast_basis="なし") == []


def test_fqr_f008_discontinuation_candidate_with_past_phase_out_date():
    assert _reasons(QUADRANT_DISCONTINUATION_CANDIDATE, phase_out_date="2026/03/31") == ["適用終了日 2026/03/31"]
    assert _reasons(QUADRANT_DISCONTINUATION_CANDIDATE, phase_out_date="2026/12/31") == []
    assert _reasons(QUADRANT_DISCONTINUATION_CANDIDATE, phase_out_date="") == []


def test_fqr_f009_normal_flow_has_no_reasons():
    assert _reasons(QUADRANT_NORMAL_FLOW, stock_qty="100") == []
