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

    # 06 で在庫切れリスクを合成したため、渡されるのは需要予測 → 在庫切れリスクの順に適用する後処理
    assert callable(captured["enrich_rows"])
    enriched = captured["enrich_rows"]([{"cust_code": "100", "item_cd": "X"}], AS_OF)
    assert enriched[0]["demand_forecast_basis"] == "なし"
    assert enriched[0]["stockout_risk"] == "監視"


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


# --- 06_stockout-risk: TC-SOR-A-001〜002 ---

from application.inventory_order_alert.domain.value_objects.flow_facts import (  # noqa: E402
    FLOW_REASON_INCOMING_BELOW_DEMAND,
)
from application.inventory_order_alert.domain.value_objects.flow_quadrant import QUADRANT_STOCKOUT  # noqa: E402
from application.inventory_order_alert.domain.value_objects.stockout_risk import (  # noqa: E402
    REASON_STOCK_MISSING,
    REASON_SUPPLY_DELAY,
    RISK_CAUTION,
    RISK_DANGER,
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


def test_a001_import_stock_composes_demand_forecast_then_stockout_risk():
    [row] = _run_import(AppSettings)

    # 内示 100/月（当月残 0）、在庫 90 → 10 月に負 → 在庫切れ 2026-10（猶予 14 日 ≤ 既定 LT 5 + 安全 14）、発注残なし → 危険
    assert row["demand_forecast_basis"] == BASIS_UNCONFIRMED
    assert row["stockout_forecast_month"] == "2026-10"
    assert row["stockout_risk"] == RISK_DANGER
    assert "発注忘れの可能性" in row["stockout_risk_reasons"]
    assert "仕入先の生産可否を先に確認" in row["stockout_risk_reasons"]
    assert row["lead_time_days"] == 5  # 既定リードタイム


def test_fqr_i001_import_reapplies_flow_quadrant_after_demand_forecast():
    """在庫なし・内示ありの行は 需要予測 → 流動区分の引き直し → 在庫切れリスク の順で 欠品 になる（07 design §3.1）。"""
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
    # 在庫なしの行は対象外にせず、理由の先頭に「在庫なし」が付く（07 design §2.6）
    assert enriched["stockout_risk_reasons"][:2] == [REASON_STOCK_MISSING, REASON_SUPPLY_DELAY]


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


def test_a002_settings_from_wiring_change_the_boundary():
    # 安全日数 1・既定 LT 1 なら 猶予 14 日 > 2 日 → 注意
    [row] = _run_import(lambda: AppSettings(safety_days=1, default_lead_time_days=1))

    assert row["stockout_risk"] == RISK_CAUTION
    assert row["lead_time_days"] == 1


def test_a002_import_stock_without_settings_loader_uses_defaults():
    captured: dict[str, object] = {}

    def fake_import(text, *, user=None, file_name="", enrich_rows=None):
        captured["stored"] = enrich_rows([_stage3_row()], AS_OF)
        return _stock_info()

    ImportStock(fake_import).execute(b"x", file_name="sample.csv")

    assert captured["stored"][0]["stockout_risk"] == RISK_DANGER
