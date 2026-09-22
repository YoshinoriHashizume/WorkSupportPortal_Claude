"""在庫切れリスク（S-204）のテスト（TC-SOR-D-020〜054、D-045〜049a）。"""

from __future__ import annotations

from datetime import date

import pytest

from application.inventory_order_alert.domain.value_objects import stockout_risk
from application.inventory_order_alert.domain.value_objects.demand_forecast import (
    BASIS_NONE,
    BASIS_UNCONFIRMED,
    NO_DEMAND,
    DemandForecast,
)
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    QUADRANT_DISCONTINUATION_CANDIDATE,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_INCOMING,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_NORMAL_FLOW,
    QUADRANT_STOCKOUT,
    QUADRANT_STOCKOUT_NO_INCOMING,
)
from application.inventory_order_alert.domain.value_objects.open_purchase_order import ReplenishmentOutlook
from application.inventory_order_alert.domain.value_objects.ordering_profile import (
    LEAD_TIME_SOURCE_DEFAULT,
    LEAD_TIME_SOURCE_MASTER,
    ORDERING_MANUAL,
    ORDERING_MRP,
    ORDERING_UNKNOWN,
)
from application.inventory_order_alert.domain.value_objects.stockout_risk import (
    REASON_LEAD_TIME_DEFAULT,
    REASON_LEVEL1_UNRESOLVED,
    REASON_MAYBE_FORGOTTEN,
    REASON_OVERDUE,
    REASON_QTY_SHORT,
    REASON_RAMP_UP,
    REASON_RECENT_INCOMING,
    REASON_REPLENISHMENT_UNKNOWN,
    REASON_STOCK_MISSING,
    REASON_SUPPLIER_CHECK_FIRST,
    REASON_SUPPLY_DELAY,
    REASON_UPSTREAM_ORDER,
    REASON_WITHIN_LEAD_TIME,
    RISK_CAUTION,
    RISK_DANGER,
    RISK_NONE,
    RISK_WATCH,
    STOCKOUT_RISK_KEYS,
    STOCKOUT_RISK_RANK,
    STOCKOUT_RISKS,
    OrderingProfile,
    StockoutRiskSettings,
    _forecast_of,
    assess_stockout_risk,
    attach_stockout_risk,
    days_until_stockout,
    demand_until_month,
    shortage_qty,
)

AS_OF = date(2026, 9, 17)
SETTINGS = StockoutRiskSettings()
FORECAST = DemandForecast(basis=BASIS_UNCONFIRMED, current_month_remaining=100, monthly=(200, 200, 200), monthly_average=200.0)
PROFILE_MRP = OrderingProfile(lead_time_days=5, lead_time_source=LEAD_TIME_SOURCE_MASTER, ordering_method=ORDERING_MRP)
PROFILE_MANUAL = OrderingProfile(lead_time_days=5, lead_time_source=LEAD_TIME_SOURCE_MASTER, ordering_method=ORDERING_MANUAL)
PROFILE_UNKNOWN = OrderingProfile(lead_time_days=5, lead_time_source=LEAD_TIME_SOURCE_MASTER, ordering_method=ORDERING_UNKNOWN)


def _outlook(qty: int = 0, *, overdue: bool = False, unknown: bool = False, later_qty: int = 0, stale_qty: int = 0) -> ReplenishmentOutlook:
    return ReplenishmentOutlook(qty=qty, later_qty=later_qty, earliest_due=None, has_overdue=overdue, unknown=unknown, stale_qty=stale_qty)


def _assess(**overrides):
    params = {
        "forecast": FORECAST,
        "stock_total": 500.0,
        "stockout_month": "2026-12",
        "outlook": _outlook(0),
        "profile": PROFILE_MRP,
        "flow_quadrant": QUADRANT_NORMAL_FLOW,
        "level1_resolved": True,
        "settings": SETTINGS,
        "as_of_date": AS_OF,
        "last_incoming_date": None,
    }
    params.update(overrides)
    return assess_stockout_risk(**params)


# --- TC-SOR-D-020〜023: 猶予日数・需要・不足数量 ---


@pytest.mark.parametrize("month, expected", [("2026-09", 0), ("2026-10", 14), ("2027-01", 106), (None, None), ("", None)])
def test_d020_days_until_stockout(month, expected):
    assert days_until_stockout(AS_OF, month) == expected


def test_d021_demand_until_month_sums_current_remaining_and_monthly():
    assert demand_until_month(FORECAST, as_of_date=AS_OF, stockout_month="2026-12") == 700


def test_d022_demand_until_month_uses_average_after_third_month():
    assert demand_until_month(FORECAST, as_of_date=AS_OF, stockout_month="2027-02") == 100 + 600 + 200 * 2


def test_d022_demand_until_current_month_is_current_remaining_only():
    assert demand_until_month(FORECAST, as_of_date=AS_OF, stockout_month="2026-09") == 100


def test_d023_shortage_qty():
    assert shortage_qty(700, 500.0) == 200
    assert shortage_qty(700, 1000.0) == 0
    assert shortage_qty(700, None) is None


# --- TC-SOR-D-030〜039: 判定 ---


def test_d030_no_demand_is_watch():
    result = _assess(forecast=DemandForecast(basis=BASIS_NONE, current_month_remaining=0, monthly=(0, 0, 0), monthly_average=0.0), stockout_month=None)

    assert result.risk == RISK_WATCH
    assert result.reasons == ()
    assert result.days_until_stockout is None


def test_d031_stockout_beyond_watch_months_is_watch():
    assert _assess(stockout_month="2027-05").risk == RISK_WATCH  # 6 か月後は 2027-03
    assert _assess(stockout_month="2027-04").risk == RISK_WATCH
    assert _assess(stockout_month="2027-03").risk != RISK_WATCH


def test_d032_stock_not_fetched_is_watch():
    assert _assess(stock_total=None).risk == RISK_WATCH


def test_d033_unknown_outlook_is_caution_with_reason():
    result = _assess(outlook=_outlook(unknown=True))

    assert result.risk == RISK_CAUTION
    assert REASON_REPLENISHMENT_UNKNOWN in result.reasons


def test_d034_within_lead_time_without_replenishment_is_danger():
    result = _assess(stockout_month="2026-09", outlook=_outlook(0))

    assert result.risk == RISK_DANGER
    assert REASON_WITHIN_LEAD_TIME in result.reasons
    assert result.days_until_stockout == 0


def test_d035_danger_boundary_is_lead_time_plus_safety_days():
    # 猶予 = LT 5 + 安全 14 = 19 日 → 危険。20 日 → 注意
    boundary = date(2026, 10, 1)
    as_of_19 = date(2026, 9, 12)
    as_of_20 = date(2026, 9, 11)
    assert (boundary - as_of_19).days == 19 and (boundary - as_of_20).days == 20

    assert _assess(stockout_month="2026-10", as_of_date=as_of_19).risk == RISK_DANGER
    assert _assess(stockout_month="2026-10", as_of_date=as_of_20, profile=PROFILE_MANUAL).risk == RISK_CAUTION
    # MRP 発注は発注期限が先なら対象外（2026/09/21）
    assert _assess(stockout_month="2026-10", as_of_date=as_of_20, profile=PROFILE_MRP).risk == RISK_NONE


@pytest.mark.parametrize("profile", [PROFILE_MANUAL, PROFILE_UNKNOWN])
def test_d036_no_replenishment_with_time_left_is_caution_for_manual_or_unknown(profile):
    result = _assess(stockout_month="2026-12", outlook=_outlook(0), profile=profile)

    assert result.risk == RISK_CAUTION
    assert REASON_WITHIN_LEAD_TIME not in result.reasons


def test_d047_mrp_with_time_left_and_no_orders_is_none():
    """MRP 発注で発注期限（在庫切れ予測 − LT − 安全日数）が先・発注残なしは所要量計算の起票前の正常状態 → 対象外（2026/09/21）。"""
    result = _assess(stockout_month="2026-12", outlook=_outlook(0), profile=PROFILE_MRP)

    assert result.risk == RISK_NONE
    assert result.reasons == ()


@pytest.mark.parametrize("quadrant", [QUADRANT_LOW_FLOW_NO_INCOMING, QUADRANT_DORMANT_STOCK, QUADRANT_LOW_FLOW_NO_SHIPMENT])
def test_d048a_mrp_deferral_applies_only_to_normal_flow(quadrant):
    """対応要 3 区分は発注前に仕入先の生産可否確認が要るため、MRP でも注意に残す（受け入れ基準 1・UC-04）。上流の納期超過も同様。"""
    assert _assess(stockout_month="2026-12", outlook=_outlook(0), profile=PROFILE_MRP, flow_quadrant=quadrant).risk == RISK_CAUTION
    upstream_overdue = ReplenishmentOutlook(qty=0, later_qty=0, earliest_due=None, has_overdue=False, upstream_qty=240, upstream_overdue=True)
    assert _assess(stockout_month="2026-12", outlook=upstream_overdue, profile=PROFILE_MRP).risk == RISK_CAUTION


def test_d048_mrp_deferral_does_not_apply_with_overdue_or_short_orders():
    assert _assess(stockout_month="2026-12", outlook=_outlook(0, overdue=True, stale_qty=30), profile=PROFILE_MRP).risk == RISK_CAUTION
    assert _assess(stockout_month="2026-12", outlook=_outlook(100), profile=PROFILE_MRP).risk == RISK_CAUTION  # 不足 200


def test_d037_short_quantity_is_caution():
    result = _assess(stockout_month="2026-12", outlook=_outlook(100))  # 不足 200

    assert result.risk == RISK_CAUTION
    assert REASON_QTY_SHORT in result.reasons
    assert result.shortage_qty == 200


def test_d038_overdue_replenishment_is_caution_even_if_enough():
    result = _assess(stockout_month="2026-12", outlook=_outlook(300, overdue=True))

    assert result.risk == RISK_CAUTION
    assert REASON_OVERDUE in result.reasons
    assert REASON_QTY_SHORT not in result.reasons


def test_d039_enough_replenishment_is_none():
    result = _assess(stockout_month="2026-12", outlook=_outlook(200))  # 不足 200 と同じ

    assert result.risk == RISK_NONE
    assert result.reasons == ()


def test_d045_short_replenishment_within_lead_time_is_danger():
    """猶予 0 で発注残が不足数量に満たなければ危険（2026/09/21 改訂: 従来は qty 0 のみ危険）。在庫 50 < 当月残 100。"""
    result = _assess(stockout_month="2026-09", stock_total=50.0, outlook=_outlook(10))

    assert result.risk == RISK_DANGER
    assert REASON_QTY_SHORT in result.reasons
    assert REASON_WITHIN_LEAD_TIME in result.reasons
    # 不足数量をちょうど満たせば対象外
    assert _assess(stockout_month="2026-09", stock_total=50.0, outlook=_outlook(50)).risk == RISK_NONE


def test_d046_only_stale_overdue_order_within_lead_time_is_danger():
    """唯一の発注残が長期納期超過（補充に数えない）→ 発注残なしと同じく危険。理由「納期遅れ」（F-014 #11、2026/09/21）。"""
    result = _assess(stockout_month="2026-09", outlook=_outlook(0, overdue=True, stale_qty=400), profile=PROFILE_MANUAL)

    assert result.risk == RISK_DANGER
    assert REASON_OVERDUE in result.reasons
    assert REASON_WITHIN_LEAD_TIME in result.reasons
    assert REASON_MAYBE_FORGOTTEN not in result.reasons  # 発注残はある


# --- TC-SOR-D-040〜044: 理由 ---


def test_d040_manual_ordering_without_replenishment_flags_forgotten_order():
    result = _assess(stockout_month="2026-12", profile=PROFILE_MANUAL, outlook=_outlook(0))

    assert REASON_MAYBE_FORGOTTEN in result.reasons
    assert REASON_MAYBE_FORGOTTEN not in _assess(stockout_month="2026-09", profile=PROFILE_MRP).reasons


def test_d049a_forgotten_order_reason_requires_no_orders_at_all():
    """補充期限より後の発注残や長期納期超過があれば「発注忘れ」ではない（F-006、F-014 #5。2026/09/21）。"""
    later = _assess(stockout_month="2026-12", profile=PROFILE_MANUAL, outlook=_outlook(0, later_qty=100))
    stale = _assess(stockout_month="2026-12", profile=PROFILE_MANUAL, outlook=_outlook(0, overdue=True, stale_qty=100))

    assert later.risk == RISK_CAUTION and REASON_MAYBE_FORGOTTEN not in later.reasons
    assert stale.risk == RISK_CAUTION and REASON_MAYBE_FORGOTTEN not in stale.reasons


@pytest.mark.parametrize("quadrant", [QUADRANT_LOW_FLOW_NO_INCOMING, QUADRANT_DORMANT_STOCK])
def test_d041_long_no_incoming_flags_supplier_check(quadrant):
    result = _assess(stockout_month="2026-12", flow_quadrant=quadrant, profile=PROFILE_MANUAL)

    assert REASON_SUPPLIER_CHECK_FIRST in result.reasons
    assert result.reasons[0] == REASON_SUPPLIER_CHECK_FIRST  # 先に確認する理由を先頭に


def test_d042_ramp_up_item_flag():
    result = _assess(stockout_month="2026-12", flow_quadrant=QUADRANT_LOW_FLOW_NO_SHIPMENT, profile=PROFILE_MANUAL)

    assert REASON_RAMP_UP in result.reasons


def test_d043_other_reasons():
    default_profile = OrderingProfile(lead_time_days=5, lead_time_source=LEAD_TIME_SOURCE_DEFAULT, ordering_method=ORDERING_MANUAL)
    result = _assess(stockout_month="2026-12", profile=default_profile, level1_resolved=False)
    assert REASON_LEAD_TIME_DEFAULT in result.reasons
    assert REASON_LEVEL1_UNRESOLVED in result.reasons


# --- TC-FQR-R-007/008: 実績ベースの撤去（07 REQ-FQR-F-002） ---


def test_fqr_r007_demand_without_unconfirmed_order_is_watch_without_actual_basis_reason():
    """在庫あり・内示なし（出荷推移があっても）は 需要予測 なし → 監視・理由なし。理由「需要は実績ベース」は廃止。"""
    result = _assess(forecast=NO_DEMAND, stockout_month="2026-12", profile=PROFILE_MANUAL)

    assert result.risk == RISK_WATCH
    assert result.reasons == ()
    assert not hasattr(stockout_risk, "REASON_ACTUAL_BASIS")


def test_fqr_r008_legacy_actual_basis_snapshot_is_read_as_no_demand():
    """旧スナップショットの算出根拠「実績ベース」は 需要なし として読む（監視に落ちる）。"""
    row = {
        "demand_forecast_basis": "実績ベース",
        "demand_forecast_current_month_remaining": 0,
        "demand_forecast_monthly": [200, 200, 200],
        "demand_forecast_monthly_average": 200.0,
    }

    assert _forecast_of(row) == NO_DEMAND


# --- TC-FQR-R-001〜006: 在庫なし（欠品）の判定（07 design §2.6） ---


def test_fqr_r001_stock_missing_within_lead_time_is_danger_even_with_recent_incoming():
    """在庫なし・猶予 0・発注残なしは、直近入荷があっても危険（補充サイクルの免除は在庫ありのみ）。"""
    result = _assess(
        stockout_month="2026-09",
        stock_total=0.0,
        outlook=_outlook(0),
        profile=PROFILE_MRP,
        flow_quadrant=QUADRANT_STOCKOUT,
        stock_missing=True,
        recent_incoming=True,
        last_incoming_date=date(2026, 9, 10),
    )

    assert result.risk == RISK_DANGER
    assert result.reasons[:2] == (REASON_STOCK_MISSING, REASON_SUPPLY_DELAY)
    assert REASON_RECENT_INCOMING not in result.reasons


def test_fqr_r002_stock_missing_with_enough_replenishment_is_caution():
    """在庫なしは補充見込みが足りていても対象外にしない（在庫が切れている事実は残る）。"""
    result = _assess(
        stockout_month="2026-12",
        stock_total=0.0,
        outlook=_outlook(1000),
        profile=PROFILE_MANUAL,
        flow_quadrant=QUADRANT_STOCKOUT_NO_INCOMING,
        stock_missing=True,
    )

    assert result.risk == RISK_CAUTION
    assert result.reasons[0] == REASON_STOCK_MISSING
    assert REASON_SUPPLY_DELAY not in result.reasons


def test_fqr_r003_stock_missing_with_short_replenishment_within_lead_time_is_danger():
    result = _assess(
        stockout_month="2026-09",
        stock_total=0.0,
        outlook=_outlook(10),
        profile=PROFILE_MANUAL,
        flow_quadrant=QUADRANT_STOCKOUT_NO_INCOMING,
        stock_missing=True,
    )

    assert result.risk == RISK_DANGER
    assert REASON_QTY_SHORT in result.reasons


def test_fqr_r003a_stock_missing_with_time_left_is_caution_even_for_mrp():
    """MRP 先送り（対象外）は在庫ありの行のみ。在庫なしは注意に残す（2026/09/21）。"""
    result = _assess(
        stockout_month="2026-11",
        stock_total=0.0,
        outlook=_outlook(0),
        profile=PROFILE_MRP,
        flow_quadrant=QUADRANT_STOCKOUT_NO_INCOMING,
        stock_missing=True,
    )

    assert result.risk == RISK_CAUTION
    assert result.reasons[0] == REASON_STOCK_MISSING


def test_fqr_r003b_stock_missing_with_upstream_order_in_flight_is_caution():
    """上流工程に補充期限内の発注残があれば、欠品でも今すぐ手を打つ行ではない（注意）。"""
    upstream = ReplenishmentOutlook(qty=0, later_qty=0, earliest_due=None, has_overdue=False, upstream_qty=500, upstream_pending_qty=500)
    result = _assess(
        stockout_month="2026-09",
        stock_total=0.0,
        outlook=upstream,
        profile=PROFILE_MANUAL,
        flow_quadrant=QUADRANT_STOCKOUT,
        stock_missing=True,
        recent_incoming=True,
    )

    assert result.risk == RISK_CAUTION
    assert REASON_UPSTREAM_ORDER in result.reasons


def test_fqr_r004_stock_present_keeps_the_replenishment_cycle_exemption():
    """在庫ありの MRP 行は従来どおり直近入荷で免除（危険にしない）。手動発注なら危険。"""
    mrp = _assess(stockout_month="2026-09", outlook=_outlook(0), profile=PROFILE_MRP, last_incoming_date=date(2026, 9, 10))
    manual = _assess(stockout_month="2026-09", outlook=_outlook(0), profile=PROFILE_MANUAL, last_incoming_date=date(2026, 9, 10))

    assert mrp.risk == RISK_CAUTION
    assert REASON_RECENT_INCOMING in mrp.reasons
    assert REASON_STOCK_MISSING not in mrp.reasons
    assert manual.risk == RISK_DANGER


def test_fqr_r005_stock_missing_without_demand_is_watch():
    result = _assess(
        forecast=NO_DEMAND,
        stock_total=0.0,
        stockout_month=None,
        flow_quadrant=QUADRANT_DISCONTINUATION_CANDIDATE,
        stock_missing=True,
    )

    assert result.risk == RISK_WATCH
    assert result.reasons == ()


def test_d044_watch_and_none_have_no_reasons():
    assert _assess(stockout_month="2027-06", profile=PROFILE_MANUAL, flow_quadrant=QUADRANT_DORMANT_STOCK).reasons == ()
    assert _assess(stockout_month="2026-12", outlook=_outlook(500), profile=PROFILE_MANUAL).reasons == ()


# --- TC-SOR-D-050〜054: attach・ランク・設定 ---


def _row(cust: str, item: str, *, stock: str | None = "500", level1=("X-9065", "9065"), orders=None, **extra):
    row: dict[str, object] = {
        "cust_code": cust,
        "item_cd": item,
        "internal_item_cd": level1[0],
        "level1_item_cd": level1[0],
        "level1_vend_cd": level1[1],
        "flow_quadrant": QUADRANT_LOW_FLOW_NO_INCOMING,
        "demand_forecast_basis": BASIS_UNCONFIRMED,
        "demand_forecast_current_month_remaining": 100,
        "demand_forecast_monthly": [200, 200, 200],
        "demand_forecast_monthly_average": 200.0,
        "demand_forecast_stock_total": 500.0,
        "stockout_forecast_month": "2026-12",
        "lead_time_days": 5,
        "lead_time_source": LEAD_TIME_SOURCE_MASTER,
        "ordering_method": ORDERING_MANUAL,
    }
    if stock is not None:
        row["stock_qty"] = stock
    if orders is not None:
        row["open_purchase_orders"] = orders
    row.update(extra)
    return row


def test_d050_attach_assesses_per_unit_and_copies_to_all_rows():
    orders = [{"item_cd": "X-9065", "vend_cd": "9065", "due_date": "2026/10/05", "remaining_qty": 50}]
    rows = [_row("100", "A", orders=orders), _row("137", "A", orders=orders), _row("137", "B", orders=[])]

    enriched = attach_stockout_risk(rows, AS_OF, settings=SETTINGS)

    assert [r["stockout_risk"] for r in enriched] == [RISK_CAUTION] * 3
    assert {r["replenishment_qty"] for r in enriched} == {50}  # 重複明細は 1 回
    assert {r["shortage_qty"] for r in enriched} == {200}
    assert {r["days_until_stockout"] for r in enriched} == {75}
    assert all(REASON_QTY_SHORT in r["stockout_risk_reasons"] for r in enriched)
    assert all(REASON_SUPPLIER_CHECK_FIRST in r["stockout_risk_reasons"] for r in enriched)
    assert enriched[0]["replenishment_earliest_due"] == "2026/10/05"
    assert enriched[0]["replenishment_has_overdue"] is False
    assert enriched[0]["replenishment_unknown"] is False


def test_d050a_attach_separates_stale_overdue_orders_and_exposes_stale_qty():
    """長期納期超過（LT 5 + 安全 14 = 19 日超）の発注残は補充に数えず `replenishment_stale_qty` に出す。猶予 0 なら危険。"""
    orders = [
        {"order_cd": "PO-1", "item_cd": "X-9065", "vend_cd": "9065", "due_date": "2026/06/01", "remaining_qty": 400},
        {"order_cd": "PO-2", "item_cd": "X-9065", "vend_cd": "9065", "due_date": "2026/09/10", "remaining_qty": 5},
    ]
    row = _row("100", "A", orders=orders, stockout_forecast_month="2026-09", demand_forecast_stock_total=50.0, stock="50")

    [enriched] = attach_stockout_risk([row], AS_OF, settings=SETTINGS)

    assert enriched["stockout_risk"] == RISK_DANGER
    assert enriched["replenishment_qty"] == 5
    assert enriched["replenishment_stale_qty"] == 400
    assert enriched["replenishment_has_overdue"] is True
    assert REASON_OVERDUE in enriched["stockout_risk_reasons"]
    assert REASON_QTY_SHORT in enriched["stockout_risk_reasons"]
    assert REASON_MAYBE_FORGOTTEN not in enriched["stockout_risk_reasons"]


def test_d050b_attach_counts_orders_due_by_deadline_not_month_end():
    """補充期限 = 予測月の 1 日 ＋ 安全日数（12/15）。12/16 納期は補充に数えない（2026/09/21）。"""
    orders = [
        {"order_cd": "PO-1", "item_cd": "X-9065", "vend_cd": "9065", "due_date": "2026/12/15", "remaining_qty": 100},
        {"order_cd": "PO-2", "item_cd": "X-9065", "vend_cd": "9065", "due_date": "2026/12/16", "remaining_qty": 100},
    ]

    [enriched] = attach_stockout_risk([_row("100", "A", orders=orders)], AS_OF, settings=SETTINGS)

    assert enriched["replenishment_qty"] == 100
    assert enriched["replenishment_later_qty"] == 100


def test_d050_attach_uses_unknown_flag_from_rows():
    [row] = attach_stockout_risk([_row("100", "A", open_purchase_orders_unknown=True)], AS_OF, settings=SETTINGS)

    assert row["stockout_risk"] == RISK_CAUTION
    assert row["replenishment_unknown"] is True
    assert REASON_REPLENISHMENT_UNKNOWN in row["stockout_risk_reasons"]


def test_d051_legacy_rows_without_forecast_keys_are_watch():
    [row] = attach_stockout_risk([{"cust_code": "100", "item_cd": "A"}], AS_OF, settings=SETTINGS)

    assert row["stockout_risk"] == RISK_WATCH
    assert row["stockout_risk_reasons"] == []
    assert row["replenishment_unknown"] is False
    assert row["replenishment_stale_qty"] == 0
    assert row["days_until_stockout"] is None
    assert row["lead_time_days"] == SETTINGS.default_lead_time_days
    assert row["ordering_method"] == "不明"


def test_fqr_r006_attach_reads_stock_missing_and_recent_incoming_from_the_row():
    """在庫数が空文字（該当なし）かつ単位の在庫合計 0 の行は在庫なしとして判定する。"""
    missing = _row(
        "100",
        "A",
        stock="",
        demand_forecast_stock_total=0.0,
        flow_quadrant=QUADRANT_STOCKOUT,
        stockout_forecast_month="2026-09",
        last_incoming_date="2026/09/10",
        ordering_method=ORDERING_MRP,
    )

    [enriched] = attach_stockout_risk([missing], AS_OF, settings=SETTINGS)

    assert enriched["stockout_risk"] == RISK_DANGER
    assert enriched["stockout_risk_reasons"][:2] == [REASON_STOCK_MISSING, REASON_SUPPLY_DELAY]


def test_fqr_r006_attach_treats_stock_zero_as_stock_present():
    """SLIMS に行があり在庫 0 は「在庫なし」ではない（従来の判定を通す）。"""
    zero_stock = _row(
        "100",
        "A",
        stock="0",
        demand_forecast_stock_total=0.0,
        stockout_forecast_month="2026-09",
        last_incoming_date="2026/09/10",
        ordering_method=ORDERING_MRP,
    )

    [enriched] = attach_stockout_risk([zero_stock], AS_OF, settings=SETTINGS)

    assert REASON_STOCK_MISSING not in enriched["stockout_risk_reasons"]
    assert REASON_RECENT_INCOMING in enriched["stockout_risk_reasons"]


def test_d052_attach_does_not_mutate_input():
    source = _row("100", "A")
    before = dict(source)

    attach_stockout_risk([source], AS_OF, settings=SETTINGS)

    assert source == before


def test_d053_rank_order_and_keys():
    assert STOCKOUT_RISKS == (RISK_DANGER, RISK_CAUTION, RISK_WATCH, RISK_NONE)
    assert [STOCKOUT_RISK_RANK[r] for r in STOCKOUT_RISKS] == [0, 1, 2, 3]
    assert STOCKOUT_RISK_KEYS == {RISK_DANGER: "danger", RISK_CAUTION: "caution", RISK_WATCH: "watch", RISK_NONE: "none"}
    assert (RISK_DANGER, RISK_CAUTION, RISK_WATCH, RISK_NONE) == ("危険", "注意", "監視", "対象外")


@pytest.mark.parametrize("kwargs", [{"safety_days": 0}, {"safety_days": 61}, {"default_lead_time_days": 0}, {"watch_months": 13}])
def test_d054_settings_are_validated(kwargs):
    with pytest.raises(ValueError):
        StockoutRiskSettings(**kwargs)


# --- 2026/09/18 改訂: 補充サイクル稼働中（直近に入荷あり）は危険にしない ---

from application.inventory_order_alert.domain.value_objects.stockout_risk import REASON_RECENT_INCOMING  # noqa: E402


def test_recent_incoming_prevents_danger_and_becomes_caution():
    # 猶予 0 日・発注残なし だが、最終入荷が 3 日前（LT 5 + 安全 14 = 19 日以内）→ 注意
    result = _assess(stockout_month="2026-09", outlook=_outlook(0), last_incoming_date=date(2026, 9, 15))

    assert result.risk == RISK_CAUTION
    assert REASON_RECENT_INCOMING in result.reasons
    assert REASON_WITHIN_LEAD_TIME in result.reasons


def test_recent_incoming_with_enough_replenishment_is_none():
    result = _assess(stockout_month="2026-12", outlook=_outlook(500), last_incoming_date=date(2026, 9, 15))

    assert result.risk == RISK_NONE
    assert result.reasons == ()


def test_recent_incoming_boundary_is_lead_time_plus_safety_days():
    # 基準日 9/17: 19 日前（8/29）→ 稼働中（注意）、20 日前（8/28）→ 危険
    assert _assess(stockout_month="2026-09", last_incoming_date=date(2026, 8, 29)).risk == RISK_CAUTION
    assert _assess(stockout_month="2026-09", last_incoming_date=date(2026, 8, 28)).risk == RISK_DANGER


def test_no_incoming_record_or_old_incoming_can_still_be_danger():
    assert _assess(stockout_month="2026-09", last_incoming_date=None).risk == RISK_DANGER
    assert _assess(stockout_month="2026-09", last_incoming_date=date(2025, 4, 2)).risk == RISK_DANGER


@pytest.mark.parametrize("profile", [PROFILE_MANUAL, PROFILE_UNKNOWN])
def test_d049_recent_incoming_exemption_applies_only_to_mrp(profile):
    """直近入荷の免除は MRP 発注のみ。手動発注・不明は「前回は入荷したが次を発注していない」＝発注忘れ（F-014 #14、2026/09/21）。"""
    result = _assess(stockout_month="2026-09", outlook=_outlook(0), profile=profile, last_incoming_date=date(2026, 9, 15))

    assert result.risk == RISK_DANGER
    assert REASON_RECENT_INCOMING not in result.reasons
    assert (REASON_MAYBE_FORGOTTEN in result.reasons) is (profile is PROFILE_MANUAL)


def test_attach_reads_last_incoming_date_from_row():
    row = _row("100", "A", last_incoming_date="2026/09/17", stockout_forecast_month="2026-09", ordering_method=ORDERING_MRP)
    [enriched] = attach_stockout_risk([row], AS_OF, settings=SETTINGS)

    assert enriched["stockout_risk"] == RISK_CAUTION
    assert REASON_RECENT_INCOMING in enriched["stockout_risk_reasons"]

    [old] = attach_stockout_risk([_row("100", "A", last_incoming_date="2025/04/02", stockout_forecast_month="2026-09")], AS_OF, settings=SETTINGS)
    assert old["stockout_risk"] == RISK_DANGER


# --- 2026/09/18 追加: 工程の連鎖（上流工程の発注残・リードタイムの合計） ---

from application.inventory_order_alert.domain.value_objects.stockout_risk import (  # noqa: E402
    REASON_UPSTREAM_ORDER,
    REASON_UPSTREAM_OVERDUE,
    chain_lead_time,
)


def _outlook_upstream(
    qty: int = 0, *, upstream_qty: int = 0, upstream_overdue: bool = False, upstream_pending_qty: int | None = None
) -> ReplenishmentOutlook:
    # 既定: 納期超過なら全量が超過（pending 0）、そうでなければ全量が納期内
    pending = upstream_pending_qty if upstream_pending_qty is not None else (0 if upstream_overdue else upstream_qty)
    return ReplenishmentOutlook(
        qty=qty, later_qty=0, earliest_due=None, has_overdue=False,
        upstream_qty=upstream_qty, upstream_overdue=upstream_overdue, upstream_pending_qty=pending,
    )


def test_upstream_order_within_due_downgrades_danger_to_caution():
    result = _assess(stockout_month="2026-09", outlook=_outlook_upstream(0, upstream_qty=240))

    assert result.risk == RISK_CAUTION
    assert REASON_UPSTREAM_ORDER in result.reasons
    assert REASON_UPSTREAM_OVERDUE not in result.reasons


def test_upstream_overdue_order_keeps_danger_with_reason():
    result = _assess(stockout_month="2026-09", outlook=_outlook_upstream(0, upstream_qty=240, upstream_overdue=True))

    assert result.risk == RISK_DANGER
    assert REASON_UPSTREAM_OVERDUE in result.reasons
    assert REASON_UPSTREAM_ORDER not in result.reasons


def test_upstream_mixed_overdue_and_pending_is_caution_with_both_reasons():
    """上流に納期超過と納期内が混在: 納期内の分が流れている以上は注意、理由は両方（F-005/F-006、2026/09/18 明確化）。"""
    result = _assess(
        stockout_month="2026-09",
        outlook=_outlook_upstream(0, upstream_qty=290, upstream_overdue=True, upstream_pending_qty=50),
    )

    assert result.risk == RISK_CAUTION
    assert REASON_UPSTREAM_ORDER in result.reasons
    assert REASON_UPSTREAM_OVERDUE in result.reasons


def test_chain_lead_time_sums_stages_and_flags_default():
    chain = [
        {"item_cd": "X-9133", "vend_cd": "9133", "lead_time_days": 0, "lead_time_source": "default"},
        {"item_cd": "X-9213", "vend_cd": "9213", "lead_time_days": 4, "lead_time_source": "master"},
        {"item_cd": "X-9106", "vend_cd": "9106", "lead_time_days": 5, "lead_time_source": "master"},
    ]

    days, source = chain_lead_time(chain, default_days=5)

    assert days == 5 + 4 + 5
    assert source == LEAD_TIME_SOURCE_DEFAULT
    assert chain_lead_time([], default_days=5) == (0, LEAD_TIME_SOURCE_DEFAULT)
    assert chain_lead_time([{"lead_time_days": 3, "lead_time_source": "master"}], default_days=5) == (3, LEAD_TIME_SOURCE_MASTER)


def test_attach_uses_chain_lead_time_and_upstream_orders():
    row = _row(
        "195",
        "138232-0213",
        level1=("138232-0213-9133", "9133"),
        stock="5",
        demand_forecast_stock_total=5.0,
        demand_forecast_current_month_remaining=20,
        demand_forecast_monthly=[20, 0, 0],
        demand_forecast_monthly_average=20.0,
        stockout_forecast_month="2026-09",
        last_incoming_date="2025/01/13",
        ordering_method=ORDERING_MRP,
        process_chain=[
            {"item_cd": "138232-0213-9133", "vend_cd": "9133", "vend_name": "丸栄NW", "lead_time_days": 0, "lead_time_source": "default"},
            {"item_cd": "138232-0213-9213", "vend_cd": "9213", "vend_name": "サーテック", "lead_time_days": 4, "lead_time_source": "master"},
            {"item_cd": "138232-0213-9106", "vend_cd": "9106", "vend_name": "誠豊電子", "lead_time_days": 5, "lead_time_source": "master"},
        ],
        open_purchase_orders=[{"item_cd": "138232-0213-9106", "vend_cd": "9106", "due_date": "2026/06/15", "remaining_qty": 240}],
    )

    [enriched] = attach_stockout_risk([row], AS_OF, settings=SETTINGS)

    assert enriched["stockout_risk"] == RISK_DANGER
    assert enriched["lead_time_days"] == 5 + 4 + 5
    assert enriched["lead_time_source"] == LEAD_TIME_SOURCE_DEFAULT
    assert enriched["replenishment_qty"] == 0
    assert enriched["upstream_order_qty"] == 240
    assert enriched["upstream_order_overdue"] is True
    assert REASON_UPSTREAM_OVERDUE in enriched["stockout_risk_reasons"]
    assert REASON_SUPPLIER_CHECK_FIRST in enriched["stockout_risk_reasons"]


def test_attach_without_chain_uses_row_lead_time():
    [enriched] = attach_stockout_risk([_row("100", "A", lead_time_days=3, lead_time_source=LEAD_TIME_SOURCE_MASTER)], AS_OF, settings=SETTINGS)

    assert enriched["lead_time_days"] == 3
    assert enriched["upstream_order_qty"] == 0


def test_chain_lead_time_takes_max_per_level_for_parallel_stages():
    chain = [
        {"level": 1, "lead_time_days": 2, "lead_time_source": "master"},
        {"level": 2, "lead_time_days": 4, "lead_time_source": "master"},
        {"level": 2, "lead_time_days": 9, "lead_time_source": "master"},  # 並列工程: 同じ階層は最大値
        {"level": 3, "lead_time_days": 5, "lead_time_source": "master"},
    ]

    assert chain_lead_time(chain, default_days=5) == (2 + 9 + 5, LEAD_TIME_SOURCE_MASTER)
