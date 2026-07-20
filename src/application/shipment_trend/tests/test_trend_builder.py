from __future__ import annotations

from application.shipment_trend.domain.value_objects.trend_builder import MonthlyShipmentRecord, build_trend_rows


def test_build_trend_rows_groups_by_cust_and_item():
    records = [
        MonthlyShipmentRecord("101", "ITEM-A", "S01", "2024-04", 100),
        MonthlyShipmentRecord("101", "ITEM-A", "S01", "2024-05", 50),
        MonthlyShipmentRecord("101", "ITEM-B", "S01", "2024-04", 20),
    ]
    rows = build_trend_rows(records, {"101": "テスト得意先"}, as_of_date=__import__("datetime").date(2025, 6, 1))
    assert len(rows) == 2
    row_a = next(row for row in rows if row["item_cd"] == "ITEM-A")
    assert row_a["cust_name"] == "テスト得意先"
    assert row_a["monthly"]["2024-04"] == 100
    assert row_a["change_qty"] is not None
