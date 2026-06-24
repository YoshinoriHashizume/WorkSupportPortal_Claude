from __future__ import annotations

from apps.portal.models import PortalMenuGroupAccess


class DjangoMenuAccessRepository:
    def user_group_names(self, user: object) -> set[str]:
        if not getattr(user, "is_authenticated", False):
            return set()
        return set(user.groups.values_list("name", flat=True))

    def accessible_menu_group_keys(self, user: object) -> set[str]:
        if not getattr(user, "is_authenticated", False):
            return set()
        return set(PortalMenuGroupAccess.objects.filter(user=user).values_list("group_key", flat=True))
