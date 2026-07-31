from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from application.gonenkukumi.domain.value_objects.errors import OracleNotConfiguredError, OracleQueryError
from application.gonenkukumi.domain.repositories.ports import GonenKukumiHistoryRepository, GonenKukumiSearchGateway


@dataclass(frozen=True)
class SearchPageContext:
    initial: Mapping[str, str]
    customers: list[dict[str, str]]
    customer_load_error: str
    oracle_use_mock: bool


class SearchPage:
    def __init__(
        self,
        search_gateway: GonenKukumiSearchGateway,
        history_repository: GonenKukumiHistoryRepository,
    ) -> None:
        self._search_gateway = search_gateway
        self._history_repository = history_repository

    def execute(self, user_id: int) -> SearchPageContext:
        today = date.today()
        latest = self._history_repository.latest_initial_values(user_id)
        initial = {
            "custCode": latest.get("custCode", "") if latest else "",
            "custItem": latest.get("custItem", "") if latest else "",
            "optionChange": latest.get("optionChange", "*") if latest else "*",
            "yearMonth": latest.get("yearMonth", f"{today.year:04d}-{today.month:02d}") if latest else f"{today.year:04d}-{today.month:02d}",
        }
        customers: list[dict[str, str]] = []
        customer_load_error = ""
        try:
            customers = self._search_gateway.list_customers()
        except OracleNotConfiguredError as exc:
            customer_load_error = str(exc)
        except OracleQueryError as exc:
            customer_load_error = str(exc)
        return SearchPageContext(
            initial=initial,
            customers=customers,
            customer_load_error=customer_load_error,
            oracle_use_mock=self._search_gateway.use_mock(),
        )
