"""取込ユースケースのテスト（test-design.md TC-SFV-A-001〜002）。

需要予測（V-220）の算出はユースケース層が domain の `attach_demand_forecast` を
取込ポート（`StockImporter`）の後処理として渡すことで行う（05 design §6.7）。
"""

from __future__ import annotations

from datetime import date, datetime

from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings
from application.inventory_order_alert.domain.value_objects.demand_forecast import BASIS_ACTUAL, attach_demand_forecast
from application.inventory_order_alert.domain.value_objects.summary import StockImportInfo, SummaryLoadResult
from application.inventory_order_alert.use_cases.import_stock import ImportStock
from application.inventory_order_alert.use_cases.list_page import ListPage

AS_OF = date(2026, 9, 15)


def _stock_info(**overrides: object) -> StockImportInfo:
    values: dict[str, object] = {
        "imported_at": datetime(2026, 9, 15, 9, 0),
        "row_count": 1,
        "file_name": "sample.csv",
        "stock_as_of_date": AS_OF,
        "stock_as_of_label": "2026年9月15日時点の在庫",
        "summary_row_count": 1,
    }
    values.update(overrides)
    return StockImportInfo(**values)


# --- TC-SFV-A-001: 取込フローで需要予測が付与されてから保存される ---


def test_a001_import_stock_passes_attach_demand_forecast_as_row_post_processing():
    captured: dict[str, object] = {}

    def fake_import(text, *, user=None, file_name="", enrich_rows=None):
        captured["enrich_rows"] = enrich_rows
        return _stock_info()

    ImportStock(fake_import).execute(b"item,loc,qty\nA,B,1", file_name="sample.csv")

    assert captured["enrich_rows"] is attach_demand_forecast


def test_a001_post_processing_attaches_demand_forecast_to_rows():
    """ポートに渡した後処理を集計行に適用すると、保存前の行に需要予測の項目が付く。"""
    captured: dict[str, object] = {}

    def fake_import(text, *, user=None, file_name="", enrich_rows=None):
        rows = [
            {
                "cust_code": "100",
                "item_cd": "X",
                "internal_item_cd": "X-9065",
                "level1_item_cd": "X-9065",
                "level1_vend_cd": "9065",
                "stock_qty": "1200",
                "shipment_trend": [{"month": f"M{index:02d}", "qty": 100} for index in range(24)],
                "unconfirmed_order_trend": [{"month": "2026-09", "qty": 0}] * 4,
            }
        ]
        captured["stored"] = enrich_rows(rows, AS_OF) if enrich_rows else rows
        return _stock_info()

    ImportStock(fake_import).execute(b"x", file_name="sample.csv")

    [row] = captured["stored"]
    assert row["demand_forecast_basis"] == BASIS_ACTUAL
    assert row["months_of_stock"] == 12.0
    assert row["stockout_forecast_month"] == "2027-10"  # 12 か月で 0、翌月に初めて負
    assert row["reconciliation_unit_key"] == "X"


def test_a001_import_stock_still_decodes_and_forwards_file_name():
    captured: dict[str, object] = {}

    def fake_import(text, *, user=None, file_name="", enrich_rows=None):
        captured["text"] = text
        captured["file_name"] = file_name
        return _stock_info()

    ImportStock(fake_import).execute("品目".encode("cp932"), file_name="sample.csv")

    assert captured["text"] == "品目"
    assert captured["file_name"] == "sample.csv"


# --- TC-SFV-A-002: 内示受注の取得失敗でも取込は成功する ---


def test_a002_import_warning_is_shown_in_import_message_without_failing():
    warning = "内示受注の取得に失敗: ORA-00942: 表またはビューが存在しません。"
    info = _stock_info(aggregation_warning=warning)

    def fake_import(text, *, user=None, file_name="", enrich_rows=None):
        return info

    def load_summary() -> SummaryLoadResult:
        return SummaryLoadResult(
            rows=[
                {
                    "cust_code": "100",
                    "cust_name": "テスト得意先",
                    "cust_chrg_psn_cd": "A01",
                    "item_cd": "X",
                    "level1_item_cd": "",
                    "level1_vend_cd": "",
                    "level1_vend_name": "",
                    "last_incoming_date": "2025/04/02",
                    "last_ship_date": "2026/06/15",
                    "post_shipment_count": 1,
                    "post_shipment_total_qty": 10,
                    "stock_qty": "100",
                    "stock_as_of_label": "2026年9月15日時点の在庫",
                    "confirmation_status": "未確認",
                }
            ],
            stock_info=info,
            as_of_date=AS_OF,
            aggregation_error="",
            total_count=1,
            critical_count=0,
            warning_count=0,
        )

    context = ListPage(ImportStock(fake_import), load_summary, AppSettings).execute(
        query_params={},
        uploaded_csv=("sample.csv", b"x"),
    )

    assert context.error_message == ""
    assert "1 件を集計しました" in context.import_message
    assert warning in context.import_message
    assert context.has_list_data is True


def test_a002_stock_import_info_defaults_to_no_warning():
    assert _stock_info().aggregation_warning == ""
