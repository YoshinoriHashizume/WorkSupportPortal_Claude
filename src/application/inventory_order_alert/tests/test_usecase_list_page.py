from __future__ import annotations

from datetime import date, datetime

from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings
from application.inventory_order_alert.domain.value_objects.summary import (
    StockImportInfo,
    SummaryLoadResult,
)
from application.inventory_order_alert.use_cases.list_page import ListPage


def _row(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "cust_code": "112",
        "cust_name": "テスト得意先",
        "cust_chrg_psn_cd": "A01",
        "item_cd": "90249-10112",
        "level1_item_cd": "90249-10112-9209",
        "level1_vend_cd": "9209",
        "level1_vend_name": "小野メッキ",
        "last_incoming_date": "2022/01/31",
        "last_ship_date": "2025/11/27",
        "post_shipment_count": 2,
        "post_shipment_total_qty": 250,
        "stock_qty": "100",
        "mari_stock_qty": 95,
        "stock_location_detail": "2D0-03-5=100",
        "stock_as_of_label": "2026年6月17日時点の在庫",
        "confirmation_status": "未確認",
    }
    base.update(overrides)
    return base


def _stock_info() -> StockImportInfo:
    return StockImportInfo(
        imported_at=datetime(2026, 6, 17, 9, 0),
        row_count=1,
        file_name="sample.csv",
        stock_as_of_date=date(2026, 6, 17),
        stock_as_of_label="2026年6月17日時点の在庫",
        summary_row_count=1,
    )


def _execute(rows: list[dict[str, object]]):
    summary = SummaryLoadResult(
        rows=rows,
        stock_info=_stock_info(),
        as_of_date=date(2026, 6, 17),
        aggregation_error="",
        total_count=len(rows),
        critical_count=0,
        warning_count=0,
    )

    def _fail_import(*args: object, **kwargs: object) -> object:  # pragma: no cover - 呼ばれないこと自体が検証対象
        raise AssertionError("一覧表示で取込を実行してはならない")

    class _Importer:
        execute = staticmethod(_fail_import)

    usecase = ListPage(
        import_stock_usecase=_Importer(),
        load_summary=lambda: summary,
        load_app_settings=AppSettings,
    )
    return usecase.execute(query_params={})


def test_list_page_passes_mari_stock_quantity_through():
    context = _execute([_row()])

    assert context.all_rows[0]["mari_stock_qty"] == 95


def test_list_page_does_not_import_stock_when_no_csv_is_uploaded():
    # CSV 未添付の一覧表示では Oracle への集計を走らせない（TC-MSV-A-002）。
    context = _execute([_row()])

    assert context.error_message == ""


def test_list_page_table_headers_label_stock_columns_by_source():
    context = _execute([_row()])
    labels = [header.label for header in context.table_headers]

    assert "在庫数(SLIMS)" in labels
    assert "在庫数(MARI)" in labels
    assert "在庫数" not in labels


def test_list_page_table_headers_have_no_responsible_department():
    context = _execute([_row()])
    keys = [header.key for header in context.table_headers]

    assert "responsible_department" not in keys


def test_TC_SHC_A_001_list_page_passes_shipment_trend_through():
    trend = [{"month": "2026-06", "qty": 10}]
    context = _execute([_row(shipment_trend=trend)])

    assert context.all_rows[0]["shipment_trend"] == trend


def test_TC_SHC_A_002_list_page_does_not_import_stock_when_no_csv_is_uploaded():
    # 出荷推移の追加後も、一覧表示では Oracle への集計を走らせない（REQ-SHC-NF-001）。
    context = _execute([_row(shipment_trend=[{"month": "2026-06", "qty": 10}])])

    assert context.error_message == ""


def test_list_page_keeps_rows_without_mari_stock_key_unchanged():
    row = _row()
    del row["mari_stock_qty"]

    context = _execute([row])

    # 未取得は「キーが無い」ことで表現する。空文字で埋めない（design.md §4.2）。
    assert "mari_stock_qty" not in context.all_rows[0]
