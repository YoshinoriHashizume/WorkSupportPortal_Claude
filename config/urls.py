from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="portal:dashboard", permanent=False)),
    path("", include("applications.identity.urls")),
    path("", include("applications.portal.urls")),
    path("", include("applications.gonenkukumi.urls")),
    path("", include("applications.receipt_comparison.urls")),
    path("", include("applications.inventory_order_alert.urls")),
    path("", include("applications.asset_inventory.urls")),
    path("", include("applications.shipment_trend.urls")),
]
