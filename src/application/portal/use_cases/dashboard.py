from __future__ import annotations

from collections.abc import Callable

from application.portal.domain.repositories.ports import NoticeRepository
from application.portal.use_cases.favorites import Favorites
from application.portal.use_cases.menu_access import MenuAccess


class Dashboard:
    def __init__(
        self,
        notice_repository: NoticeRepository,
        favorites: Favorites,
        menu_access: MenuAccess,
        *,
        inventory_order_alert_banner: Callable[[], object] | None = None,
    ) -> None:
        self._notices = notice_repository
        self._favorites = favorites
        self._access = menu_access
        self._inventory_order_alert_banner = inventory_order_alert_banner

    def execute(self, user: object) -> dict[str, object]:
        banner = None
        if self._inventory_order_alert_banner is not None and self._access.can_access_menu_item(
            user, "inventory-order-alert"
        ):
            banner = self._inventory_order_alert_banner()
        return {
            "favorite_items": self._favorites.favorite_items_for_user(user),
            "notices": self._notices.list_published(limit=10),
            "inventory_order_alert_banner": banner,
        }
