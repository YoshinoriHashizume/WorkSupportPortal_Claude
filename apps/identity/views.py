from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.portal.models import UserAccessRequest

from .desknet import DesknetAuthError, DesknetUserInfo, authenticate_desknet_user


def safe_next_url(request: HttpRequest) -> str:
    next_url = request.POST.get("next") or request.GET.get("next") or settings.LOGIN_REDIRECT_URL
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return next_url
    return settings.LOGIN_REDIRECT_URL


def split_desknet_name(name: str) -> tuple[str, str]:
    parts = (name or "").replace("\u3000", " ").split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    return "", name.strip()


def upsert_django_user_from_desknet(user_info: DesknetUserInfo):
    User = get_user_model()
    user, created = User.objects.get_or_create(username=user_info.employee_id)
    last_name, first_name = split_desknet_name(user_info.name)
    user.last_name = last_name
    user.first_name = first_name
    user.email = ""
    user.is_active = True
    user.set_unusable_password()
    user.save()
    if created:
        UserAccessRequest.objects.get_or_create(user=user)
    return user


@require_GET
def login_page(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("portal:dashboard")
    return render(
        request,
        "identity/login.html",
        {
            "auth_provider": settings.AUTH_PROVIDER,
            "next": safe_next_url(request),
        },
    )


@require_POST
def desknet_login(request: HttpRequest) -> HttpResponse:
    employee_id = (request.POST.get("employee_id") or "").strip()
    password = request.POST.get("password") or ""
    if not employee_id or not password:
        messages.error(request, "社員番号とパスワードを入力してください。")
        return redirect("identity:login")

    try:
        user_info = authenticate_desknet_user(
            settings.DESKNETS_LOGIN_URL,
            employee_id,
            password,
            timeout=settings.DESKNETS_TIMEOUT_SECONDS,
        )
    except DesknetAuthError as exc:
        messages.error(request, str(exc))
        return redirect("identity:login")

    user = upsert_django_user_from_desknet(user_info)
    request.session["desknet_user_id"] = user_info.user_id
    request.session["desknet_default_group_id"] = user_info.default_group_id
    login(request, user)
    access_request = getattr(user, "access_request", None)
    if access_request and access_request.status != UserAccessRequest.Status.APPROVED:
        return redirect("portal:access_status")
    return redirect(safe_next_url(request))


@require_http_methods(["GET", "POST"])
def logout_page(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("identity:login")


@require_GET
def microsoft_login(request: HttpRequest) -> HttpResponse:
    messages.info(request, "Microsoft Entra ID 接続は接続フェーズで有効化します。")
    return redirect("identity:login")


@require_GET
def microsoft_callback(request: HttpRequest) -> HttpResponse:
    messages.info(request, "Microsoft Entra ID callback endpoint is reserved for Authlib integration.")
    return redirect("identity:login")
