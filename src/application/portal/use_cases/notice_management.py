from __future__ import annotations

from application.portal.domain.repositories.ports import NoticeRepository


class NoticeManagement:
    def __init__(self, repository: NoticeRepository) -> None:
        self._repository = repository

    def page_context(self) -> dict[str, object]:
        return {"notices": self._repository.list_all()}

    def process(
        self,
        *,
        actor: object,
        action: str | None,
        notice_id: str | None,
        title: str,
        body: str,
        is_published: bool,
    ) -> None:
        if action == "delete" and notice_id:
            self._repository.delete(notice_id)
            return

        if not (title and body):
            return

        if notice_id:
            self._repository.update(notice_id, title=title, body=body, is_published=is_published)
            return

        self._repository.create(title=title, body=body, is_published=is_published, created_by=actor)
