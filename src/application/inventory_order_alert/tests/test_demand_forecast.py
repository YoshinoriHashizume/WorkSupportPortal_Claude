"""需要予測（V-220）・在庫切れ予測月（V-221）・在庫月数（V-222）のテスト（test-design.md TC-SFV-D-090〜109、07 TC-FQR-D-001〜006）。

test-design §3.1 の ROW_100 / ROW_104 / ROW_137_A / ROW_137_B（96160-00500 の照合単位）を使う。
"""

from __future__ import annotations

from datetime import date

import pytest

from application.inventory_order_alert.domain.value_objects.demand_forecast import (
    BASIS_NONE,
    BASIS_UNCONFIRMED,
    DEMAND_FORECAST_BASES,
    STOCKOUT_FORECAST_LIMIT_MONTHS,
    DemandForecast,
    attach_demand_forecast,
    build_demand_forecast,
    months_of_stock,
    stock_total_of,
    stockout_forecast_month,
)

AS_OF = date(2026, 9, 15)
MONTHS = ["2026-09", "2026-10", "2026-11", "2026-12"]


def _trend(qtys: list[int]) -> list[dict[str, object]]:
    return [{"month": month, "qty": qty} for month, qty in zip(MONTHS, qtys)]


def _shipment_trend(recent_12: list[int]) -> list[dict[str, object]]:
    """直近 24 か月の出荷推移（古い順）。先頭 12 か月は 0、末尾 12 か月に recent_12 を置く。"""
    qtys = [0] * 12 + list(recent_12)
    return [{"month": f"M{index:02d}", "qty": qty} for index, qty in enumerate(qtys)]


def _row(cust_code: str, item_cd: str, *, internal="96160-00500-9065", stock="12970", unconfirmed=None, shipments=None, **extra):
    row: dict[str, object] = {
        "cust_code": cust_code,
        "item_cd": item_cd,
        "internal_item_cd": internal,
        "level1_item_cd": internal,
        "level1_vend_cd": "9065",
        "last_incoming_date": "2025/04/02",
        "last_ship_date": "2023/07/27",
        "shipment_trend": _shipment_trend(shipments or [0] * 12),
    }
    if stock is not None:
        row["stock_qty"] = stock
    if unconfirmed is not None:
        row["unconfirmed_order_trend"] = _trend(unconfirmed)
    row.update(extra)
    return row


ROW_100 = _row("100", "96160-00500", unconfirmed=[0, 0, 0, 0])
ROW_104 = _row("104", "96160-00500", unconfirmed=[0, 194, 186, 169], shipments=[1000, 1000, 500, 500, 1000, 1000, 500, 500, 1000, 1000, 500, 500])
ROW_137_A = _row("137", "96160-00500", unconfirmed=[0, 30, 30, 28])
ROW_137_B = _row("137", "10523-X0A02", stock="19000", unconfirmed=[0, 30, 30, 28])
UNIT_96160 = [ROW_100, ROW_104, ROW_137_A, ROW_137_B]


# --- TC-SFV-D-090: 内示があれば内示ベース ---


def test_d090_unconfirmed_orders_give_unconfirmed_basis():
    forecast = build_demand_forecast([_row("100", "X", unconfirmed=[10, 100, 200, 300])], as_of_date=AS_OF)

    assert forecast.basis == BASIS_UNCONFIRMED
    assert forecast.current_month_remaining == 10
    assert forecast.monthly == (100, 200, 300)
    assert forecast.monthly_average == 200.0


# --- TC-SFV-D-091: (得意先, 内作品番) の重複を除いて合算 ---


def test_d091_duplicates_by_customer_and_internal_item_are_counted_once():
    forecast = build_demand_forecast(UNIT_96160, as_of_date=AS_OF)

    assert forecast.basis == BASIS_UNCONFIRMED
    assert forecast.monthly == (224, 216, 197)


# --- TC-SFV-D-092: 内示が 3 か月に満たない場合は存在する月で平均 ---


def test_d092_average_uses_only_months_with_orders():
    forecast = build_demand_forecast([_row("100", "X", unconfirmed=[0, 300, 0, 0])], as_of_date=AS_OF)

    assert forecast.basis == BASIS_UNCONFIRMED
    assert forecast.monthly == (300, 0, 0)
    assert forecast.monthly_average == 300.0


# --- TC-SFV-D-093 → 07 TC-FQR-D-001/002: 内示ゼロなら出荷実績があっても なし（実績ベースは廃止。REQ-FQR-F-002） ---


def test_d093_fqr_d001_zero_unconfirmed_with_recent_shipments_gives_none_basis():
    forecast = build_demand_forecast([_row("100", "X", unconfirmed=[0, 0, 0, 0], shipments=[0] * 9 + [10, 20, 30])], as_of_date=AS_OF)

    assert forecast.basis == BASIS_NONE
    assert forecast.monthly_average == 0
    assert forecast.has_demand is False


def test_d093_fqr_d002_older_shipments_only_give_none_basis():
    trend = [{"month": f"M{index:02d}", "qty": 999 if index < 12 else 0} for index in range(24)]
    forecast = build_demand_forecast([{"cust_code": "100", "item_cd": "X", "shipment_trend": trend, "unconfirmed_order_trend": _trend([0, 0, 0, 0])}], as_of_date=AS_OF)

    assert forecast.basis == BASIS_NONE


# --- TC-SFV-D-094: 内示も出荷もゼロなら なし ---


def test_d094_no_orders_and_no_shipments_gives_none_basis():
    forecast = build_demand_forecast([_row("100", "X", unconfirmed=[0, 0, 0, 0])], as_of_date=AS_OF)

    assert forecast.basis == BASIS_NONE
    assert forecast.monthly_average == 0
    assert forecast.monthly == (0, 0, 0)


# --- TC-SFV-D-095: 内示推移を持たない旧行 ---


def test_d095_rows_without_unconfirmed_trend_are_none_even_with_shipments():
    with_shipments = build_demand_forecast([_row("100", "X", shipments=[120] * 12)], as_of_date=AS_OF)
    without = build_demand_forecast([_row("100", "X")], as_of_date=AS_OF)

    assert with_shipments.basis == BASIS_NONE
    assert without.basis == BASIS_NONE


# --- TC-SFV-D-096 / TC-FQR-D-003: basis は 内示 / なし の 2 値 ---


@pytest.mark.parametrize("basis", ["内示受注", "実績ベース"])
def test_d096_fqr_d003_invalid_basis_is_rejected(basis):
    assert DEMAND_FORECAST_BASES == (BASIS_UNCONFIRMED, BASIS_NONE)
    with pytest.raises(ValueError):
        DemandForecast(basis=basis, current_month_remaining=0, monthly=(0, 0, 0), monthly_average=0.0)


# --- TC-SFV-D-097: 在庫月数 = 在庫合計 ÷ 月平均、小数 1 桁 ---


def test_d097_months_of_stock_is_rounded_to_one_decimal():
    forecast = DemandForecast(basis=BASIS_UNCONFIRMED, current_month_remaining=0, monthly=(212, 212, 213), monthly_average=212.3)

    assert months_of_stock(31970, forecast) == 150.6


# --- TC-SFV-D-098: 在庫月数は需要なし・平均 0 で空 ---


def test_d098_months_of_stock_is_none_without_demand():
    none_basis = DemandForecast(basis=BASIS_NONE, current_month_remaining=0, monthly=(0, 0, 0), monthly_average=0.0)
    zero_average = DemandForecast(basis=BASIS_UNCONFIRMED, current_month_remaining=50, monthly=(0, 0, 0), monthly_average=0.0)

    assert months_of_stock(1000, none_basis) is None
    assert months_of_stock(1000, zero_average) is None
    assert months_of_stock(None, DemandForecast(basis=BASIS_UNCONFIRMED, current_month_remaining=0, monthly=(0, 0, 0), monthly_average=10.0)) is None


# --- TC-SFV-D-099: 在庫切れ予測月（内示で当月残を引く） ---


def _forecast(current: int, monthly: tuple[int, int, int], average: float, basis: str = BASIS_UNCONFIRMED) -> DemandForecast:
    return DemandForecast(basis=basis, current_month_remaining=current, monthly=monthly, monthly_average=average)


def test_d099_stockout_month_subtracts_current_month_remaining_then_monthly():
    # 500 − 100 = 400 → 10 月 200 → 11 月 0 → 12 月 −200
    assert stockout_forecast_month(500, _forecast(100, (200, 200, 200), 200.0), as_of_date=AS_OF) == "2026-12"


# --- TC-SFV-D-100: 在庫切れ予測月（4 か月目以降は平均） ---


def test_d100_stockout_month_uses_average_after_the_third_month():
    # 1,000 → 10 月 900 … 2027/07 で 0、2027/08 に初めて負（在庫月数 10.0 か月）
    forecast = _forecast(0, (100, 100, 100), 100.0)

    assert stockout_forecast_month(1000, forecast, as_of_date=AS_OF) == "2027-08"
    assert months_of_stock(1000, forecast) == 10.0


# --- TC-SFV-D-101: 在庫が当月残より少なければ当月 ---


def test_d101_stock_below_current_month_remaining_is_current_month():
    assert stockout_forecast_month(50, _forecast(100, (0, 0, 0), 0.0), as_of_date=AS_OF) == "2026-09"


# --- TC-SFV-D-102 → 07 TC-FQR-D-005/006: 在庫 0 は需要が初めて出る月（「在庫 0 以下は当月」は廃止。2026/09/21） ---


def test_d102_fqr_d005_zero_stock_stockout_month_is_the_first_month_with_demand():
    assert stockout_forecast_month(0, _forecast(0, (100, 100, 100), 100.0), as_of_date=AS_OF) == "2026-10"
    assert stockout_forecast_month(0, _forecast(0, (0, 320, 290), 305.0), as_of_date=AS_OF) == "2026-11"
    assert stockout_forecast_month(0, _forecast(50, (0, 320, 290), 305.0), as_of_date=AS_OF) == "2026-09"
    assert months_of_stock(0, _forecast(0, (100, 100, 100), 100.0)) == 0.0


def test_d102_fqr_d006_zero_stock_without_monthly_demand_falls_to_average():
    # 内示 3 か月とも 0 だが月平均 > 0（データ不整合）でも 4 か月目以降の平均で尽きる
    assert stockout_forecast_month(0, _forecast(0, (0, 0, 0), 10.0), as_of_date=AS_OF) == "2027-01"


# --- TC-SFV-D-103: 120 か月以内に尽きなければ空 ---


def test_d103_stock_lasting_beyond_limit_gives_none():
    assert STOCKOUT_FORECAST_LIMIT_MONTHS == 120
    assert stockout_forecast_month(1_000_000, _forecast(0, (1, 1, 1), 1.0), as_of_date=AS_OF) is None


# --- TC-SFV-D-104: 需要なしなら予測月は空 ---


def test_d104_none_basis_gives_none():
    assert stockout_forecast_month(100, _forecast(0, (0, 0, 0), 0.0, basis=BASIS_NONE), as_of_date=AS_OF) is None
    assert stockout_forecast_month(None, _forecast(0, (100, 100, 100), 100.0), as_of_date=AS_OF) is None


# --- TC-SFV-D-105〜107: 単位の在庫合計 ---


def test_d105_stock_total_treats_empty_as_zero_and_not_fetched_as_zero():
    rows = [_row("100", "A", stock=""), _row("100", "B", stock="100"), _row("100", "C", stock=None)]

    assert stock_total_of(rows) == 100.0


def test_d106_stock_total_is_none_when_no_row_has_stock_fetched():
    rows = [_row("100", "A", stock=None), _row("137", "B", stock=None)]
    forecast = _forecast(0, (100, 100, 100), 100.0)

    assert stock_total_of(rows) is None
    assert months_of_stock(stock_total_of(rows), forecast) is None
    assert stockout_forecast_month(stock_total_of(rows), forecast, as_of_date=AS_OF) is None


def test_d107_stock_total_counts_each_item_once():
    rows = [_row("100", "96160-00500", stock="12970"), _row("137", "96160-00500", stock="12970")]

    assert stock_total_of(rows) == 12970.0


def test_stock_total_of_96160_unit_and_months_of_stock():
    forecast = build_demand_forecast(UNIT_96160, as_of_date=AS_OF)

    assert stock_total_of(UNIT_96160) == 31970.0
    assert forecast.monthly_average == round((224 + 216 + 197) / 3, 4)
    assert months_of_stock(31970.0, forecast) == 150.6


def test_stock_total_of_accepts_comma_separated_text():
    assert stock_total_of([_row("100", "A", stock="12,970")]) == 12970.0


# --- TC-SFV-D-108〜109: attach_demand_forecast ---


def test_d108_attach_demand_forecast_copies_unit_values_to_every_row():
    rows = [ROW_104, ROW_137_A, ROW_137_B]

    enriched = attach_demand_forecast(rows, as_of_date=AS_OF)

    assert len(enriched) == 3
    assert {row["demand_forecast_basis"] for row in enriched} == {BASIS_UNCONFIRMED}
    assert {row["reconciliation_unit_key"] for row in enriched} == {"10523-X0A02"}
    assert {tuple(row["demand_forecast_monthly"]) for row in enriched} == {(224, 216, 197)}
    assert {row["months_of_stock"] for row in enriched} == {150.6}
    # 150.6 か月分 > 上限 120 か月 → 在庫切れ予測月は None（「十分」）
    assert {row["stockout_forecast_month"] for row in enriched} == {None}
    assert {row["demand_forecast_current_month_remaining"] for row in enriched} == {0}
    assert {row["demand_forecast_stock_total"] for row in enriched} == {31970.0}


def test_d108_rows_without_forecast_keys_get_none_basis_and_null_values():
    [row] = attach_demand_forecast([{"cust_code": "100", "item_cd": "X"}], as_of_date=AS_OF)

    assert row["demand_forecast_basis"] == BASIS_NONE
    assert row["demand_forecast_monthly"] == [0, 0, 0]
    assert row["months_of_stock"] is None
    assert row["stockout_forecast_month"] is None
    assert row["reconciliation_unit_key"] == "X"


def test_d109_attach_demand_forecast_does_not_mutate_input_rows():
    source = _row("100", "X", unconfirmed=[10, 100, 200, 300])
    before = dict(source)

    attach_demand_forecast([source], as_of_date=AS_OF)

    assert source == before
    assert "demand_forecast_basis" not in source
