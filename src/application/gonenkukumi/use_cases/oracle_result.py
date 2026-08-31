from __future__ import annotations

from collections.abc import Mapping

from application.gonenkukumi.domain.repositories.ports import GonenKukumiSearchGateway
from application.gonenkukumi.domain.value_objects.schemas import validate_search_params


class OracleResult:
    def __init__(self, search_gateway: GonenKukumiSearchGateway) -> None:
        self._search_gateway = search_gateway

    def execute(self, data: Mapping[str, object]) -> dict[str, object]:
        params = validate_search_params(dict(data))
        return self._search_gateway.search(params)
