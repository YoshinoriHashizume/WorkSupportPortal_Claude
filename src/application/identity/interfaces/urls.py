from django.urls import path

from . import views

app_name = "identity"

urlpatterns = [
    path("login", views.login_page, name="login"),
    path("logout", views.logout_page, name="logout"),
    path("auth/desknet-login", views.desknet_login, name="desknet_login"),
    path("auth/dev-login", views.dev_login, name="dev_login"),
    path("auth/microsoft", views.microsoft_login, name="microsoft_login"),
    path("api/auth/callback/microsoft-entra-id", views.microsoft_callback, name="microsoft_callback"),
]
