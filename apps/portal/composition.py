from __future__ import annotations

from apps.portal.usecase.usecase_bootstrap_local_dev import BootstrapLocalDevUsecase
from apps.portal.usecase.usecase_bootstrap_production_admin import BootstrapProductionAdminUsecase
from apps.portal.usecase.usecase_favorites import FavoritesUsecase
from apps.portal.usecase.usecase_menu_access import MenuAccessUsecase
from apps.portal.domain.ports import FavoriteRepository, MenuAccessRepository
from apps.portal.infrastructure.persistence.favorite_repository import DjangoFavoriteRepository
from apps.portal.infrastructure.persistence.menu_access_repository import DjangoMenuAccessRepository
from apps.portal.infrastructure.persistence.user_bootstrap_repository import (
    run_bootstrap_local_dev,
    run_bootstrap_production_admin,
)


def get_menu_access_repository() -> MenuAccessRepository:
    return DjangoMenuAccessRepository()


def get_favorite_repository() -> FavoriteRepository:
    return DjangoFavoriteRepository()


def menu_access_usecase() -> MenuAccessUsecase:
    return MenuAccessUsecase(get_menu_access_repository())


def favorites_usecase() -> FavoritesUsecase:
    return FavoritesUsecase(get_favorite_repository(), menu_access_usecase())


def bootstrap_local_dev_usecase() -> BootstrapLocalDevUsecase:
    return BootstrapLocalDevUsecase(run_bootstrap_local_dev)


def bootstrap_production_admin_usecase() -> BootstrapProductionAdminUsecase:
    return BootstrapProductionAdminUsecase(run_bootstrap_production_admin)
