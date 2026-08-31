from __future__ import annotations

from django.contrib.auth.models import Group
from django.utils import timezone

from application.portal.domain.value_objects.constants import (
    ADMIN_GROUP_NAME,
    GENERAL_USER_GROUP_NAME,
    ROLE_GROUP_NAMES,
)
from application.portal.domain.value_objects.database_display import assignable_menu_groups
from application.portal.domain.value_objects.menu_access import normalize_menu_group_key
from application.portal.models import PortalMenuGroupAccess, UserAccessRequest


class DjangoAccessRequestRepository:
    def list_pending_entries(self) -> list[dict[str, object]]:
        requests = UserAccessRequest.objects.filter(status=UserAccessRequest.Status.PENDING).select_related(
            "user", "reviewed_by"
        ).prefetch_related(
            "user__groups",
            "user__portal_menu_group_accesses",
        )
        entries = []
        for access_request in requests:
            group_names = set(access_request.user.groups.values_list("name", flat=True))
            role = ADMIN_GROUP_NAME if ADMIN_GROUP_NAME in group_names else GENERAL_USER_GROUP_NAME
            selected_menu_group_keys = set(
                normalize_menu_group_key(key)
                for key in access_request.user.portal_menu_group_accesses.values_list("group_key", flat=True)
            )
            if access_request.status == UserAccessRequest.Status.PENDING and not selected_menu_group_keys:
                selected_menu_group_keys = {"company"}
            entries.append(
                {
                    "access_request": access_request,
                    "role": role,
                    "selected_menu_group_keys": selected_menu_group_keys,
                }
            )
        return entries

    def list_role_groups(self) -> list[object]:
        for name in ROLE_GROUP_NAMES:
            Group.objects.get_or_create(name=name)
        return list(Group.objects.filter(name__in=ROLE_GROUP_NAMES).order_by("name"))

    def approve(
        self,
        *,
        request_id: str,
        reviewer: object,
        role_name: str,
        menu_group_keys: list[str],
        note: str,
    ) -> None:
        access_request = UserAccessRequest.objects.select_related("user").get(id=request_id)
        access_request.reviewed_at = timezone.now()
        access_request.reviewed_by = reviewer
        access_request.note = note
        role_group_name = ADMIN_GROUP_NAME if role_name == ADMIN_GROUP_NAME else GENERAL_USER_GROUP_NAME
        role_group, _ = Group.objects.get_or_create(name=role_group_name)
        access_request.status = UserAccessRequest.Status.APPROVED
        access_request.user.groups.set([role_group])
        PortalMenuGroupAccess.objects.filter(user=access_request.user).delete()
        if role_group_name != ADMIN_GROUP_NAME:
            valid_menu_group_keys = {group.key for group in assignable_menu_groups()}
            PortalMenuGroupAccess.objects.bulk_create(
                [
                    PortalMenuGroupAccess(user=access_request.user, group_key=group_key)
                    for group_key in menu_group_keys
                    if group_key in valid_menu_group_keys
                ],
                ignore_conflicts=True,
            )
        access_request.save()

    def reject(self, *, request_id: str, reviewer: object, note: str) -> None:
        access_request = UserAccessRequest.objects.select_related("user").get(id=request_id)
        access_request.reviewed_at = timezone.now()
        access_request.reviewed_by = reviewer
        access_request.note = note
        access_request.status = UserAccessRequest.Status.REJECTED
        access_request.user.groups.clear()
        PortalMenuGroupAccess.objects.filter(user=access_request.user).delete()
        access_request.save()
