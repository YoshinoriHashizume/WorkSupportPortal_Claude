from __future__ import annotations

from application.gonenkukumi.domain.repositories.ports import GonenKukumiSearchGateway


class ListCustomers:
    def __init__(self, search_gateway: GonenKukumiSearchGateway) -> None:
        self._search_gateway = search_gateway

    def execute(self, keyword: str = "") -> list[dict[str, str]]:
        return self._search_gateway.list_customers(keyword)
