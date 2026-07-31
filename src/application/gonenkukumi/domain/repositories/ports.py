from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Protocol

from ..value_objects.schemas import GonenKukumiSearchParams


class GonenKukumiSearchGateway(Protocol):
    def search(self, params: GonenKukumiSearchParams) -> dict[str, object]:
        ...

    def list_customers(self, keyword: str = "") -> list[dict[str, str]]:
        ...

    def list_cust_items(
        self,
        cust_code: str,
        keyword: str = "",
        as_of_date: date | None = None,
    ) -> list[dict[str, str]]:
        ...

    def use_mock(self) -> bool:
        ...


class GonenKukumiHistoryRepository(Protocol):
    def save(self, user_id: int, params: GonenKukumiSearchParams) -> None:
        ...

    def latest_unique(self, user_id: int, limit: int = 20) -> list[dict[str, object]]:
        ...

    def latest_initial_values(self, user_id: int) -> Mapping[str, str] | None:
        ...
