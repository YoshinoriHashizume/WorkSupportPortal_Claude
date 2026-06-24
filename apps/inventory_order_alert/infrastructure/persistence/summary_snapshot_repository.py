from __future__ import annotations

from datetime import date

from apps.inventory_order_alert.domain.row_counts import count_rows
from apps.inventory_order_alert.domain.summary import EditableSummarySnapshot
from apps.inventory_order_alert.infrastructure.persistence.summary_row_codec import row_from_stored, row_to_storable
from apps.inventory_order_alert.models import InventoryOrderAlertSummarySnapshot, SlimsStockImport


def store_summary_snapshot(
    import_record: SlimsStockImport,
    rows: list[dict[str, object]],
    *,
    as_of_date: date,
    aggregation_error: str = "",
) -> InventoryOrderAlertSummarySnapshot:
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


def load_latest_editable_snapshot() -> EditableSummarySnapshot:
    import_record = SlimsStockImport.objects.order_by("-imported_at").first()
    if import_record is None:
        raise ValueError("SLIMS 在庫の取込履歴がありません。")
    snapshot = InventoryOrderAlertSummarySnapshot.objects.filter(import_record=import_record).first()
    if snapshot is None:
        raise ValueError("集計スナップショットがありません。")
    if snapshot.aggregation_error:
        raise ValueError(f"集計エラーのためパッチできません: {snapshot.aggregation_error}")
    return EditableSummarySnapshot(
        id=snapshot.id,
        as_of_date=snapshot.as_of_date,
        rows=[row_from_stored(row) for row in snapshot.rows],
    )


def persist_editable_snapshot(snapshot: EditableSummarySnapshot, rows: list[dict[str, object]]) -> None:
    counts = count_rows(rows)
    InventoryOrderAlertSummarySnapshot.objects.filter(pk=snapshot.id).update(
        rows=[row_to_storable(row) for row in rows],
        total_count=counts.total,
        critical_count=counts.critical,
        warning_count=counts.warning,
    )
