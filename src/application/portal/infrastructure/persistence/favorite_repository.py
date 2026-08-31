from __future__ import annotations

from collections.abc import Iterable

from application.portal.domain.value_objects.menu import MENU_BY_KEY
from application.portal.models import UserFavoriteMenu


class DjangoFavoriteRepository:
    def favorite_keys_for_user(self, user: object) -> list[str]:
        if not getattr(user, "is_authenticated", False):
            return []
        return list(
            UserFavoriteMenu.objects.filter(user=user, menu_key__in=MENU_BY_KEY.keys())
            .order_by("sort_order", "created_at")
            .values_list("menu_key", flat=True)
        )

    def next_sort_order(self, user: object) -> int:
        latest = UserFavoriteMenu.objects.filter(user=user).order_by("-sort_order").first()
        return 0 if latest is None else latest.sort_order + 1

    def get_or_create_favorite(self, user: object, menu_key: str, sort_order: int) -> None:
        UserFavoriteMenu.objects.get_or_create(
            user=user,
            menu_key=menu_key,
            defaults={"sort_order": sort_order},
        )

    def delete_favorite(self, user: object, menu_key: str) -> None:
        UserFavoriteMenu.objects.filter(user=user, menu_key=menu_key).delete()

    def list_favorites(self, user: object) -> dict[str, object]:
        return {
            favorite.menu_key: favorite
            for favorite in UserFavoriteMenu.objects.filter(user=user)
        }

    def reorder_favorites(self, user: object, menu_keys: Iterable[str]) -> None:
        favorites = self.list_favorites(user)
        for index, key in enumerate(menu_keys):
            favorite = favorites.get(key)
            if favorite is None:
                continue
            favorite.sort_order = index
            favorite.save(update_fields=["sort_order"])
