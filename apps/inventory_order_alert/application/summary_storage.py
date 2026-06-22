from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from django.utils import timezone

from apps.inventory_order_alert.application.confirmation import attach_confirmation_fields, load_confirmation_map
from apps.inventory_order_alert.application.reconcile_confirmations import reconcile_confirmations_after_import
from apps.inventory_order_alert.application.list_summary import ListQuery, apply_alert_levels_to_rows, build_list_rows
from apps.inventory_order_alert.application.dashboard_summary import count_rows
from apps.inventory_order_alert.application.settings_service import get_app_settings
from apps.inventory_order_alert.domain.dates import format_stock_as_of_label
from apps.inventory_order_alert.domain.slims_stock import SlimsStockLocationLine
from apps.inventory_order_alert.models import InventoryOrderAlertSummarySnapshot, SlimsStockImport
from apps.gonenkukumi.infrastructure.oracle.client import (
    OracleNotConfiguredError,
    OracleQueryError,
    oracle_connection,
)


@dataclass(frozen=True)
class StockImportInfo:
    imported_at: datetime
    row_count: int
    file_name: str
    stock_as_of_date: date
    stock_as_of_label: str
    summary_row_count: int = 0
    aggregation_error: str = ""
    confirmation_reset_count: int = 0

    @property
    def has_data(self) -> bool:
        return self.row_count > 0


@dataclass(frozen=True)
class SummaryLoadResult:
    rows: list[dict[str, object]]
    stock_info: StockImportInfo | None
    as_of_date: date | None
    aggregation_error: str
    total_count: int
    critical_count: int
    warning_count: int

    @property
    def has_summary(self) -> bool:
        return bool(self.rows) or bool(self.aggregation_error)


def row_to_storable(row: dict[str, object]) -> dict[str, object]:
    stored: dict[str, object] = {}
    for key, value in row.items():
        if isinstance(value, Decimal):
            stored[key] = str(value)
        elif isinstance(value, (date, datetime)):
            stored[key] = value.isoformat()
        else:
            stored[key] = value
    return stored


def row_from_stored(row: dict[str, object]) -> dict[str, object]:
    return dict(row)


def store_summary_snapshot(
    import_record: SlimsStockImport,
    rows: list[dict[str, object]],
    *,
    as_of_date: date,
    aggregation_error: str = "",
) -> InventoryOrderAlertSummarySnapshot:
    from apps.inventory_order_alert.application.dashboard_summary import count_rows

    storable_rows = [row_to_storable(row) for row in rows]
    counts = count_rows(rows)
    snapshot, _ = InventoryOrderAlertSummarySnapshot.objects.update_or_create(
        import_record=import_record,
        defaults={
            "as_of_date": as_of_date,
            "rows": storable_rows,
            "total_count": counts.total,
            "critical_count": counts.critical,
            "warning_count": counts.warning,
            "aggregation_error": aggregation_error,
        },
    )
    return snapshot


def run_summary_aggregation(
    import_record: SlimsStockImport,
    stock_lines: list[SlimsStockLocationLine],
) -> tuple[str, int]:
    app_settings = get_app_settings()
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


def _stock_info_from_import(import_record: SlimsStockImport) -> StockImportInfo:
    stock_date = timezone.localdate(import_record.imported_at)
    return StockImportInfo(
        imported_at=import_record.imported_at,
        row_count=import_record.row_count,
        file_name=import_record.file_name,
        stock_as_of_date=stock_date,
        stock_as_of_label=format_stock_as_of_label(stock_date),
    )


def load_latest_summary() -> SummaryLoadResult | None:
    import_record = SlimsStockImport.objects.order_by("-imported_at").first()
    if import_record is None:
        return None

    stock_info = _stock_info_from_import(import_record)
    snapshot = (
        InventoryOrderAlertSummarySnapshot.objects.filter(import_record=import_record)
        .order_by("-id")
        .first()
    )
    if snapshot is None:
        return SummaryLoadResult(
            rows=[],
            stock_info=stock_info,
            as_of_date=None,
            aggregation_error="",
            total_count=0,
            critical_count=0,
            warning_count=0,
        )

    stored_rows = [row_from_stored(row) for row in snapshot.rows]
    rows = attach_confirmation_fields(stored_rows, load_confirmation_map())
    app_settings = get_app_settings()
    as_of_date = snapshot.as_of_date or stock_info.stock_as_of_date
    rows = apply_alert_levels_to_rows(
        rows,
        as_of_date=as_of_date,
        query=ListQuery(
            as_of_date=as_of_date,
            warning_shipment_months=app_settings.warning_shipment_months,
            warning_incoming_months=app_settings.warning_incoming_months,
            critical_enabled=app_settings.critical_enabled,
        ),
    )
    from apps.inventory_order_alert.application.stock_storage import load_latest_stock_lines
    from apps.inventory_order_alert.domain.stock_join import attach_stock_fields

    stock_lines, _ = load_latest_stock_lines()
    rows = attach_stock_fields(
        rows,
        stock_lines,
        stock_as_of_date=as_of_date,
    )
    counts = count_rows(rows)
    return SummaryLoadResult(
        rows=rows,
        stock_info=stock_info,
        as_of_date=snapshot.as_of_date,
        aggregation_error=snapshot.aggregation_error,
        total_count=counts.total,
        critical_count=counts.critical,
        warning_count=counts.warning,
    )


def load_latest_summary_rows() -> list[dict[str, object]]:
    summary = load_latest_summary()
    if summary is None:
        return []
    return summary.rows
