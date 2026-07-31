from django.urls import path

from . import views

app_name = "shipment_trend"

urlpatterns = [
    path("app/sales/shipment-trend", views.list_page, name="list_page"),
    path("app/sales/shipment-trend/export.csv", views.export_csv, name="export_csv"),
    path("api/shipment-trend/chart", views.api_chart_data, name="api_chart_data"),
    path("api/shipment-trend/alert-settings", views.api_save_alert_settings, name="api_save_alert_settings"),
    path("api/shipment-trend/baseline-year", views.api_baseline_year, name="api_baseline_year"),
    path("api/shipment-trend/export.csv", views.export_csv, name="api_export_csv"),
]
