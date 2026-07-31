from __future__ import annotations

import pytest

from application.portal.use_cases.favorites import Favorites
from application.portal.use_cases.menu_access import MenuAccess
from application.portal.domain.value_objects.menu_access import can_access_menu_item, receipt_comparison_menu_key
from application.portal.infrastructure.persistence.favorite_repository import DjangoFavoriteRepository
from application.portal.infrastructure.persistence.menu_access_repository import DjangoMenuAccessRepository


class FakeMenuAccessRepository:
    def __init__(self, groups: set[str] | None = None, role_names: set[str] | None = None) -> None:
        self._groups = groups or set()
        self._role_names = role_names or set()

    def user_group_names(self, user: object) -> set[str]:
        return self._role_names

    def accessible_menu_group_keys(self, user: object) -> set[str]:
        return self._groups


def test_receipt_comparison_menu_key_maps_slug():
    assert receipt_comparison_menu_key("finished-product") == "receipt-comparison-finished-product"
    assert receipt_comparison_menu_key("supplied-parts") == "receipt-comparison-supplied-parts"


def test_can_access_menu_item_allows_production_menu_when_group_granted():
    allowed = can_access_menu_item(
        is_admin=False,
        accessible_group_keys={"production"},
        menu_key="five-year-nine",
    )
    denied = can_access_menu_item(
        is_admin=False,
        accessible_group_keys=set(),
        menu_key="five-year-nine",
    )
    assert allowed is True
    assert denied is False


def test_menu_access_usecase_detects_admin_role():
    usecase = MenuAccess(FakeMenuAccessRepository(role_names={"管理者"}))

    class User:
        is_superuser = False
        is_authenticated = True

    assert usecase.is_portal_admin(User()) is True


def test_favorites_usecase_skips_inaccessible_items():
    menu_access = MenuAccess(FakeMenuAccessRepository(groups={"production"}))
    usecase = Favorites(DjangoFavoriteRepository(), menu_access)

    class User:
        is_authenticated = False

    assert usecase.favorite_items_for_user(User()) == []
