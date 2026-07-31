from __future__ import annotations

from datetime import date

from application.gonenkukumi.domain.repositories.ports import GonenKukumiSearchGateway
from application.gonenkukumi.domain.value_objects.schemas import GonenKukumiSearchParams
from application.gonenkukumi.infrastructure.oracle import client


class OracleGonenKukumiSearchGateway:
    def search(self, params: GonenKukumiSearchParams) -> dict[str, object]:
        return client.run_gonenkukumi_oracle_search(params)

    def list_customers(self, keyword: str = "") -> list[dict[str, str]]:
        return client.list_customers(keyword)

    def list_cust_items(
        self,
        cust_code: str,
        keyword: str = "",
        as_of_date: date | None = None,
    ) -> list[dict[str, str]]:
        return client.list_cust_items(cust_code, keyword, as_of_date)

    def use_mock(self) -> bool:
        return client.use_mock()
