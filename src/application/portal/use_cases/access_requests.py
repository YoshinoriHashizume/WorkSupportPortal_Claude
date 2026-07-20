from __future__ import annotations

from application.portal.domain.repositories.ports import AccessRequestRepository
from application.portal.domain.value_objects.constants import ADMIN_GROUP_NAME, GENERAL_USER_GROUP_NAME
from application.portal.domain.value_objects.database_display import menu_group_choices_in_order


class AccessRequests:
    def __init__(self, repository: AccessRequestRepository) -> None:
        self._repository = repository

    def page_context(self) -> dict[str, object]:
        return {
            "access_request_entries": self._repository.list_pending_entries(),
            "role_groups": self._repository.list_role_groups(),
            "menu_group_choices": menu_group_choices_in_order(),
            "admin_group_name": ADMIN_GROUP_NAME,
        }

    def process(
        self,
        *,
        reviewer: object,
        request_id: str,
        action: str,
        role: str,
        menu_group_keys: list[str],
        note: str,
    ) -> None:
        if action == "approve":
            self._repository.approve(
                request_id=request_id,
                reviewer=reviewer,
                role_name=role or GENERAL_USER_GROUP_NAME,
                menu_group_keys=menu_group_keys,
                note=note,
            )
            return
        if action == "reject":
            self._repository.reject(request_id=request_id, reviewer=reviewer, note=note)
