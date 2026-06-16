from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="portal:dashboard", permanent=False)),
    path("", include("apps.identity.urls")),
    path("", include("apps.portal.urls")),
    path("", include("apps.gonenkukumi.urls")),
    path("", include("apps.receipt_comparison.urls")),
]
