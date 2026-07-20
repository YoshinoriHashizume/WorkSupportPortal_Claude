from __future__ import annotations

from application.portal.domain.value_objects.menu_access import normalize_menu_group_keys
from application.portal.models import PortalMenuGroupAccess


class DjangoMenuAccessRepository:
    def user_group_names(self, user: object) -> set[str]:
        if not getattr(user, "is_authenticated", False):
            return set()
        return set(user.groups.values_list("name", flat=True))

    def accessible_menu_group_keys(self, user: object) -> set[str]:
        if not getattr(user, "is_authenticated", False):
            return set()
        raw_keys = PortalMenuGroupAccess.objects.filter(user=user).values_list("group_key", flat=True)
        return normalize_menu_group_keys(set(raw_keys))
