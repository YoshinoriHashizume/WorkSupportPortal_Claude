from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.repositories.ports import (
    LoadEditableSnapshot,
    PersistEditableSnapshot,
    ReconcileConfirmationsAfterImport,
)
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    REFERENCE_FLOW_SELECTION,
    normalize_flow_quadrant,
)
from application.inventory_order_alert.domain.value_objects.list_query import ListQuery
from application.inventory_order_alert.domain.value_objects.list_rows import apply_flow_quadrants_to_rows
from application.inventory_order_alert.domain.value_objects.snapshot_patch import (
    SnapshotRowPatchResult,
    find_snapshot_row_index,
)
from application.inventory_order_alert.domain.value_objects.summary import EditableSummarySnapshot


class PatchSnapshotRow:
    def __init__(
        self,
        load_editable_snapshot: LoadEditableSnapshot,
        persist_snapshot: PersistEditableSnapshot,
        reconcile_confirmations_after_import: ReconcileConfirmationsAfterImport,
    ) -> None:
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
    ) -> SnapshotRowPatchResult:
        if last_ship_date is None and last_incoming_date is None and post_shipment_count is None:
            raise ValueError("更新する項目（last_ship_date 等）を1つ以上指定してください。")

        editable = self._load_editable_snapshot()
        rows = list(editable.rows)
        index = find_snapshot_row_index(rows, cust_code=cust_code, item_cd=item_cd)
        target = dict(rows[index])

        previous_last_ship_date = str(target.get("last_ship_date") or "")
        previous_rows = self._apply_flow_quadrants(rows, editable=editable)
        previous_flow_quadrant = normalize_flow_quadrant(
            str(previous_rows[index].get("flow_quadrant") or "")
        )

        if last_ship_date is not None:
            target["last_ship_date"] = last_ship_date.strftime("%Y/%m/%d")
        if last_incoming_date is not None:
            target["last_incoming_date"] = last_incoming_date.strftime("%Y/%m/%d")
        if post_shipment_count is not None:
            target["post_shipment_count"] = post_shipment_count

        rows[index] = target
        rows = self._apply_flow_quadrants(rows, editable=editable)
        updated = rows[index]
        new_flow_quadrant = normalize_flow_quadrant(str(updated.get("flow_quadrant") or ""))

        self._persist_snapshot(editable, rows)
        reset_count = self._reconcile_confirmations_after_import(rows) if run_reconcile else 0
        return SnapshotRowPatchResult(
            cust_code=cust_code,
            item_cd=item_cd,
            previous_last_ship_date=previous_last_ship_date,
            new_last_ship_date=str(updated.get("last_ship_date") or ""),
            previous_flow_quadrant=previous_flow_quadrant,
            new_flow_quadrant=new_flow_quadrant,
            confirmation_reset_count=reset_count,
        )

    @staticmethod
    def _apply_flow_quadrants(
        rows: list[dict[str, object]],
        *,
        editable: EditableSummarySnapshot,
    ) -> list[dict[str, object]]:
        """基準判定条件で流動区分を付け直す（design.md §5.2）。

        スナップショットの部分更新は取込バッチ相当の処理であり、
        利用者が一覧で選んだ判定条件を知り得ないため固定条件を使う。
        """
        as_of_date = editable.as_of_date
        return apply_flow_quadrants_to_rows(
            rows,
            as_of_date=as_of_date,
            query=ListQuery(as_of_date=as_of_date, flow_selection=REFERENCE_FLOW_SELECTION),
        )
