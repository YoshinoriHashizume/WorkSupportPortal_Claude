from __future__ import annotations

import pytest

from application.inventory_order_alert.use_cases.import_stock import ImportStock


def test_import_stock_usecase_delegates_to_injected_importer():
    captured: dict[str, object] = {}

    def fake_import(text, *, user=None, file_name="", enrich_rows=None):
        captured["text"] = text
        captured["file_name"] = file_name
        return object()

    use_case = ImportStock(fake_import)
    use_case.execute(b"item,loc,qty\nA,B,1", file_name="sample.csv")
    assert "item,loc,qty" in str(captured["text"])
    assert captured["file_name"] == "sample.csv"


def test_import_stock_usecase_decodes_cp932_bytes():
    captured: dict[str, object] = {}

    def fake_import(text, *, user=None, file_name="", enrich_rows=None):
        captured["text"] = text
        return object()

    ImportStock(fake_import).execute("品目".encode("cp932"), file_name="sample.csv")
    assert captured["text"] == "品目"


# --- 05_single-flow-view: 一覧・CSV ユースケース（TC-SFV-A-003、A-005） ---

from dataclasses import fields  # noqa: E402
from datetime import date, datetime  # noqa: E402

from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings  # noqa: E402
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (  # noqa: E402
    QUADRANT_LOW_FLOW_NO_INCOMING,
    QUADRANT_NORMAL_FLOW,
)
from application.inventory_order_alert.domain.value_objects.recommended_action import (  # noqa: E402
    DEFAULT_RECOMMENDED_ACTIONS,
)
from application.inventory_order_alert.domain.value_objects.summary import (  # noqa: E402
    StockImportInfo,
    SummaryLoadResult,
)
from application.inventory_order_alert.use_cases.export_csv import ExportCsv  # noqa: E402
from application.inventory_order_alert.use_cases.list_page import ListPage, ListPageContext  # noqa: E402

AS_OF = date(2026, 9, 7)

#: 96160-00500 の実データ: 1 年なら低流動品（入荷なし）、5 年なら通常流動品。
ROW_96160_00500 = {
    "cust_code": "100",
    "cust_name": "テスト得意先",
    "cust_chrg_psn_cd": "A01",
    "item_cd": "96160-00500",
    "level1_item_cd": "96160-00500-9209",
    "level1_vend_cd": "9209",
    "level1_vend_name": "仕入先",
    "last_incoming_date": "2025/04/02",
    "last_ship_date": "2026/06/15",
    "post_shipment_count": 1,
    "post_shipment_total_qty": 10,
    "stock_qty": "100",
    "stock_as_of_label": "2026年9月7日時点の在庫",
    "confirmation_status": "未確認",
}


def _stock_info() -> StockImportInfo:
    return StockImportInfo(
        imported_at=datetime(2026, 9, 7, 9, 0),
        row_count=1,
        file_name="sample.csv",
        stock_as_of_date=AS_OF,
        stock_as_of_label="2026年9月7日時点の在庫",
        summary_row_count=1,
    )


def _load_summary() -> SummaryLoadResult:
    return SummaryLoadResult(
        rows=[dict(ROW_96160_00500)],
        stock_info=_stock_info(),
        as_of_date=AS_OF,
        aggregation_error="",
        total_count=1,
        critical_count=0,
        warning_count=0,
    )


def _list_page(**kwargs) -> ListPage:
    return ListPage(ImportStock(lambda text, *, user=None, file_name="", enrich_rows=None: _stock_info()), _load_summary, AppSettings, **kwargs)


def test_a003_list_page_receives_period_in_years_and_exposes_it():
    context = _list_page().execute(query_params={"period": "5"})

    assert context.flow_selection.period.years == 5
    assert context.flow_selection.key == "Y5"
    assert [period.years for period in context.evaluation_periods] == [1, 3, 5]
    assert context.all_rows[0]["flow_quadrant"] == QUADRANT_NORMAL_FLOW


def test_a003_list_page_context_has_no_axis_fields():
    names = {field.name for field in fields(ListPageContext)}

    assert "flow_axis_options" not in names
    assert "flow_period_options" not in names
    assert not any("axis" in name for name in names)


def test_a003_list_page_ignores_legacy_axis_and_month_period():
    context = _list_page().execute(query_params={"axis": "low_flow", "period": "3"})

    assert context.flow_selection.period.years == 3

    context = _list_page().execute(query_params={"axis": "dormant", "period": "6"})

    assert context.flow_selection.period.years == 1


def test_a003_list_page_default_is_one_year_and_rows_carry_status():
    context = _list_page().execute(query_params={})

    assert context.flow_selection.period.years == 1
    row = context.all_rows[0]
    assert row["flow_quadrant"] == QUADRANT_LOW_FLOW_NO_INCOMING
    assert "最終入荷 2025/04/02" in row["flow_status"]
    assert row["recommended_action"] == DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_LOW_FLOW_NO_INCOMING).action
    assert context.counts.low_flow_no_incoming == 1


def test_a003_list_page_uses_injected_recommended_actions_for_rows_and_rules():
    overridden = DEFAULT_RECOMMENDED_ACTIONS.with_action_texts({"low-flow-no-incoming": "上書き文言"})

    context = _list_page(recommended_actions=overridden).execute(query_params={})

    assert context.all_rows[0]["recommended_action"] == "上書き文言"
    assert context.flow_quadrant_rule_rows[0].action == "上書き文言"
    assert context.recommended_actions is overridden


def test_a005_export_csv_uses_selected_evaluation_period():
    import csv
    import io

    result = ExportCsv(_load_summary).execute(query_params={"period": "5"})
    record = next(csv.DictReader(io.StringIO(result.content.decode("utf-8-sig"))))

    assert record["流動区分"] == QUADRANT_NORMAL_FLOW
    assert record["判定期間"] == "5年"
    assert record["判定軸"] == ""


def test_a005_export_csv_defaults_to_one_year():
    import csv
    import io

    result = ExportCsv(_load_summary).execute(query_params={})
    record = next(csv.DictReader(io.StringIO(result.content.decode("utf-8-sig"))))

    assert record["流動区分"] == QUADRANT_LOW_FLOW_NO_INCOMING
    assert record["判定期間"] == "1年"
    assert record["責任部署"] == "調達G・営業G・生産管理"


# --- TC-SFV-A-007: 推奨アクションの上書きが一覧ペイロードに反映される（wiring） ---


@pytest.mark.django_db
def test_a007_wiring_injects_overridden_recommended_actions_into_list_payload(monkeypatch):
    from application.inventory_order_alert.domain.value_objects.list_client_data import build_list_client_payload
    from application.inventory_order_alert.domain.value_objects.list_filter import ListFilterOptions
    from application.inventory_order_alert.interfaces import wiring

    overridden = DEFAULT_RECOMMENDED_ACTIONS.with_action_texts({"low-flow-no-incoming": "上書き文言"})
    monkeypatch.setattr(wiring, "load_recommended_actions", lambda: overridden)

    context = wiring.list_page_usecase().execute(query_params={})
    payload = build_list_client_payload(
        all_rows=context.all_rows,
        filter_options=ListFilterOptions.empty(),
        confirmation_status_choices=context.confirmation_status_choices,
        recommended_actions=context.recommended_actions,
    )

    assert payload["recommendedActions"]["low-flow-no-incoming"]["action"] == "上書き文言"
    assert context.flow_quadrant_rule_rows[0].action == "上書き文言"


@pytest.mark.django_db
def test_a007_wiring_uses_definition_file_loader_by_default():
    from application.inventory_order_alert.interfaces import wiring

    context = wiring.list_page_usecase().execute(query_params={})

    assert context.recommended_actions == wiring.load_recommended_actions()
