from __future__ import annotations

from collections.abc import Callable
from datetime import date

from application.inventory_order_alert.domain.value_objects.list_rows import apply_alert_levels_to_rows
from application.inventory_order_alert.domain.value_objects.list_query import ListQuery
from application.inventory_order_alert.domain.repositories.ports import LoadAppSettings, LoadEditableSnapshot, PersistEditableSnapshot
from application.inventory_order_alert.domain.value_objects.summary import EditableSummarySnapshot
from application.inventory_order_alert.domain.value_objects.alert_level import normalize_alert_level
from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings
from application.inventory_order_alert.domain.value_objects.snapshot_patch import (
    SnapshotRowPatchResult,
    find_snapshot_row_index,
)

ReconcileConfirmationsAfterImport = Callable[[list[dict[str, object]]], int]


class PatchSnapshotRow:
    def __init__(
        self,
        load_app_settings: LoadAppSettings,
        load_editable_snapshot: LoadEditableSnapshot,
        persist_snapshot: PersistEditableSnapshot,
        reconcile_confirmations_after_import: ReconcileConfirmationsAfterImport,
    ) -> None:
        self._load_app_settings = load_app_settings
        self._load_editable_snapshot = load_editable_snapshot
        self._persist_snapshot = persist_snapshot
        self._reconcile_confirmations_after_import = reconcile_confirmations_after_import

    def execute(
        self,
        *,
        cust_code: str,
        item_cd: str,
        last_ship_date: date | None = None,
        last_incoming_date: date | None = None,
        post_shipment_count: int | None = None,
        run_reconcile: bool = False,
        app_settings: AppSettings | None = None,
    ) -> SnapshotRowPatchResult:
        if last_ship_date is None and last_incoming_date is None and post_shipment_count is None:
            raise ValueError("更新する項目（last_ship_date 等）を1つ以上指定してください。")

        settings = app_settings or self._load_app_settings()
        editable = self._load_editable_snapshot()
        rows = list(editable.rows)
        index = find_snapshot_row_index(rows, cust_code=cust_code, item_cd=item_cd)
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
        rows = self._apply_alert_levels(rows, editable=editable, app_settings=settings)
        updated = rows[index]
        new_alert_level = normalize_alert_level(str(updated.get("alert_level") or ""))

        self._persist_snapshot(editable, rows)
        reset_count = self._reconcile_confirmations_after_import(rows) if run_reconcile else 0
        return SnapshotRowPatchResult(
            cust_code=cust_code,
            item_cd=item_cd,
            previous_last_ship_date=previous_last_ship_date,
            new_last_ship_date=str(updated.get("last_ship_date") or ""),
            previous_alert_level=previous_alert_level,
            new_alert_level=new_alert_level,
            confirmation_reset_count=reset_count,
        )

    @staticmethod
    def _apply_alert_levels(
        rows: list[dict[str, object]],
        *,
        editable: EditableSummarySnapshot,
        app_settings: AppSettings,
    ) -> list[dict[str, object]]:
        as_of_date = editable.as_of_date
        return apply_alert_levels_to_rows(
            rows,
            as_of_date=as_of_date,
            query=ListQuery(
                as_of_date=as_of_date,
                warning_shipment_months=app_settings.warning_shipment_months,
                warning_incoming_months=app_settings.warning_incoming_months,
                critical_enabled=app_settings.critical_enabled,
            ),
        )
