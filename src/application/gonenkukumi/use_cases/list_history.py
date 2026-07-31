from __future__ import annotations

from application.gonenkukumi.domain.repositories.ports import GonenKukumiHistoryRepository


class ListHistory:
    def __init__(self, history_repository: GonenKukumiHistoryRepository) -> None:
        self._history_repository = history_repository

    def execute(self, user_id: int) -> list[dict[str, object]]:
        return self._history_repository.latest_unique(user_id)
