from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.list_query import ListQuery
from application.inventory_order_alert.domain.value_objects.list_rows import (
    enrich_summary_rows,
    filter_summary_rows,
    sort_summary_rows,
)
from application.inventory_order_alert.domain.value_objects.slims_stock import SlimsStockLocationLine, parse_slims_stock_csv
from application.inventory_order_alert.infrastructure.oracle.summary_queries import build_summary_rows
from application.inventory_order_alert.infrastructure.persistence.confirmation_repository import load_confirmation_map


def build_list_rows(
    connection: object,
    query: ListQuery,
    *,
    slims_csv_text: str | None = None,
    stock_lines: list[SlimsStockLocationLine] | None = None,
    stock_as_of_date=None,
    confirmations: dict[tuple[str, str], object] | None = None,
    warnings: list[str] | None = None,
) -> list[dict[str, object]]:
    if stock_lines is None and slims_csv_text:
        stock_lines = parse_slims_stock_csv(slims_csv_text)
    if confirmations is None:
        confirmations = load_confirmation_map()
    rows = build_summary_rows(
        connection,
        query.as_of_date,
        warnings=warnings,
    )
    enriched = enrich_summary_rows(
        rows,
        as_of_date=query.as_of_date,
        query=query,
        stock_lines=stock_lines,
        stock_as_of_date=stock_as_of_date,
        confirmations=confirmations,
    )
    filtered = filter_summary_rows(enriched, query)
    return sort_summary_rows(filtered)


__all__ = ["ListQuery", "build_list_rows"]
