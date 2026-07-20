from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="portal:dashboard", permanent=False)),
    path("", include("application.identity.interfaces.urls")),
    path("", include("application.portal.interfaces.urls")),
    path("", include("application.gonenkukumi.interfaces.urls")),
    path("", include("application.receipt_comparison.interfaces.urls")),
    path("", include("application.inventory_order_alert.interfaces.urls")),
    path("", include("application.asset_inventory.interfaces.urls")),
    path("", include("application.shipment_trend.interfaces.urls")),
]
