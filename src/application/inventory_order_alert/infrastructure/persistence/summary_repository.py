from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.confirmation import attach_confirmation_fields
from application.inventory_order_alert.domain.value_objects.list_query import ListQuery
from application.inventory_order_alert.domain.value_objects.flow_quadrant import REFERENCE_FLOW_SELECTION
from application.inventory_order_alert.domain.value_objects.list_rows import apply_flow_quadrants_to_rows
from application.inventory_order_alert.domain.value_objects.row_counts import count_rows
from application.inventory_order_alert.domain.value_objects.stock_join import attach_stock_fields
from application.inventory_order_alert.domain.value_objects.summary import SummaryLoadResult
from application.inventory_order_alert.domain.value_objects.reconciliation_unit_row import build_reconciliation_unit_rows
from application.inventory_order_alert.infrastructure.persistence.confirmation_repository import load_confirmation_map, memo_author_names
from application.inventory_order_alert.infrastructure.persistence.slims_stock_repository import load_latest_stock_lines
from application.inventory_order_alert.infrastructure.persistence.summary_row_codec import row_from_stored, stock_info_from_import
from application.inventory_order_alert.models import InventoryOrderAlertSummarySnapshot, SlimsStockImport


def load_latest_summary() -> SummaryLoadResult | None:
    import_record = SlimsStockImport.objects.order_by("-imported_at").first()
    if import_record is None:
        return None

    stock_info = stock_info_from_import(import_record)
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
    as_of_date = snapshot.as_of_date or stock_info.stock_as_of_date
    # 処理順（spec/13 design §3.1）: 在庫の付与 → 照合単位行へのまとめ → 確認記録 → 流動区分 → 件数。
    # まとめるには得意先品番ごとの SLIMS 在庫数が要るため在庫を先に付け、流動区分はまとめた後に照合単位で判定する。
    stock_lines, _ = load_latest_stock_lines()
    rows = attach_stock_fields(
        stored_rows,
        stock_lines,
        stock_as_of_date=as_of_date,
    )
    rows = build_reconciliation_unit_rows(rows)
    confirmations = load_confirmation_map()
    rows = attach_confirmation_fields(rows, confirmations, author_names=memo_author_names(confirmations))
    # 読込のたびに基準判定条件で再判定する。スナップショットには流動区分を保存しない（design.md §3.1）。
    # 利用者が選んだ判定条件は use_cases 側で付け直す。
    rows = apply_flow_quadrants_to_rows(
        rows,
        as_of_date=as_of_date,
        query=ListQuery(as_of_date=as_of_date, flow_selection=REFERENCE_FLOW_SELECTION),
    )
    counts = count_rows(rows)
    return SummaryLoadResult(
        rows=rows,
        stock_info=stock_info,
        as_of_date=snapshot.as_of_date,
        aggregation_error=snapshot.aggregation_error,
        total_count=counts.total,
        # 残置カラムへの詰め替え規則（design.md §5.1）。カラム名は据え置く。
        critical_count=counts.low_flow_no_incoming,
        warning_count=counts.dormant_stock + counts.low_flow_no_shipment,
    )


def load_latest_summary_rows() -> list[dict[str, object]]:
    summary = load_latest_summary()
    if summary is None:
        return []
    return summary.rows
