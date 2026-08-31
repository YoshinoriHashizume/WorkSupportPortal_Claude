from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from application.gonenkukumi.use_cases.export_excel import ExportExcel
from application.gonenkukumi.use_cases.list_history import ListHistory
from application.gonenkukumi.use_cases.result_page import ResultPage
from application.gonenkukumi.use_cases.search import Search
from application.gonenkukumi.use_cases.search_page import SearchPage
from application.sales.domain.value_objects.errors import OracleQueryError
from application.gonenkukumi.domain.value_objects.result import build_multi_month_result, month_label
from application.gonenkukumi.domain.value_objects.schemas import GonenKukumiSearchParams


class FakeSearchGateway:
    def __init__(self, result: dict[str, object] | None = None) -> None:
        self._result = result or {"yearMonth": "2026-05", "blocks": []}
        self.search_calls: list[GonenKukumiSearchParams] = []

    def search(self, params: GonenKukumiSearchParams) -> dict[str, object]:
        self.search_calls.append(params)
        return {**self._result, "yearMonth": params.year_month}

    def list_customers(self, keyword: str = "") -> list[dict[str, str]]:
        return [{"custCode": "101", "custName": "テスト得意先"}]

    def list_cust_items(self, cust_code: str, keyword: str = "", as_of_date: date | None = None) -> list[dict[str, str]]:
        return [{"custItem": "ITEM-001"}]

    def use_mock(self) -> bool:
        return True


class FakeHistoryRepository:
    def __init__(self) -> None:
        self.saved: list[tuple[int, GonenKukumiSearchParams]] = []

    def save(self, user_id: int, params: GonenKukumiSearchParams) -> None:
        self.saved.append((user_id, params))

    def latest_unique(self, user_id: int, limit: int = 20) -> list[dict[str, object]]:
        return [{"custCode": "101", "custItem": "ITEM-001", "optionChange": "*", "yearMonth": "2026-05", "executedAt": "2026-06-01T00:00:00"}]

    def latest_initial_values(self, user_id: int) -> dict[str, str] | None:
        return {
            "custCode": "101",
            "custItem": "ITEM-001",
            "optionChange": "*",
            "yearMonth": "2026-05",
        }


def test_search_usecase_saves_history():
    gateway = FakeSearchGateway()
    history = FakeHistoryRepository()
    params = GonenKukumiSearchParams(
        cust_code="101",
        cust_item="ITEM-001",
        option_change="*",
        year_month="2026-05",
        as_of_date=date(2026, 6, 1),
    )
    result = Search(gateway, history).execute(1, {
        "custCode": "101",
        "custItem": "ITEM-001",
        "optionChange": "*",
        "yearMonth": "2026/05",
        "asOfDate": "2026/06/01",
    })
    assert result["yearMonth"] == "2026-05"
    assert len(history.saved) == 1
    assert gateway.search_calls[0].cust_code == "101"


def test_search_page_usecase_returns_customers():
    context = SearchPage(FakeSearchGateway(), FakeHistoryRepository()).execute(1)
    assert context.customers[0]["custCode"] == "101"
    assert context.oracle_use_mock is True


def test_result_page_usecase_builds_multi_month_result():
    gateway = FakeSearchGateway({"yearMonth": "2026-05", "blocks": [{"kind": "customer", "meta": {"custCode": "101", "custItem": "X"}, "rows": []}]})
    result = ResultPage(gateway).execute({
        "custCode": "101",
        "custItem": "ITEM-001",
        "optionChange": "*",
        "yearMonth": "2026-05",
        "asOfDate": "2026-06-01",
        "months": "2026-04,2026-05",
    })
    assert len(result["months"]) == 2
    assert len(gateway.search_calls) == 2


def test_list_history_usecase():
    histories = ListHistory(FakeHistoryRepository()).execute(1)
    assert histories[0]["custCode"] == "101"


def test_build_multi_month_result_groups_blocks():
    params = GonenKukumiSearchParams(
        cust_code="101",
        cust_item="ITEM-001",
        option_change="*",
        year_month="2026-05",
        as_of_date=date(2026, 6, 1),
    )

    def fake_search(search_params: GonenKukumiSearchParams) -> dict[str, object]:
        return {
            "yearMonth": search_params.year_month,
            "blocks": [{
                "kind": "customer",
                "meta": {"custCode": "101", "custItem": "ITEM-001"},
                "rows": [{"item": "確定受注", "values": [], "total": 0, "balance": 0}],
            }],
            "activeDays": 30,
            "holidayDays": [],
            "days": list(range(1, 32)),
        }

    result = build_multi_month_result(params, ["2026-05"], fake_search)
    assert result["blocks"][0]["monthPanels"][0]["label"] == month_label("2026-05", "2026-05")


def test_export_excel_usecase_returns_workbook_bytes():
    gateway = FakeSearchGateway({
        "yearMonth": "2026-05",
        "blocks": [],
        "custCode": "101",
        "custItem": "ITEM-001",
        "optionChange": "*",
        "asOfDate": "2026/06/01",
        "internalItemCd": "INT-001",
        "customerName": "テスト",
    })
    content, filename = ExportExcel(gateway).execute({
        "custCode": "101",
        "custItem": "ITEM-001",
        "optionChange": "*",
        "yearMonth": "2026-05",
        "asOfDate": "2026-06-01",
    })
    assert content[:2] == b"PK"
    assert filename.endswith(".xlsx")
