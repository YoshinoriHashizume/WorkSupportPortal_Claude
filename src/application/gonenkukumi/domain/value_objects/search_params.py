from __future__ import annotations

from collections.abc import Mapping

from .schemas import GonenKukumiSearchParams, validate_search_params


def _mapping_from_query(query: Mapping[str, object] | object) -> dict[str, object]:
    if hasattr(query, "dict"):
        return query.dict()
    if hasattr(query, "items") and not isinstance(query, dict):
        return dict(query.items())
    return dict(query)


def search_params_from_mapping(query: Mapping[str, object] | object) -> GonenKukumiSearchParams:
    return validate_search_params(_mapping_from_query(query))
