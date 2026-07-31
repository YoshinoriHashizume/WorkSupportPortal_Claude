from __future__ import annotations

from decimal import Decimal

from application.inventory_order_alert.domain.value_objects.slims_stock import SlimsStockLocationLine
from application.inventory_order_alert.domain.value_objects.stock_join import attach_stock_fields


def test_attach_stock_fields_uses_aggregated_summary_and_raw_detail():
    rows = [{"item_cd": "43522-D1020-00"}]
    stock_lines = [
        SlimsStockLocationLine(
            item_cd="43522-D1020-00",
            wloccd="2D0-03-5",
            stock_qty=Decimal("90"),
            wnyudt="20161228",
        ),
        SlimsStockLocationLine(
            item_cd="43522-D1020-00",
            wloccd="2D0-03-5",
            stock_qty=Decimal("50"),
            wnyudt="20170101",
        ),
        SlimsStockLocationLine(
            item_cd="43522-D1020-00",
            wloccd="2E1-03-4",
            stock_qty=Decimal("10"),
            wnyudt="20161228",
        ),
    ]

    enriched = attach_stock_fields(rows, stock_lines)
    row = enriched[0]

    assert row["stock_qty"] == Decimal("150")
    assert row["stock_location_summary"] == "2D0-03-5 他1"
    assert row["stock_location_detail"] == (
        "2D0-03-5=90@20161228;2E1-03-4=10@20161228;2D0-03-5=50@20170101"
    )
