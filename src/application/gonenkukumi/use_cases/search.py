from __future__ import annotations

from collections.abc import Mapping

from application.gonenkukumi.domain.repositories.ports import GonenKukumiHistoryRepository, GonenKukumiSearchGateway
from application.gonenkukumi.domain.value_objects.schemas import validate_search_params


class Search:
    def __init__(
        self,
        search_gateway: GonenKukumiSearchGateway,
        history_repository: GonenKukumiHistoryRepository,
    ) -> None:
        self._search_gateway = search_gateway
        self._history_repository = history_repository

    def execute(self, user_id: int, data: Mapping[str, object]) -> dict[str, object]:
        params = validate_search_params(dict(data))
        result = self._search_gateway.search(params)
        self._history_repository.save(user_id, params)
        return result
