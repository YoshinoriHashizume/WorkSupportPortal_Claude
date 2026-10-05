"""取込ユースケースのテスト（test-design.md TC-SFV-A-001〜002）。

需要予測（V-220）の算出はユースケース層が domain の `attach_demand_forecast` を
取込ポート（`StockImporter`）の後処理として渡すことで行う（05 design §6.7）。
"""

from __future__ import annotations

from datetime import date, datetime

from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings
from application.inventory_order_alert.domain.value_objects.demand_forecast import BASIS_UNCONFIRMED
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

    # 08 で対応区分に作り直したため、渡されるのは需要予測 → 流動区分 → 対応区分の順に適用する後処理
    assert callable(captured["enrich_rows"])
    enriched = captured["enrich_rows"]([{"cust_code": "100", "item_cd": "X"}], AS_OF)
    assert enriched[0]["demand_forecast_basis"] == "なし"
    assert enriched[0]["response_class"] == "対象外"  # 内示なし → 在庫は動かない


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
                "unconfirmed_order_trend": [
                    {"month": "2026-09", "qty": 0},
                    {"month": "2026-10", "qty": 100},
                    {"month": "2026-11", "qty": 100},
                    {"month": "2026-12", "qty": 100},
                ],
            }
        ]
        captured["stored"] = enrich_rows(rows, AS_OF) if enrich_rows else rows
        return _stock_info()

    ImportStock(fake_import).execute(b"x", file_name="sample.csv")

    [row] = captured["stored"]
    assert row["demand_forecast_basis"] == BASIS_UNCONFIRMED
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


# --- 08_stockout-risk-rework: TC-SRR-I-004（取込の順序） ---

from application.inventory_order_alert.domain.value_objects.flow_facts import (  # noqa: E402
    FLOW_REASON_INCOMING_BELOW_DEMAND,
)
from application.inventory_order_alert.domain.value_objects.flow_quadrant import QUADRANT_STOCKOUT  # noqa: E402
from application.inventory_order_alert.domain.value_objects.stockout_risk import (  # noqa: E402
    RESPONSE_ORDER_NEEDED,
)


def _stage3_row() -> dict[str, object]:
    return {
        "cust_code": "100",
        "item_cd": "X",
        "internal_item_cd": "X-9065",
        "level1_item_cd": "X-9065",
        "level1_vend_cd": "9065",
        # 取込では需要予測のあとに流動区分を引き直す（07 design §3.1）ため、判定の元になる日付を持たせる。
        # 最終入荷 2025/04/02 は基準日 2026/09/15 の 1 年より前、最終出荷 2026/06/15 は 1 年内 → 低流動品（入荷なし）
        "last_incoming_date": "2025/04/02",
        "last_ship_date": "2026/06/15",
        "stock_qty": "90",
        "shipment_trend": [{"month": f"M{index:02d}", "qty": 100} for index in range(24)],
        "unconfirmed_order_trend": [
            {"month": "2026-09", "qty": 0},
            {"month": "2026-10", "qty": 100},
            {"month": "2026-11", "qty": 100},
            {"month": "2026-12", "qty": 100},
        ],
        # 08: 対応区分は日次の内示だけを見る（月次の `unconfirmed_order_trend` は需要予測が使う）
        "unconfirmed_order_daily": [{"date": "2026-10-01", "qty": 100}],
        "open_purchase_orders": [],
        "open_purchase_orders_unknown": False,
        "lead_time_days": 0,
        "lead_time_source": "default",
        "ordering_method": "手動発注",
    }


def _run_import(load_settings):
    captured: dict[str, object] = {}

    def fake_import(text, *, user=None, file_name="", enrich_rows=None):
        captured["stored"] = enrich_rows([_stage3_row()], AS_OF) if enrich_rows else []
        return _stock_info()

    ImportStock(fake_import, load_settings).execute(b"x", file_name="sample.csv")
    return captured["stored"]


def test_i004_import_stock_composes_demand_forecast_then_response_class():
    [row] = _run_import(AppSettings)

    # 在庫 90・内示 10/01 に 100 → 10/01 に負 → 在庫切れ 2026/10/01。既定 LT 5 日 → 発注期限 2026/09/26（未来）→ 要発注
    assert row["demand_forecast_basis"] == BASIS_UNCONFIRMED
    assert row["stockout_forecast_month"] == "2026-10"
    assert row["response_class"] == RESPONSE_ORDER_NEEDED
    assert row["stockout_date"] == "2026/10/01"
    assert row["order_deadline"] == "2026/09/26"
    assert "在庫切れ 2026/10/01" in row["response_reasons"]
    assert "リードタイム未設定" in row["response_reasons"]
    assert row["lead_time_days"] == 5  # 既定リードタイム


def test_fqr_i001_import_reapplies_flow_quadrant_after_demand_forecast():
    """在庫なし・内示ありの行は 需要予測 → 流動区分の引き直し → 対応区分 の順で 欠品 になる（07 design §3.1）。"""
    row = _stage3_row() | {
        "stock_qty": "",
        "last_incoming_date": "2026/09/10",
        "last_ship_date": "2026/09/12",
        "incoming_trend": [{"month": "2026-09", "qty": 10}],
    }

    def fake_import(text, *, user=None, file_name="", enrich_rows=None):
        captured["stored"] = enrich_rows([row], AS_OF)
        return _stock_info()

    captured: dict[str, object] = {}
    ImportStock(fake_import, AppSettings).execute(b"x", file_name="sample.csv")
    [enriched] = captured["stored"]

    assert enriched["flow_quadrant"] == QUADRANT_STOCKOUT
    assert enriched["flow_quadrant_key"] == "stockout"
    assert enriched["flow_reasons"] == [FLOW_REASON_INCOMING_BELOW_DEMAND]
    # 在庫未取得は 0 として日次で計算する（REQ-SRR-F-002）。10/01 の内示 100 で切れる
    assert enriched["response_class"] == RESPONSE_ORDER_NEEDED
    assert enriched["stockout_date"] == "2026/10/01"


def test_fqr_i001_import_keeps_four_quadrants_for_rows_with_stock():
    """在庫がある行は従来どおり 4 区分（引き直しても変わらない）。"""
    [row] = _run_import(AppSettings)

    assert row["flow_quadrant"] == "低流動品（入荷なし）"
    assert row["flow_reasons"] == []


def test_fqr_f008_recent_incoming_days_setting_changes_the_stockout_split():
    """直近入荷の窓は設定値（REQ-FQR-F-008）。広げると 欠品（入荷なし）が 欠品 になる。"""
    row = _stage3_row() | {
        "stock_qty": "",
        "last_incoming_date": "2026/08/01",  # 基準日 2026/09/15 の 45 日前
        "last_ship_date": "2026/09/12",
    }

    def run(load_settings):
        captured: dict[str, object] = {}

        def fake_import(text, *, user=None, file_name="", enrich_rows=None):
            captured["stored"] = enrich_rows([row], AS_OF)
            return _stock_info()

        ImportStock(fake_import, load_settings).execute(b"x", file_name="sample.csv")
        [enriched] = captured["stored"]
        return enriched

    assert run(AppSettings)["flow_quadrant"] == "欠品（入荷なし）"  # 既定 30 日
    assert run(lambda: AppSettings(recent_incoming_days=60))["flow_quadrant"] == QUADRANT_STOCKOUT


def test_a002_default_lead_time_setting_moves_the_order_deadline():
    """既定リードタイム（設定値）は発注期限（V-233）に効く。安全日数・監視期間は 08 で撤去した。"""
    [row] = _run_import(lambda: AppSettings(default_lead_time_days=1))

    assert row["lead_time_days"] == 1
    assert row["stockout_date"] == "2026/10/01"
    assert row["order_deadline"] == "2026/09/30"  # 在庫切れ日 − 1 日


def test_a002_import_stock_without_settings_loader_uses_defaults():
    captured: dict[str, object] = {}

    def fake_import(text, *, user=None, file_name="", enrich_rows=None):
        captured["stored"] = enrich_rows([_stage3_row()], AS_OF)
        return _stock_info()

    ImportStock(fake_import).execute(b"x", file_name="sample.csv")

    assert captured["stored"][0]["order_deadline"] == "2026/09/26"  # 既定リードタイム 5 日
