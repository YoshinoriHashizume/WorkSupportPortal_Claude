from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from application.portal.domain.value_objects.menu import MENU_BY_KEY, MENU_ITEMS
from application.portal.interfaces.favorites import (
    can_access_menu_item,
    page_favorite_toggle_context,
)
from application.portal.interfaces.wiring import (
    access_requests_usecase,
    dashboard_usecase,
    database_page_usecase,
    favorites_usecase,
    notice_management_usecase,
    user_management_usecase,
)


def delete_portal_user(*, actor: object, target_user: object) -> bool:
    return user_management_usecase().delete_user(actor=actor, target_user=target_user)


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    context = dashboard_usecase().execute(request.user)
    return render(
        request,
        "portal/dashboard.html",
        {
            "menu_items": MENU_ITEMS,
            **context,
        },
    )


@login_required
def access_status(request: HttpRequest) -> HttpResponse:
    access_request = getattr(request.user, "access_request", None)
    return render(request, "portal/access_status.html", {"access_request": access_request})


@login_required
@require_http_methods(["GET", "POST"])
def access_requests(request: HttpRequest) -> HttpResponse:
    usecase = access_requests_usecase()
    if request.method == "POST":
        usecase.process(
            reviewer=request.user,
            request_id=str(request.POST.get("request_id") or ""),
            action=str(request.POST.get("action") or ""),
            role=str(request.POST.get("role") or ""),
            menu_group_keys=request.POST.getlist("menu_groups"),
            note=(request.POST.get("note") or "").strip(),
        )
        return redirect("portal:access_requests")

    return render(
        request,
        "portal/access_requests.html",
        {
            **usecase.page_context(),
            **page_favorite_toggle_context(request.user, "access-requests"),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def user_management(request: HttpRequest) -> HttpResponse:
    usecase = user_management_usecase()
    if request.method == "POST":
        usecase.process(
            actor=request.user,
            user_id=str(request.POST.get("user_id") or ""),
            action=str(request.POST.get("action") or "save"),
            last_name=(request.POST.get("last_name") or "").strip(),
            first_name=(request.POST.get("first_name") or "").strip(),
            email=(request.POST.get("email") or "").strip(),
            role=str(request.POST.get("role") or ""),
            menu_group_keys=request.POST.getlist("menu_groups"),
        )
        return redirect("portal:user_management")

    sort_key = (request.GET.get("sort") or "username").strip()
    sort_direction = (request.GET.get("dir") or "asc").strip().lower()
    return render(
        request,
        "portal/user_management.html",
        {
            **usecase.page_context(sort_key=sort_key, sort_direction=sort_direction),
            **page_favorite_toggle_context(request.user, "user-management"),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def notice_management(request: HttpRequest) -> HttpResponse:
    usecase = notice_management_usecase()
    if request.method == "POST":
        usecase.process(
            actor=request.user,
            action=request.POST.get("action"),
            notice_id=request.POST.get("notice_id"),
            title=(request.POST.get("title") or "").strip(),
            body=(request.POST.get("body") or "").strip(),
            is_published=request.POST.get("is_published") == "on",
        )
        return redirect("portal:notice_management")

    return render(
        request,
        "portal/notices.html",
        {
            **usecase.page_context(),
            **page_favorite_toggle_context(request.user, "notices"),
        },
    )


@login_required
def management_page(request: HttpRequest, slug: str) -> HttpResponse:
    pages = {
        "database": "データベース",
    }
    title = pages.get(slug)
    if title is None:
        return render(request, "portal/placeholder.html", {"title": "メニューが見つかりません"}, status=404)
    if slug == "database":
        context = database_page_usecase().execute(
            selected_table=(request.GET.get("table") or "").strip(),
            sort_column=(request.GET.get("sort") or "").strip(),
            sort_direction=(request.GET.get("dir") or "asc").strip().lower(),
        )
        return render(
            request,
            "portal/database.html",
            {
                **context,
                **page_favorite_toggle_context(request.user, "database"),
            },
        )
    return render(request, "portal/placeholder.html", {"title": title})


@login_required
@require_http_methods(["POST"])
def favorite_menus(request: HttpRequest) -> JsonResponse:
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "JSON の形式が不正です。"}, status=400)

    menu_key = str(payload.get("menuKey") or "").strip()
    item = MENU_BY_KEY.get(menu_key)
    if item is None:
        return JsonResponse({"success": False, "error": "メニューが見つかりません。"}, status=404)
    if not item.href:
        return JsonResponse({"success": False, "error": "このメニューはお気に入り登録できません。"}, status=400)
    if not can_access_menu_item(request.user, menu_key):
        return JsonResponse({"success": False, "error": "このメニューをお気に入り登録する権限がありません。"}, status=403)

    favorites_usecase().add_favorite(request.user, menu_key)
    return JsonResponse({"success": True})


@login_required
@require_http_methods(["DELETE"])
def favorite_menu_detail(request: HttpRequest, menu_key: str) -> JsonResponse:
    usecase = favorites_usecase()
    usecase.remove_favorite(request.user, menu_key)
    usecase.reorder_favorites(request.user, usecase.favorite_keys_for_user(request.user))
    return JsonResponse({"success": True})


@login_required
@require_http_methods(["PATCH"])
def favorite_menu_order(request: HttpRequest) -> JsonResponse:
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "JSON の形式が不正です。"}, status=400)

    menu_keys = payload.get("menuKeys")
    if not isinstance(menu_keys, list):
        return JsonResponse({"success": False, "error": "menuKeys を指定してください。"}, status=400)

    favorites_usecase().reorder_favorites(request.user, [str(key) for key in menu_keys])
    return JsonResponse({"success": True})
