from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from application.inventory_order_alert.infrastructure.oracle.summary_queries import build_summary_rows


@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_last_incoming_by_item_vend",
    return_value={},
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_vendor_by_component",
    return_value={},
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_bom_level1_by_root",
    return_value={},
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_finished_roots",
    return_value={},
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_all_shipments",
    return_value=[],
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_internal_items_from_m_cust_item",
    return_value=({}, {}),
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_ship_customer_items",
    return_value=[],
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_customer_names",
    return_value={"137": "テスト得意先"},
)
def test_build_summary_rows_ignores_legacy_stock_item_cds(
    *_mocks: object,
) -> None:
    rows = build_summary_rows(
        MagicMock(),
        date(2026, 6, 29),
        stock_item_cds={"SLIMS-ONLY-ITEM"},
    )
    assert rows == []


@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_last_incoming_by_item_vend",
    return_value={},
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_vendor_by_component",
    return_value={},
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_bom_level1_by_root",
    return_value={"96160-00500": []},
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_finished_roots",
    return_value={"96160-00500": {"96160-00500"}},
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_all_shipments",
    return_value=[("137", "10523-X0A02", date(2026, 6, 1), 10)],
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_internal_items_from_m_cust_item",
    return_value=({("137", "10523-X0A02"): "96160-00500"}, {"10523-X0A02": "96160-00500"}),
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_ship_customer_items",
    return_value=[("137", "10523-X0A02", "001", "96160-00500")],
)
@patch(
    "application.inventory_order_alert.infrastructure.oracle.summary_queries.fetch_customer_names",
    return_value={"137": "テスト得意先"},
)
def test_build_summary_rows_includes_shipped_cust_item_pairs(
    *_mocks: object,
) -> None:
    rows = build_summary_rows(MagicMock(), date(2026, 6, 29))
    assert len(rows) == 1
    assert rows[0]["cust_code"] == "137"
    assert rows[0]["item_cd"] == "10523-X0A02"
