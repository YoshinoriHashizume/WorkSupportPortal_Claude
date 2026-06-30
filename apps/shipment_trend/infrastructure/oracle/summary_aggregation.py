from __future__ import annotations

from django.utils import timezone

from apps.gonenkukumi.infrastructure.oracle.client import (
    OracleNotConfiguredError,
    OracleQueryError,
    oracle_connection,
)
from apps.shipment_trend.domain.trend_builder import build_trend_rows
from apps.shipment_trend.infrastructure.oracle.shipment_queries import (
    fetch_customer_names,
    fetch_monthly_shipments,
)
from apps.shipment_trend.infrastructure.persistence.summary_snapshot_repository import store_summary_snapshot
from apps.shipment_trend.models import ShipmentTrendRefresh


def run_summary_aggregation(refresh_record: ShipmentTrendRefresh) -> tuple[str, int]:
    as_of_date = timezone.localdate(refresh_record.refreshed_at)
    try:
        with oracle_connection() as connection:
            customer_names = fetch_customer_names(connection)
            records = fetch_monthly_shipments(connection)
            rows = build_trend_rows(records, customer_names, as_of_date=as_of_date)
    except (OracleNotConfiguredError, OracleQueryError, Exception) as exc:
        store_summary_snapshot(refresh_record, [], as_of_date=as_of_date, aggregation_error=str(exc))
        return str(exc), 0

    store_summary_snapshot(refresh_record, rows, as_of_date=as_of_date)
    return "", len(rows)
