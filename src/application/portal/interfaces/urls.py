from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    path("app", views.dashboard, name="dashboard"),
    path("dashboard", views.dashboard, name="dashboard_alias"),
    path("app/access-status", views.access_status, name="access_status"),
    path("app/management/notices", views.notice_management, name="notice_management"),
    path("app/management/access-requests", views.access_requests, name="access_requests"),
    path("app/management/users", views.user_management, name="user_management"),
    path("app/management/<str:slug>", views.management_page, name="management_page"),
    path("api/favorite-menus", views.favorite_menus, name="favorite_menus"),
    path("api/favorite-menus/order", views.favorite_menu_order, name="favorite_menu_order"),
    path("api/favorite-menus/<str:menu_key>", views.favorite_menu_detail, name="favorite_menu_detail"),
]
