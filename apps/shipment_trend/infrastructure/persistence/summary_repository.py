from __future__ import annotations

from django.utils import timezone

from apps.shipment_trend.domain.summary import SummaryLoadResult
from apps.shipment_trend.models import ShipmentTrendRefresh, ShipmentTrendSummarySnapshot


def load_latest_summary() -> SummaryLoadResult | None:
    refresh_record = ShipmentTrendRefresh.objects.order_by("-refreshed_at").first()
    if refresh_record is None:
        return None

    snapshot = (
        ShipmentTrendSummarySnapshot.objects.filter(refresh_record=refresh_record)
        .order_by("-id")
        .first()
    )
    if snapshot is None:
        return SummaryLoadResult(
            rows=[],
            as_of_date=None,
            aggregation_error="",
            total_count=0,
            refreshed_at=timezone.localdate(refresh_record.refreshed_at),
        )

    return SummaryLoadResult(
        rows=list(snapshot.rows),
        as_of_date=snapshot.as_of_date,
        aggregation_error=snapshot.aggregation_error or "",
        total_count=snapshot.total_count,
        refreshed_at=timezone.localdate(refresh_record.refreshed_at),
    )
