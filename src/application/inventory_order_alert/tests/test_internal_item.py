from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.internal_item import resolve_cust_code, resolve_internal_item_cd
from application.inventory_order_alert.infrastructure.oracle.summary_queries import (
    aggregate_shipment_stats,
    fetch_internal_items_from_m_cust_item,
)


class _FakeCursor:
    def __init__(self, rows: list[tuple[object, ...]], columns: list[str]) -> None:
        self._rows = rows
        self.description = [(column,) for column in columns]

    def execute(self, _sql: str, _params: dict[str, object] | None = None) -> None:
        return None

    def fetchall(self) -> list[tuple[object, ...]]:
        return self._rows


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor

    def cursor(self) -> _FakeCursor:
        return self._cursor


def test_resolve_internal_item_cd_prefers_ship_then_pair_then_item():
    assert (
        resolve_internal_item_cd(
            cust_item_cd="CUST-A",
            internal_from_ship="SHIP-INT",
            internal_from_m_cust_item_pair="PAIR-INT",
            internal_from_m_cust_item="ITEM-INT",
        )
        == "SHIP-INT"
    )
    assert (
        resolve_internal_item_cd(
            cust_item_cd="CUST-A",
            internal_from_m_cust_item_pair="PAIR-INT",
            internal_from_m_cust_item="ITEM-INT",
        )
        == "PAIR-INT"
    )
    assert (
        resolve_internal_item_cd(
            cust_item_cd="CUST-A",
            internal_from_m_cust_item="ITEM-INT",
        )
        == "ITEM-INT"
    )
    assert resolve_internal_item_cd(cust_item_cd="CUST-A") == "CUST-A"


def test_resolve_cust_code_returns_ship_cust_only():
    assert resolve_cust_code(cust_from_ship="137") == "137"
    assert resolve_cust_code() == ""


def test_fetch_internal_items_from_m_cust_item_uses_last_row_per_key():
    cursor = _FakeCursor(
        [
            ("137", "10523-X0A02", "10523-X0A02"),
            ("137", "10523-X0A02", "96160-00500"),
            ("201", "10523-X0A02", "OTHER-INT"),
        ],
        ["CUST_CD", "CUST_ITEM_CD", "ITEM_CD"],
    )
    connection = _FakeConnection(cursor)

    by_pair, by_item = fetch_internal_items_from_m_cust_item(
        connection,
        date(2026, 6, 29),
        cust_item_cds={"10523-X0A02"},
    )

    assert by_pair[("137", "10523-X0A02")] == "96160-00500"
    assert by_pair[("201", "10523-X0A02")] == "OTHER-INT"
    assert by_item["10523-X0A02"] == "OTHER-INT"


def test_aggregate_shipment_stats_matches_cust_item_cd():
    shipments = [
        ("137", "10523-X0A02", date(2026, 3, 3), 2000),
    ]

    _, wrong_count, _ = aggregate_shipment_stats(
        shipments,
        "137",
        "96160-00500",
        date(2026, 1, 1),
    )
    _, correct_count, total_qty = aggregate_shipment_stats(
        shipments,
        "137",
        "10523-X0A02",
        date(2026, 1, 1),
    )

    assert wrong_count == 0
    assert correct_count == 1
    assert total_qty == 2000
