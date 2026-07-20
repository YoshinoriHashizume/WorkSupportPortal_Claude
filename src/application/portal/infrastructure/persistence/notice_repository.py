from __future__ import annotations

from application.portal.models import PortalNotice


class DjangoNoticeRepository:
    def list_published(self, *, limit: int) -> list[object]:
        return list(PortalNotice.objects.filter(is_published=True).order_by("-created_at")[:limit])

    def list_all(self) -> list[object]:
        return list(PortalNotice.objects.order_by("-created_at"))

    def delete(self, notice_id: str) -> None:
        PortalNotice.objects.filter(id=notice_id).delete()

    def create(self, *, title: str, body: str, is_published: bool, created_by: object) -> None:
        PortalNotice.objects.create(
            title=title,
            body=body,
            is_published=is_published,
            created_by=created_by,
        )

    def update(self, notice_id: str, *, title: str, body: str, is_published: bool) -> None:
        notice = PortalNotice.objects.get(id=notice_id)
        notice.title = title
        notice.body = body
        notice.is_published = is_published
        notice.save(update_fields=["title", "body", "is_published", "updated_at"])
