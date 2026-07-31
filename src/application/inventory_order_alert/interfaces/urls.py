from django.urls import path

from . import views

app_name = "inventory_order_alert"

urlpatterns = [
    path("app/production/inventory-order-alert", views.list_page, name="list_page"),
    path("app/production/inventory-order-alert/export.csv", views.export_csv, name="export_csv"),
    path("api/inventory-order-alert/export.csv", views.export_csv, name="api_export_csv"),
    path("api/inventory-order-alert/confirmation", views.api_save_confirmation, name="api_save_confirmation"),
    path(
        "api/inventory-order-alert/confirmation/memos",
        views.api_confirmation_memos,
        name="api_confirmation_memos",
    ),
    path(
        "api/inventory-order-alert/confirmation/reset",
        views.api_reset_confirmations,
        name="api_reset_confirmations",
    ),
    path("api/inventory-order-alert/alert-settings", views.api_save_alert_settings, name="api_save_alert_settings"),
]
