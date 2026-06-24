from __future__ import annotations

from datetime import date

from apps.gonenkukumi.domain.ports import GonenKukumiSearchGateway
from apps.gonenkukumi.domain.schemas import GonenKukumiSearchParams
from apps.gonenkukumi.infrastructure.oracle import client


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
