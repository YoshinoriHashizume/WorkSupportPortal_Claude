from __future__ import annotations

from apps.gonenkukumi.usecase.usecase_export_excel import ExportExcelUsecase
from apps.gonenkukumi.usecase.usecase_list_cust_items import ListCustItemsUsecase
from apps.gonenkukumi.usecase.usecase_list_customers import ListCustomersUsecase
from apps.gonenkukumi.usecase.usecase_list_history import ListHistoryUsecase
from apps.gonenkukumi.usecase.usecase_oracle_result import OracleResultUsecase
from apps.gonenkukumi.usecase.usecase_result_page import ResultPageUsecase
from apps.gonenkukumi.usecase.usecase_search import SearchUsecase
from apps.gonenkukumi.usecase.usecase_search_page import SearchPageUsecase
from apps.gonenkukumi.domain.ports import GonenKukumiHistoryRepository, GonenKukumiSearchGateway
from apps.gonenkukumi.infrastructure.oracle.search_gateway import OracleGonenKukumiSearchGateway
from apps.gonenkukumi.infrastructure.persistence.history_repository import DjangoGonenKukumiHistoryRepository


def get_search_gateway() -> GonenKukumiSearchGateway:
    return OracleGonenKukumiSearchGateway()


def get_history_repository() -> GonenKukumiHistoryRepository:
    return DjangoGonenKukumiHistoryRepository()


def search_page_usecase() -> SearchPageUsecase:
    return SearchPageUsecase(get_search_gateway(), get_history_repository())


def result_page_usecase() -> ResultPageUsecase:
    return ResultPageUsecase(get_search_gateway())


def search_usecase() -> SearchUsecase:
    return SearchUsecase(get_search_gateway(), get_history_repository())


def oracle_result_usecase() -> OracleResultUsecase:
    return OracleResultUsecase(get_search_gateway())


def list_customers_usecase() -> ListCustomersUsecase:
    return ListCustomersUsecase(get_search_gateway())


def list_cust_items_usecase() -> ListCustItemsUsecase:
    return ListCustItemsUsecase(get_search_gateway())


def list_history_usecase() -> ListHistoryUsecase:
    return ListHistoryUsecase(get_history_repository())


def export_excel_usecase() -> ExportExcelUsecase:
    return ExportExcelUsecase(get_search_gateway())
