"""行への流動区分・状況・推奨アクション付与と、絞り込み・既定ソートのテスト（TC-SFV-D-058、D-063）。"""

from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.flow_facts import FLOW_REASON_INCOMING_BELOW_DEMAND
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    FLOW_QUADRANT_KEYS,
    QUADRANT_DISCONTINUATION_CANDIDATE,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_INCOMING,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
    QUADRANT_STOCKOUT,
    QUADRANT_STOCKOUT_NO_INCOMING,
    EvaluationPeriod,
    FlowSelection,
    FlowThresholds,
)
from application.inventory_order_alert.domain.value_objects.list_query import ListQuery, parse_list_query
from application.inventory_order_alert.domain.value_objects.list_rows import (
    apply_flow_quadrants_to_rows,
    filter_summary_rows,
    sort_summary_rows,
)
from application.inventory_order_alert.domain.value_objects.recommended_action import (
    DEFAULT_RECOMMENDED_ACTIONS,
)

#: BOM 基準日（V-209）。2026/09/07 取込の実データに合わせる。
AS_OF = date(2026, 9, 7)

#: 各区分の代表行（判定期間 1 年）。
ROW_LOW_FLOW_NO_INCOMING = ("2025/04/02", "2026/06/15")
ROW_DORMANT_STOCK = ("2025/04/02", "2023/07/27")
ROW_LOW_FLOW_NO_SHIPMENT = ("2026/05/20", "2023/07/27")
ROW_NORMAL_FLOW = ("2026/05/20", "2026/06/15")


def _row(dates: tuple[str, str], *, qty: int = 0, **extra: object) -> dict[str, object]:
    last_incoming_date, last_ship_date = dates
    row: dict[str, object] = {
        "cust_code": "100",
        "item_cd": "96160-00500",
        "last_incoming_date": last_incoming_date,
        "last_ship_date": last_ship_date,
        "post_shipment_total_qty": qty,
    }
    row.update(extra)
    return row


def _query(**params: str) -> ListQuery:
    return parse_list_query(params, today=AS_OF)


def _apply(rows, *, period_years: int = 1, query: ListQuery | None = None):
    return apply_flow_quadrants_to_rows(
        rows,
        as_of_date=AS_OF,
        query=query or _query(period=str(period_years)),
    )


# --- TC-SFV-D-063: 行に状況・推奨アクションが付与される ---


def test_d063_low_flow_no_incoming_row_gets_status_action_and_department():
    [row] = _apply([_row(ROW_LOW_FLOW_NO_INCOMING)])
    expected = DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_LOW_FLOW_NO_INCOMING)

    assert row["flow_quadrant"] == QUADRANT_LOW_FLOW_NO_INCOMING
    assert row["flow_quadrant_key"] == FLOW_QUADRANT_KEYS[QUADRANT_LOW_FLOW_NO_INCOMING]
    assert "最終入荷 2025/04/02" in row["flow_status"]
    assert "1年" in row["flow_status"]
    assert "{" not in row["flow_status"]
    assert row["recommended_action"] == expected.action
    assert row["responsible_department"] == "調達G・営業G・生産管理"


def test_d063_status_follows_selected_evaluation_period():
    [row] = _apply([_row(ROW_LOW_FLOW_NO_INCOMING)], period_years=5)

    # 5 年では最終入荷 2025/04/02 は期間内なので通常流動品になり、状況は空
    assert row["flow_quadrant"] == QUADRANT_NORMAL_FLOW
    assert row["flow_status"] == ""


def test_d063_dormant_stock_status_mentions_both_dates():
    [row] = _apply([_row(ROW_DORMANT_STOCK)])

    assert row["flow_quadrant"] == QUADRANT_DORMANT_STOCK
    assert "2025/04/02" in row["flow_status"]
    assert "2023/07/27" in row["flow_status"]
    assert row["recommended_action"] == DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_DORMANT_STOCK).action
    assert row["responsible_department"] == "調達G"


def test_d063_low_flow_no_shipment_status_mentions_last_ship():
    [row] = _apply([_row(ROW_LOW_FLOW_NO_SHIPMENT)])

    assert row["flow_quadrant"] == QUADRANT_LOW_FLOW_NO_SHIPMENT
    assert "2023/07/27" in row["flow_status"]
    assert row["responsible_department"] == "営業G"


def test_d063_normal_flow_row_has_empty_status_and_action():
    [row] = _apply([_row(ROW_NORMAL_FLOW)])

    assert row["flow_quadrant"] == QUADRANT_NORMAL_FLOW
    assert row["flow_status"] == ""
    assert row["recommended_action"] == ""
    assert row["responsible_department"] == "生産管理"


def test_d063_no_incoming_record_uses_wording_instead_of_date():
    [row] = _apply([_row(("", "2026/06/15"))])

    assert row["flow_quadrant"] == QUADRANT_LOW_FLOW_NO_INCOMING
    assert row["no_incoming_record"] is True
    assert "入荷実績なし" in row["flow_status"]
    assert "{last_incoming}" not in row["flow_status"]


def test_d063_overridden_recommended_actions_are_used():
    overridden = DEFAULT_RECOMMENDED_ACTIONS.with_action_texts(
        {FLOW_QUADRANT_KEYS[QUADRANT_LOW_FLOW_NO_INCOMING]: "上書き文言"}
    )

    [row] = apply_flow_quadrants_to_rows(
        [_row(ROW_LOW_FLOW_NO_INCOMING)],
        as_of_date=AS_OF,
        query=_query(period="1"),
        recommended_actions=overridden,
    )

    assert row["recommended_action"] == "上書き文言"


def test_d063_flow_quadrants_matrix_uses_year_keys():
    [row] = _apply([_row(ROW_LOW_FLOW_NO_INCOMING)])

    assert set(row["flow_quadrants"]) == {"Y1", "Y3", "Y5"}
    assert row["flow_quadrants"]["Y1"] == FLOW_QUADRANT_KEYS[QUADRANT_LOW_FLOW_NO_INCOMING]
    assert row["flow_quadrants"]["Y3"] == FLOW_QUADRANT_KEYS[QUADRANT_NORMAL_FLOW]


def test_d063_does_not_mutate_input_rows():
    source = _row(ROW_LOW_FLOW_NO_INCOMING)
    _apply([source])

    assert "flow_status" not in source
    assert "flow_quadrant" not in source


# --- 絞り込み: 新キー・旧キー ---


def _four_rows() -> list[dict[str, object]]:
    return _apply(
        [
            _row(ROW_NORMAL_FLOW, qty=10),
            _row(ROW_LOW_FLOW_NO_SHIPMENT, qty=20),
            _row(ROW_DORMANT_STOCK, qty=30),
            _row(ROW_LOW_FLOW_NO_INCOMING, qty=40),
        ]
    )


def test_filter_by_new_key_keeps_only_that_quadrant():
    filtered = filter_summary_rows(_four_rows(), _query(flow_quadrant="low-flow-no-incoming"))

    assert [row["flow_quadrant"] for row in filtered] == [QUADRANT_LOW_FLOW_NO_INCOMING]


def test_filter_by_legacy_key_is_mapped_to_new_quadrant():
    filtered = filter_summary_rows(_four_rows(), _query(flow_quadrant="supply-risk"))

    assert [row["flow_quadrant"] for row in filtered] == [QUADRANT_LOW_FLOW_NO_INCOMING]

    filtered = filter_summary_rows(_four_rows(), _query(flow_quadrant="excess-stock-risk"))

    assert [row["flow_quadrant"] for row in filtered] == [QUADRANT_LOW_FLOW_NO_SHIPMENT]


def test_filter_attention_only_excludes_normal_flow():
    filtered = filter_summary_rows(_four_rows(), _query(attentionOnly="true"))

    assert QUADRANT_NORMAL_FLOW not in {row["flow_quadrant"] for row in filtered}
    assert len(filtered) == 3


# --- TC-SFV-D-058: ソート既定はランク → 出荷数量降順 ---


def test_d058_default_sort_is_rank_then_shipment_qty_desc():
    rows = _four_rows() + _apply([_row(ROW_LOW_FLOW_NO_INCOMING, qty=99)])

    ordered = sort_summary_rows(rows)

    assert [row["flow_quadrant"] for row in ordered] == [
        QUADRANT_LOW_FLOW_NO_INCOMING,
        QUADRANT_LOW_FLOW_NO_INCOMING,
        QUADRANT_DORMANT_STOCK,
        QUADRANT_LOW_FLOW_NO_SHIPMENT,
        QUADRANT_NORMAL_FLOW,
    ]
    assert [row["post_shipment_total_qty"] for row in ordered[:2]] == [99, 40]


def test_d058_sort_treats_legacy_label_by_its_new_rank():
    rows = [
        {"flow_quadrant": QUADRANT_NORMAL_FLOW, "post_shipment_total_qty": 0},
        {"flow_quadrant": "供給リスク品", "post_shipment_total_qty": 0},
        {"flow_quadrant": "在庫過剰リスク品", "post_shipment_total_qty": 0},
    ]

    ordered = sort_summary_rows(rows)

    assert [row["flow_quadrant"] for row in ordered] == ["供給リスク品", "在庫過剰リスク品", QUADRANT_NORMAL_FLOW]


def test_selection_object_is_usable_directly():
    query = ListQuery(as_of_date=AS_OF, flow_selection=FlowSelection(EvaluationPeriod(3)))
    [row] = apply_flow_quadrants_to_rows([_row(ROW_LOW_FLOW_NO_INCOMING)], as_of_date=AS_OF, query=query)

    assert row["flow_quadrant"] == QUADRANT_NORMAL_FLOW
    assert row["flow_status"] == ""


# --- TC-FQR-L-001〜005: 在庫なしの 3 区分・理由・並び・絞り込み（07） ---


def _stock_missing_row(dates: tuple[str, str], **extra: object) -> dict[str, object]:
    """SLIMS 在庫なし（該当なし）の行。需要予測は付与済みの想定。"""
    row = _row(dates, stock_qty="", demand_forecast_stock_total=0.0)
    row.update(extra)
    return row


def test_fqr_l001_stock_missing_with_demand_and_recent_incoming_is_stockout():
    [row] = _apply(
        [
            _stock_missing_row(
                ("2026/09/01", "2026/06/15"),
                demand_forecast_basis="内示",
                demand_forecast_monthly=[20, 20, 20],
                incoming_trend=[{"month": "2026-09", "qty": 10}],
            )
        ]
    )

    assert row["flow_quadrant"] == QUADRANT_STOCKOUT
    assert row["flow_quadrant_key"] == "stockout"
    # 欠品・打ち切り候補は判定期間によらないので 3 キーとも同値（TC-FQR-Q-005）
    assert set(row["flow_quadrants"].values()) == {"stockout"}
    assert row["flow_reasons"] == [FLOW_REASON_INCOMING_BELOW_DEMAND]
    assert "在庫なし・入荷はあるが在庫が残らない" in row["flow_status"]


def test_fqr_l001_stock_missing_without_recent_incoming_is_stockout_no_incoming():
    [row] = _apply([_stock_missing_row(("2026/06/01", "2026/06/15"), demand_forecast_basis="内示")])

    assert row["flow_quadrant"] == QUADRANT_STOCKOUT_NO_INCOMING
    assert row["flow_reasons"] == []
    assert "直近 30 日入荷なし" in row["flow_status"]


def test_fqr_l002_stock_missing_without_demand_is_discontinuation_candidate():
    [row] = _apply(
        [_stock_missing_row(("2026/09/01", "2023/07/27"), demand_forecast_basis="なし", phase_out_date="2026/03/31")]
    )

    assert row["flow_quadrant"] == QUADRANT_DISCONTINUATION_CANDIDATE
    assert row["flow_status"] == "在庫なし・内示なし（最終出荷 2023/07/27）"
    assert row["recommended_action"] == DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_DISCONTINUATION_CANDIDATE).action
    assert row["responsible_department"] == "営業G"
    assert row["flow_reasons"] == ["適用終了日 2026/03/31"]


def test_fqr_l003_legacy_row_without_stock_key_keeps_the_four_quadrants():
    """在庫数のキーがない旧スナップショットは未取得。欠品・打ち切り候補にしない。"""
    [row] = _apply([_row(ROW_DORMANT_STOCK)])

    assert row["flow_quadrant"] == QUADRANT_DORMANT_STOCK
    assert row["flow_reasons"] == []


def test_fqr_l004_default_sort_puts_stockout_before_low_flow():
    rows = _apply(
        [
            _row(ROW_LOW_FLOW_NO_INCOMING, qty=40),
            _stock_missing_row(("", "2026/06/15"), demand_forecast_basis="内示"),
        ]
    )

    ordered = sort_summary_rows(rows)

    assert [row["flow_quadrant"] for row in ordered] == [QUADRANT_STOCKOUT_NO_INCOMING, QUADRANT_LOW_FLOW_NO_INCOMING]


def test_fqr_l005_filter_by_stockout_key():
    rows = _apply(
        [
            _row(ROW_NORMAL_FLOW, qty=10),
            _stock_missing_row(("2026/09/01", "2026/06/15"), demand_forecast_basis="内示"),
        ]
    )

    filtered = filter_summary_rows(rows, _query(flow_quadrant="stockout"))

    assert [row["flow_quadrant"] for row in filtered] == [QUADRANT_STOCKOUT]


def test_fqr_l006_rows_carry_reasons_for_every_evaluation_period():
    """理由は判定期間で変わるため、区分と同じく 3 期間ぶん持たせる（07 design §1-6）。"""
    [row] = _apply(
        [
            _stock_missing_row(
                ("2026/09/01", "2025/08/20"),  # 最終出荷は 1 年より前・3 年内
                demand_forecast_basis="内示",
                demand_forecast_monthly=[20, 20, 20],
                incoming_trend=[{"month": "2026-09", "qty": 100}],
            )
        ]
    )

    assert set(row["flow_reasons_by_period"]) == {"Y1", "Y3", "Y5"}
    assert row["flow_reasons_by_period"]["Y1"] == ["1年以上出荷なし・経路要確認"]
    assert row["flow_reasons_by_period"]["Y3"] == []
    assert row["flow_reasons_by_period"]["Y5"] == []
    # 表示中の判定期間（既定 1 年）の理由は flow_reasons に入る
    assert row["flow_reasons"] == ["1年以上出荷なし・経路要確認"]


def test_fqr_l007_period_dependent_reason_follows_the_quadrant():
    """低流動品（出荷なし）は期間を広げると通常流動品になり、理由も消える（古い理由が残らない）。"""
    [row] = _apply([_row(ROW_LOW_FLOW_NO_SHIPMENT, stock_qty="100", demand_forecast_basis="内示")])

    assert row["flow_quadrants"]["Y1"] == FLOW_QUADRANT_KEYS[QUADRANT_LOW_FLOW_NO_SHIPMENT]
    assert row["flow_reasons_by_period"]["Y1"] == ["内示あり（立ち上がり／出荷経路要確認）"]
    assert row["flow_quadrants"]["Y5"] == FLOW_QUADRANT_KEYS[QUADRANT_NORMAL_FLOW]
    assert row["flow_reasons_by_period"]["Y5"] == []


def test_fqr_l001_thresholds_change_the_recent_incoming_boundary():
    """直近入荷の窓を広げると 欠品（入荷なし）が 欠品 になる（第 2 段階の設定に備える）。"""
    # 最終入荷 2026/07/01 は基準日 2026/09/07 の 68 日前。既定 30 日では直近入荷なし、90 日なら直近入荷あり
    rows = [_stock_missing_row(("2026/07/01", "2026/06/15"), demand_forecast_basis="内示")]

    [default_row] = apply_flow_quadrants_to_rows(rows, as_of_date=AS_OF, query=_query(period="1"))
    [widened] = apply_flow_quadrants_to_rows(
        rows,
        as_of_date=AS_OF,
        query=_query(period="1"),
        thresholds=FlowThresholds(recent_incoming_days=90),
    )

    assert default_row["flow_quadrant"] == QUADRANT_STOCKOUT_NO_INCOMING
    assert widened["flow_quadrant"] == QUADRANT_STOCKOUT
