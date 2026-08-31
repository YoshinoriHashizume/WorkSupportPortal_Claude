from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from application.inventory_order_alert.infrastructure.oracle.summary_aggregation import run_summary_aggregation
from application.inventory_order_alert.infrastructure.oracle.summary_queries import build_summary_rows
from application.inventory_order_alert.infrastructure.persistence.summary_snapshot_repository import (
    store_summary_snapshot,
)
from application.inventory_order_alert.models import (
    InventoryOrderAlertSummarySnapshot,
    SlimsStockImport,
)


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


def _shipped_pair_patches(mari_stock_totals: dict[str, object] | None = None, **overrides):
    """出荷実績のある 1 行を組み立てるためのパッチ群。"""
    defaults = {
        "fetch_customer_names": {"137": "テスト得意先"},
        "fetch_ship_customer_items": [("137", "10523-X0A02", "001", "96160-00500")],
        "fetch_internal_items_from_m_cust_item": (
            {("137", "10523-X0A02"): "96160-00500"},
            {"10523-X0A02": "96160-00500"},
        ),
        "fetch_all_shipments": [("137", "10523-X0A02", date(2026, 6, 1), 10)],
        "fetch_finished_roots": {"96160-00500": {"96160-00500"}},
        "fetch_bom_level1_by_root": {"96160-00500": []},
        "fetch_vendor_by_component": {},
        "fetch_last_incoming_by_item_vend": {},
        "fetch_mari_stock_totals": mari_stock_totals if mari_stock_totals is not None else {},
    }
    defaults.update(overrides)
    return [
        patch(
            f"application.inventory_order_alert.infrastructure.oracle.summary_queries.{name}",
            return_value=value,
        )
        for name, value in defaults.items()
    ]


def _build_rows_with(mari_stock_totals: dict[str, object] | None = None, **overrides):
    patches = _shipped_pair_patches(mari_stock_totals, **overrides)
    for p in patches:
        p.start()
    try:
        return build_summary_rows(MagicMock(), date(2026, 6, 29))
    finally:
        for p in patches:
            p.stop()


def test_build_summary_rows_attaches_mari_stock_qty() -> None:
    rows = _build_rows_with({"96160-00500": 42})

    assert rows[0]["mari_stock_qty"] == 42


def test_build_summary_rows_leaves_mari_stock_empty_when_not_found() -> None:
    rows = _build_rows_with({})

    # 該当在庫が無い場合は空。0 にしない
    assert rows[0]["mari_stock_qty"] == ""


def test_build_summary_rows_keeps_zero_mari_stock_qty() -> None:
    rows = _build_rows_with({"96160-00500": 0})

    # 在庫 0 は空にしない
    assert rows[0]["mari_stock_qty"] == 0


def test_build_summary_rows_leaves_mari_stock_empty_when_internal_item_unresolved() -> None:
    rows = _build_rows_with(
        {"96160-00500": 42},
        fetch_ship_customer_items=[("137", "10523-X0A02", "001", "")],
        fetch_internal_items_from_m_cust_item=({}, {}),
    )

    assert rows[0]["mari_stock_qty"] == ""
    # 他の列は従来どおり組み立てられる
    assert rows[0]["cust_code"] == "137"
    assert rows[0]["item_cd"] == "10523-X0A02"


def _failing_aggregation(import_record, message: str):
    with (
        patch(
            "application.inventory_order_alert.infrastructure.oracle.summary_aggregation.oracle_connection"
        ) as connection,
        patch(
            "application.inventory_order_alert.infrastructure.oracle.summary_aggregation.build_list_rows",
            side_effect=RuntimeError(message),
        ),
    ):
        connection.return_value.__enter__.return_value = MagicMock()
        return run_summary_aggregation(import_record, [])


@pytest.mark.django_db
def test_run_summary_aggregation_fails_whole_import_when_stock_query_raises() -> None:
    """MARI 在庫の取得に失敗したら取込全体を失敗させる（REQ-MSV-F-009）。"""
    import_record = SlimsStockImport.objects.create(file_name="sample.csv", row_count=1)

    aggregation_error, reset_count = _failing_aggregation(
        import_record, "ORA-00942: table or view does not exist"
    )

    assert "ORA-00942" in aggregation_error
    assert reset_count == 0

    snapshot = InventoryOrderAlertSummarySnapshot.objects.filter(import_record=import_record).latest("id")
    assert snapshot.aggregation_error
    # MARI 在庫だけ欠けた中途半端なスナップショットを作らない。
    assert snapshot.rows == []


@pytest.mark.django_db
def test_run_summary_aggregation_keeps_previous_snapshot_on_failure() -> None:
    """失敗しても直前のスナップショットは残る（REQ-MSV-F-009）。"""
    healthy_import = SlimsStockImport.objects.create(file_name="ok.csv", row_count=1)
    store_summary_snapshot(
        healthy_import,
        [{"cust_code": "112", "item_cd": "90249-10112", "mari_stock_qty": 95}],
        as_of_date=date(2026, 6, 17),
    )

    failing_import = SlimsStockImport.objects.create(file_name="ng.csv", row_count=1)
    _failing_aggregation(failing_import, "MARI 在庫の取得に失敗")

    healthy = InventoryOrderAlertSummarySnapshot.objects.filter(import_record=healthy_import).latest("id")
    assert healthy.rows[0]["mari_stock_qty"] == 95
    assert healthy.aggregation_error == ""
