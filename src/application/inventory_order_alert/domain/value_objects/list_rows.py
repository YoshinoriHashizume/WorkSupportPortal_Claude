from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.alert_level import is_alert_level, resolve_alert_level
from application.inventory_order_alert.domain.value_objects.confirmation import ConfirmationRecord, attach_confirmation_fields
from application.inventory_order_alert.domain.value_objects.dates import parse_optional_ymd
from application.inventory_order_alert.domain.value_objects.list_query import ListQuery
from application.inventory_order_alert.domain.value_objects.slims_stock import SlimsStockLocationLine
from application.inventory_order_alert.domain.value_objects.stock_join import attach_stock_fields


def apply_alert_levels_to_rows(
    rows: list[dict[str, object]],
    *,
    as_of_date: date,
    query: ListQuery,
) -> list[dict[str, object]]:
    enriched: list[dict[str, object]] = []
    for row in rows:
        copied = dict(row)
        last_incoming_raw = str(copied.get("last_incoming_date") or "")
        last_ship_raw = str(copied.get("last_ship_date") or "")
        last_incoming = parse_optional_ymd(last_incoming_raw, today=as_of_date) if last_incoming_raw else None
        last_ship = parse_optional_ymd(last_ship_raw, today=as_of_date) if last_ship_raw else None
        copied["alert_level"] = resolve_alert_level(
            last_incoming,
            last_ship,
            int(copied.get("post_shipment_count") or 0),
            as_of_date=as_of_date,
            warning_shipment_months=query.warning_shipment_months,
            warning_incoming_months=query.warning_incoming_months,
            critical_enabled=query.critical_enabled,
        )
        enriched.append(copied)
    return enriched


def enrich_summary_rows(
    rows: list[dict[str, object]],
    *,
    as_of_date: date,
    query: ListQuery,
    stock_lines: list[SlimsStockLocationLine] | None = None,
    stock_as_of_date: date | None = None,
    confirmations: dict[tuple[str, str], ConfirmationRecord] | None = None,
) -> list[dict[str, object]]:
    rows_with_stock = attach_stock_fields(rows, stock_lines, stock_as_of_date=stock_as_of_date)
    enriched = apply_alert_levels_to_rows(rows_with_stock, as_of_date=as_of_date, query=query)
    confirmation_map = confirmations if confirmations is not None else {}
    return attach_confirmation_fields(enriched, confirmation_map)


def filter_summary_rows(rows: list[dict[str, object]], query: ListQuery) -> list[dict[str, object]]:
    filtered: list[dict[str, object]] = []
    for row in rows:
        if query.cust_code and str(row.get("cust_code") or "") != query.cust_code:
            continue
        if query.vend_code and str(row.get("level1_vend_cd") or "") != query.vend_code:
            continue
        if query.alert_only and not is_alert_level(str(row.get("alert_level") or "")):
            continue
        if query.hide_confirmed and str(row.get("confirmation_status") or "") == "確認済み":
            continue
        filtered.append(row)
    return filtered


def sort_summary_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    from application.inventory_order_alert.domain.value_objects.alert_level import ALERT_NONE, alert_sort_rank

    def sort_key(row: dict[str, object]) -> tuple[int, int]:
        level = str(row.get("alert_level") or ALERT_NONE)
        qty = int(row.get("post_shipment_total_qty") or 0)
        return (alert_sort_rank(level), -qty)

    return sorted(rows, key=sort_key)
