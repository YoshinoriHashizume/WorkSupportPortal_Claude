from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from django.utils import timezone

from apps.inventory_order_alert.application.dashboard_summary import count_rows
from apps.inventory_order_alert.application.list_summary import ListQuery, apply_alert_levels_to_rows
from apps.inventory_order_alert.application.reconcile_confirmations import reconcile_confirmations_after_import
from apps.inventory_order_alert.application.settings_service import get_app_settings
from apps.inventory_order_alert.application.summary_storage import row_from_stored, row_to_storable
from apps.inventory_order_alert.domain.alert_level import normalize_alert_level
from apps.inventory_order_alert.models import InventoryOrderAlertSummarySnapshot, SlimsStockImport


@dataclass(frozen=True)
class SnapshotRowPatchResult:
    cust_code: str
    item_cd: str
    previous_last_ship_date: str
    new_last_ship_date: str
    previous_alert_level: str
    new_alert_level: str
    confirmation_reset_count: int


def parse_patch_date(value: str, *, today: date | None = None) -> date:
    text = str(value or "").strip().lower()
    if text in {"today", "今日"}:
        return today or timezone.localdate()
    normalized = text.replace("-", "/")
    for fmt in ("%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(normalized, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"日付形式が不正です: {value}")


def _find_row_index(rows: list[dict[str, object]], *, cust_code: str, item_cd: str) -> int:
    for index, row in enumerate(rows):
        if str(row.get("cust_code") or "") == cust_code and str(row.get("item_cd") or "") == item_cd:
            return index
    raise ValueError(f"スナップショットに cust_code={cust_code}, item_cd={item_cd} の行がありません。")


def load_latest_snapshot() -> InventoryOrderAlertSummarySnapshot:
    import_record = SlimsStockImport.objects.order_by("-imported_at").first()
    if import_record is None:
        raise ValueError("SLIMS 在庫の取込履歴がありません。")
    snapshot = InventoryOrderAlertSummarySnapshot.objects.filter(import_record=import_record).first()
    if snapshot is None:
        raise ValueError("集計スナップショットがありません。")
    if snapshot.aggregation_error:
        raise ValueError(f"集計エラーのためパッチできません: {snapshot.aggregation_error}")
    return snapshot


def patch_snapshot_row(
    *,
    cust_code: str,
    item_cd: str,
    last_ship_date: date | None = None,
    last_incoming_date: date | None = None,
    post_shipment_count: int | None = None,
    run_reconcile: bool = False,
) -> SnapshotRowPatchResult:
    if last_ship_date is None and last_incoming_date is None and post_shipment_count is None:
        raise ValueError("更新する項目（last_ship_date 等）を1つ以上指定してください。")

    snapshot = load_latest_snapshot()
    rows = [row_from_stored(row) for row in snapshot.rows]
    index = _find_row_index(rows, cust_code=cust_code, item_cd=item_cd)
    target = dict(rows[index])

    previous_last_ship_date = str(target.get("last_ship_date") or "")
    previous_alert_level = normalize_alert_level(str(target.get("alert_level") or ""))

    if last_ship_date is not None:
        target["last_ship_date"] = last_ship_date.strftime("%Y/%m/%d")
    if last_incoming_date is not None:
        target["last_incoming_date"] = last_incoming_date.strftime("%Y/%m/%d")
    if post_shipment_count is not None:
        target["post_shipment_count"] = post_shipment_count

    rows[index] = target

    app_settings = get_app_settings()
    as_of_date = snapshot.as_of_date
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
    updated = rows[index]
    new_alert_level = normalize_alert_level(str(updated.get("alert_level") or ""))

    counts = count_rows(rows)
    snapshot.rows = [row_to_storable(row) for row in rows]
    snapshot.total_count = counts.total
    snapshot.critical_count = counts.critical
    snapshot.warning_count = counts.warning
    snapshot.save(
        update_fields=[
            "rows",
            "total_count",
            "critical_count",
            "warning_count",
        ]
    )

    reset_count = reconcile_confirmations_after_import(rows) if run_reconcile else 0
    return SnapshotRowPatchResult(
        cust_code=cust_code,
        item_cd=item_cd,
        previous_last_ship_date=previous_last_ship_date,
        new_last_ship_date=str(updated.get("last_ship_date") or ""),
        previous_alert_level=previous_alert_level,
        new_alert_level=new_alert_level,
        confirmation_reset_count=reset_count,
    )
