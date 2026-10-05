"""月次出荷推移の集計ロジック（domain）のテスト（test-design.md TC-SHC-D-001〜009）。"""

from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.shipment_trend import build_monthly_shipment_trend

AS_OF_DATE = date(2026, 6, 17)


def test_TC_SHC_D_001_returns_24_zero_months_when_no_shipments():
    result = build_monthly_shipment_trend([], as_of_date=AS_OF_DATE)

    assert len(result) == 24
    assert all(point["qty"] == 0 for point in result)
    assert result[0]["month"] == "2024-07"
    assert result[-1]["month"] == "2026-06"


def test_TC_SHC_D_002_sums_multiple_shipments_in_same_month():
    shipments = [(date(2026, 6, 1), 10), (date(2026, 6, 30), 5)]

    result = build_monthly_shipment_trend(shipments, as_of_date=AS_OF_DATE)

    june = next(point for point in result if point["month"] == "2026-06")
    assert june["qty"] == 15


def test_TC_SHC_D_003_last_point_is_as_of_month():
    result = build_monthly_shipment_trend([], as_of_date=AS_OF_DATE)

    assert result[-1]["month"] == "2026-06"


def test_TC_SHC_D_004_excludes_shipments_older_than_24_months():
    # ちょうど24か月前（2024-07）は範囲内、25か月前（2024-06）は範囲外。
    shipments = [(date(2024, 7, 15), 100), (date(2024, 6, 15), 200)]

    result = build_monthly_shipment_trend(shipments, as_of_date=AS_OF_DATE)

    assert result[0]["month"] == "2024-07"
    assert result[0]["qty"] == 100
    assert all(point["month"] != "2024-06" for point in result)


def test_TC_SHC_D_005_months_are_ordered_oldest_first():
    result = build_monthly_shipment_trend([], as_of_date=AS_OF_DATE)

    months = [point["month"] for point in result]
    assert months == sorted(months)


def test_TC_SHC_D_006_always_returns_fixed_length_24():
    shipments = [(date(2026, 6, 1), 1)]

    result = build_monthly_shipment_trend(shipments, as_of_date=AS_OF_DATE)

    assert len(result) == 24


def test_TC_SHC_D_007_month_end_shipment_is_not_misclassified():
    shipments = [(date(2026, 5, 31), 7), (date(2026, 6, 1), 3)]

    result = build_monthly_shipment_trend(shipments, as_of_date=AS_OF_DATE)

    may = next(point for point in result if point["month"] == "2026-05")
    june = next(point for point in result if point["month"] == "2026-06")
    assert may["qty"] == 7
    assert june["qty"] == 3


def test_TC_SHC_D_008_negative_quantity_is_summed_as_is():
    # 返品等による負値は基幹の値をそのまま合算する（design.md §8）。
    shipments = [(date(2026, 6, 5), 10), (date(2026, 6, 10), -3)]

    result = build_monthly_shipment_trend(shipments, as_of_date=AS_OF_DATE)

    june = next(point for point in result if point["month"] == "2026-06")
    assert june["qty"] == 7


def test_TC_SHC_D_009_months_argument_changes_length():
    result = build_monthly_shipment_trend([], as_of_date=AS_OF_DATE, months=6)

    assert len(result) == 6
    assert result[-1]["month"] == "2026-06"
    assert result[0]["month"] == "2026-01"
