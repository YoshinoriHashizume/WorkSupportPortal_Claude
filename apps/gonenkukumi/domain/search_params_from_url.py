from __future__ import annotations

from django.http import QueryDict

from .schemas import GonenKukumiSearchParams, validate_search_params


def search_params_from_url(query: QueryDict | dict[str, object]) -> GonenKukumiSearchParams:
    return validate_search_params(dict(query.items()) if hasattr(query, "items") else dict(query))
