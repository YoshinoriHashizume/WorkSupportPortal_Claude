from __future__ import annotations

from django.utils import timezone

from application.sales.infrastructure.oracle.client import (
    OracleNotConfiguredError,
    OracleQueryError,
    oracle_connection,
)
from application.inventory_order_alert.domain.repositories.ports import EnrichRows
from application.inventory_order_alert.domain.value_objects.flow_quadrant import REFERENCE_FLOW_SELECTION
from application.inventory_order_alert.domain.value_objects.list_query import ListQuery
from application.inventory_order_alert.infrastructure.persistence.summary_snapshot_repository import store_summary_snapshot
from application.inventory_order_alert.infrastructure.persistence.confirmation_repository import reconcile_confirmations_after_import
from application.inventory_order_alert.domain.value_objects.slims_stock import SlimsStockLocationLine
from application.inventory_order_alert.infrastructure.oracle.list_rows_builder import build_list_rows
from application.inventory_order_alert.models import SlimsStockImport


def run_summary_aggregation(
    import_record: SlimsStockImport,
    stock_lines: list[SlimsStockLocationLine],
    *,
    enrich_rows: EnrichRows | None = None,
) -> tuple[str, int, str]:
    """集計 → 後処理（`enrich_rows`）→ 保存 の順で実行する（05 design §6.7）。

    戻り値は (集計エラー, 未確認に戻した件数, 警告)。警告は取込を止めない取得失敗（内示受注）で、
    `aggregation_error` には入れない（入れると一覧が「集計失敗」扱いになるため）。
    """
    as_of_date = timezone.localdate(import_record.imported_at)
    # 取込バッチは利用者の画面選択を知り得ないため既定の判定期間で固定する（05 design §6.5）。
    query = ListQuery(as_of_date=as_of_date, flow_selection=REFERENCE_FLOW_SELECTION)
    warnings: list[str] = []
    try:
        with oracle_connection() as connection:
            rows = build_list_rows(
                connection,
                query,
                stock_lines=stock_lines,
                stock_as_of_date=as_of_date,
                warnings=warnings,
            )
        if enrich_rows is not None:
            rows = enrich_rows(rows, as_of_date)
    except (OracleNotConfiguredError, OracleQueryError, Exception) as exc:
        store_summary_snapshot(import_record, [], as_of_date=as_of_date, aggregation_error=str(exc))
        return str(exc), 0, ""

    store_summary_snapshot(import_record, rows, as_of_date=as_of_date)
    reset_count = reconcile_confirmations_after_import(rows)
    return "", reset_count, " ".join(warnings)
