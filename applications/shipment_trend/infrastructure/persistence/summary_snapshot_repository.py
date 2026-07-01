from __future__ import annotations

from applications.shipment_trend.models import ShipmentTrendRefresh, ShipmentTrendSummarySnapshot


def create_refresh_record(*, user: object | None) -> ShipmentTrendRefresh:
    return ShipmentTrendRefresh.objects.create(refreshed_by=user if getattr(user, "is_authenticated", False) else None)


def store_summary_snapshot(
    refresh_record: ShipmentTrendRefresh,
    rows: list[dict[str, object]],
    *,
    as_of_date,
    aggregation_error: str = "",
) -> ShipmentTrendSummarySnapshot:
    snapshot, _ = ShipmentTrendSummarySnapshot.objects.update_or_create(
        refresh_record=refresh_record,
        defaults={
            "as_of_date": as_of_date,
            "rows": rows,
            "total_count": len(rows),
            "aggregation_error": aggregation_error,
        },
    )
    refresh_record.row_count = len(rows)
    refresh_record.save(update_fields=["row_count"])
    return snapshot
