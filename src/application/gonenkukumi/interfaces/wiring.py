from __future__ import annotations

from application.gonenkukumi.use_cases.export_excel import ExportExcel
from application.gonenkukumi.use_cases.list_cust_items import ListCustItems
from application.gonenkukumi.use_cases.list_customers import ListCustomers
from application.gonenkukumi.use_cases.list_history import ListHistory
from application.gonenkukumi.use_cases.oracle_result import OracleResult
from application.gonenkukumi.use_cases.result_page import ResultPage
from application.gonenkukumi.use_cases.search import Search
from application.gonenkukumi.use_cases.search_page import SearchPage
from application.gonenkukumi.domain.repositories.ports import GonenKukumiHistoryRepository, GonenKukumiSearchGateway
from application.gonenkukumi.infrastructure.oracle.search_gateway import OracleGonenKukumiSearchGateway
from application.gonenkukumi.infrastructure.persistence.history_repository import DjangoGonenKukumiHistoryRepository


def get_search_gateway() -> GonenKukumiSearchGateway:
    return OracleGonenKukumiSearchGateway()


def get_history_repository() -> GonenKukumiHistoryRepository:
    return DjangoGonenKukumiHistoryRepository()


def search_page_usecase() -> SearchPage:
    return SearchPage(get_search_gateway(), get_history_repository())


def result_page_usecase() -> ResultPage:
    return ResultPage(get_search_gateway())


def search_usecase() -> Search:
    return Search(get_search_gateway(), get_history_repository())


def oracle_result_usecase() -> OracleResult:
    return OracleResult(get_search_gateway())


def list_customers_usecase() -> ListCustomers:
    return ListCustomers(get_search_gateway())


def list_cust_items_usecase() -> ListCustItems:
    return ListCustItems(get_search_gateway())


def list_history_usecase() -> ListHistory:
    return ListHistory(get_history_repository())


def export_excel_usecase() -> ExportExcel:
    return ExportExcel(get_search_gateway())
