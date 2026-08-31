from django.urls import path

from . import views

app_name = "receipt_comparison"

urlpatterns = [
    path("app/production/receipt-comparison", views.comparison_page, name="comparison"),
    path("app/production/receipt-comparison/export", views.export_csv, name="export_csv"),
    path("app/production/receipt-comparison/settings", views.settings_page, name="settings"),
    path(
        "app/production/receipt-comparison/<slug:comparison_slug>",
        views.legacy_comparison_redirect,
        name="legacy_comparison",
    ),
    path(
        "app/production/receipt-comparison/<slug:comparison_slug>/export",
        views.legacy_export_redirect,
        name="legacy_export",
    ),
    path(
        "app/production/receipt-comparison/<slug:comparison_slug>/settings",
        views.legacy_settings_redirect,
        name="legacy_settings",
    ),
]
