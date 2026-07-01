from __future__ import annotations

from applications.gonenkukumi.domain.ports import GonenKukumiSearchGateway


class ListCustomersUsecase:
    def __init__(self, search_gateway: GonenKukumiSearchGateway) -> None:
        self._search_gateway = search_gateway

    def execute(self, keyword: str = "") -> list[dict[str, str]]:
        return self._search_gateway.list_customers(keyword)
