from __future__ import annotations

from django.utils import timezone

from application.sales.infrastructure.oracle.client import (
    OracleNotConfiguredError,
    OracleQueryError,
    oracle_connection,
)
from application.inventory_order_alert.domain.value_objects.list_query import ListQuery
from application.inventory_order_alert.infrastructure.persistence.settings_repository import load_app_settings
from application.inventory_order_alert.infrastructure.persistence.summary_snapshot_repository import store_summary_snapshot
from application.inventory_order_alert.infrastructure.persistence.confirmation_repository import reconcile_confirmations_after_import
from application.inventory_order_alert.domain.value_objects.slims_stock import SlimsStockLocationLine
from application.inventory_order_alert.infrastructure.oracle.list_rows_builder import build_list_rows
from application.inventory_order_alert.models import SlimsStockImport


def run_summary_aggregation(
    import_record: SlimsStockImport,
    stock_lines: list[SlimsStockLocationLine],
) -> tuple[str, int]:
    app_settings = load_app_settings()
    as_of_date = timezone.localdate(import_record.imported_at)
    query = ListQuery(
        as_of_date=as_of_date,
        alert_only=False,
        warning_shipment_months=app_settings.warning_shipment_months,
        warning_incoming_months=app_settings.warning_incoming_months,
        critical_enabled=app_settings.critical_enabled,
    )
    try:
        with oracle_connection() as connection:
            rows = build_list_rows(
                connection,
                query,
                stock_lines=stock_lines,
                stock_as_of_date=as_of_date,
            )
    except (OracleNotConfiguredError, OracleQueryError, Exception) as exc:
        store_summary_snapshot(import_record, [], as_of_date=as_of_date, aggregation_error=str(exc))
        return str(exc), 0

    store_summary_snapshot(import_record, rows, as_of_date=as_of_date)
    reset_count = reconcile_confirmations_after_import(rows)
    return "", reset_count
