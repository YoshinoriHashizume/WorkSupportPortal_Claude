from __future__ import annotations

from application.portal.use_cases.access_requests import AccessRequests
from application.portal.use_cases.bootstrap_local_dev import BootstrapLocalDev
from application.portal.use_cases.bootstrap_production_admin import BootstrapProductionAdmin
from application.portal.use_cases.dashboard import Dashboard
from application.portal.use_cases.database_page import DatabasePage
from application.portal.use_cases.favorites import Favorites
from application.portal.use_cases.menu_access import MenuAccess
from application.portal.use_cases.notice_management import NoticeManagement
from application.portal.use_cases.user_management import UserManagement
from application.portal.domain.repositories.ports import (
    AccessRequestRepository,
    DatabaseBrowser,
    FavoriteRepository,
    MenuAccessRepository,
    NoticeRepository,
    UserManagementRepository,
)
from application.portal.infrastructure.persistence.access_request_repository import DjangoAccessRequestRepository
from application.portal.infrastructure.persistence.database_browser import DjangoDatabaseBrowser
from application.portal.infrastructure.persistence.favorite_repository import DjangoFavoriteRepository
from application.portal.infrastructure.persistence.menu_access_repository import DjangoMenuAccessRepository
from application.portal.infrastructure.persistence.notice_repository import DjangoNoticeRepository
from application.portal.infrastructure.persistence.user_bootstrap_repository import (
    run_bootstrap_local_dev,
    run_bootstrap_production_admin,
)
from application.portal.infrastructure.persistence.user_management_repository import DjangoUserManagementRepository


def get_menu_access_repository() -> MenuAccessRepository:
    return DjangoMenuAccessRepository()


def get_favorite_repository() -> FavoriteRepository:
    return DjangoFavoriteRepository()


def get_notice_repository() -> NoticeRepository:
    return DjangoNoticeRepository()


def get_access_request_repository() -> AccessRequestRepository:
    return DjangoAccessRequestRepository()


def get_user_management_repository() -> UserManagementRepository:
    return DjangoUserManagementRepository()


def get_database_browser() -> DatabaseBrowser:
    return DjangoDatabaseBrowser()


def menu_access_usecase() -> MenuAccess:
    return MenuAccess(get_menu_access_repository())


def favorites_usecase() -> Favorites:
    return Favorites(get_favorite_repository(), menu_access_usecase())


def dashboard_usecase() -> Dashboard:
    def inventory_order_alert_banner():
        from application.inventory_order_alert.interfaces.wiring import portal_dashboard_usecase

        return portal_dashboard_usecase().execute()

    return Dashboard(
        get_notice_repository(),
        favorites_usecase(),
        menu_access_usecase(),
        inventory_order_alert_banner=inventory_order_alert_banner,
    )


def access_requests_usecase() -> AccessRequests:
    return AccessRequests(get_access_request_repository())


def user_management_usecase() -> UserManagement:
    return UserManagement(get_user_management_repository())


def notice_management_usecase() -> NoticeManagement:
    return NoticeManagement(get_notice_repository())


def database_page_usecase() -> DatabasePage:
    return DatabasePage(get_database_browser())


def bootstrap_local_dev_usecase() -> BootstrapLocalDev:
    return BootstrapLocalDev(run_bootstrap_local_dev)


def bootstrap_production_admin_usecase() -> BootstrapProductionAdmin:
    return BootstrapProductionAdmin(run_bootstrap_production_admin)
