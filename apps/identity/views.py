from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.identity.composition import desknet_login_usecase, dev_login_usecase, login_page_usecase
from apps.identity.domain.errors import DesknetAuthError


def _safe_next_url(request: HttpRequest) -> str:
    next_url = request.POST.get("next") or request.GET.get("next") or settings.LOGIN_REDIRECT_URL
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return next_url
    return settings.LOGIN_REDIRECT_URL


@ensure_csrf_cookie
@require_GET
def login_page(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("portal:dashboard")
    context = login_page_usecase().execute(settings.AUTH_PROVIDER, _safe_next_url(request))
    return render(
        request,
        "identity/login.html",
        {
            "auth_provider": context.auth_provider,
            "show_dev_login": context.show_dev_login,
            "next": context.next_url,
        },
    )


@require_POST
def desknet_login(request: HttpRequest) -> HttpResponse:
    employee_id = (request.POST.get("employee_id") or "").strip()
    password = request.POST.get("password") or ""
    try:
        result = desknet_login_usecase().execute(
            settings.DESKNETS_LOGIN_URL,
            employee_id,
            password,
            settings.DESKNETS_TIMEOUT_SECONDS,
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("identity:login")
    except DesknetAuthError as exc:
        messages.error(request, str(exc))
        return redirect("identity:login")

    request.session["desknet_user_id"] = result.user_info.user_id
    request.session["desknet_default_group_id"] = result.user_info.default_group_id
    request.session["desknet_access_key"] = result.user_info.access_key
    login(request, result.user)
    if result.requires_access_approval:
        return redirect("portal:access_status")
    return redirect(_safe_next_url(request))


@csrf_exempt
@require_POST
def dev_login(request: HttpRequest) -> HttpResponse:
    try:
        user = dev_login_usecase().execute(
            (request.POST.get("employee_id") or "").strip(),
            request.POST.get("password") or "",
        )
    except PermissionError:
        return HttpResponse("Not Found", status=404)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("identity:login")

    if user is None:
        messages.error(request, "社員番号またはパスワードが正しくありません。")
        return redirect("identity:login")

    login(request, user)
    return redirect(_safe_next_url(request))


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
