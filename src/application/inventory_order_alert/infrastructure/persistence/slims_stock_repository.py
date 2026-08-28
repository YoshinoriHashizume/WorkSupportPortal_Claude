from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from application.inventory_order_alert.domain.value_objects.summary import StockImportInfo
from application.inventory_order_alert.domain.value_objects.dates import format_stock_as_of_label
from application.inventory_order_alert.domain.value_objects.slims_stock import SlimsStockLocationLine, parse_slims_stock_csv
from application.inventory_order_alert.infrastructure.oracle.summary_aggregation import run_summary_aggregation
from application.inventory_order_alert.infrastructure.persistence.import_lock import slims_import_lock
from application.inventory_order_alert.models import InventoryOrderAlertSummarySnapshot, SlimsStockImport, SlimsStockSnapshot


def import_slims_csv_text(
    text: str,
    *,
    user: object | None = None,
    file_name: str = "",
) -> StockImportInfo:
    lines = parse_slims_stock_csv(text)
    # 取込は「在庫保存 → Oracle 全件集計 → スナップショット保存」を全件差し替えで行うため、
    # 排他ロックを取得したうえで単一トランザクションで実行する（機能仕様書 §3「取込の排他」・§7.2）。
    with transaction.atomic(), slims_import_lock():
        SlimsStockSnapshot.objects.all().delete()
        import_record = SlimsStockImport.objects.create(
            imported_by=user if getattr(user, "is_authenticated", False) else None,
            file_name=file_name,
            row_count=len(lines),
        )
        SlimsStockSnapshot.objects.bulk_create(
            [
                SlimsStockSnapshot(
                    import_record=import_record,
                    item_cd=line.item_cd,
                    wloccd=line.wloccd,
                    stock_qty=line.stock_qty,
                    wnyudt=line.wnyudt,
                )
                for line in lines
            ]
        )
        aggregation_error, confirmation_reset_count = run_summary_aggregation(import_record, lines)
    stock_date = timezone.localdate(import_record.imported_at)
    snapshot = InventoryOrderAlertSummarySnapshot.objects.filter(import_record=import_record).first()
    return StockImportInfo(
        imported_at=import_record.imported_at,
        row_count=import_record.row_count,
        file_name=import_record.file_name,
        stock_as_of_date=stock_date,
        stock_as_of_label=format_stock_as_of_label(stock_date),
        summary_row_count=snapshot.total_count if snapshot else 0,
        aggregation_error=aggregation_error,
        confirmation_reset_count=confirmation_reset_count,
    )


def load_latest_stock_lines() -> tuple[list[SlimsStockLocationLine], StockImportInfo | None]:
    import_record = SlimsStockImport.objects.order_by("-imported_at").first()
    if import_record is None:
        return [], None

    lines = [
        SlimsStockLocationLine(
            item_cd=snapshot.item_cd,
            wloccd=snapshot.wloccd,
            stock_qty=snapshot.stock_qty,
            wnyudt=snapshot.wnyudt,
        )
        for snapshot in SlimsStockSnapshot.objects.filter(import_record=import_record)
    ]
    stock_date = timezone.localdate(import_record.imported_at)
    info = StockImportInfo(
        imported_at=import_record.imported_at,
        row_count=import_record.row_count,
        file_name=import_record.file_name,
        stock_as_of_date=stock_date,
        stock_as_of_label=format_stock_as_of_label(stock_date),
    )
    return lines, info
