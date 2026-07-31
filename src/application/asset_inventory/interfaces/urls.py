from django.urls import path

from . import views

app_name = "asset_inventory"

urlpatterns = [
    path("app/general-affairs/asset-inventory", views.list_page, name="list_page"),
    path("api/asset-inventory/export.csv", views.export_csv, name="export_csv"),
    path("api/asset-inventory/attachment", views.attachment_proxy, name="attachment"),
]
