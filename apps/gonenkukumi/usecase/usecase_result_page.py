from __future__ import annotations

from collections.abc import Mapping

from apps.gonenkukumi.domain.ports import GonenKukumiSearchGateway
from apps.gonenkukumi.domain.result import build_multi_month_result, display_months_from_query
from apps.gonenkukumi.domain.search_params import _mapping_from_query, search_params_from_mapping


class ResultPageUsecase:
    def __init__(self, search_gateway: GonenKukumiSearchGateway) -> None:
        self._search_gateway = search_gateway

    def execute(self, query: Mapping[str, object] | object) -> dict[str, object]:
        query_map = _mapping_from_query(query)
        params = search_params_from_mapping(query_map)
        raw_months = str(query_map.get("months") or "")
        return build_multi_month_result(
            params,
            display_months_from_query(params, raw_months),
            self._search_gateway.search,
        )
