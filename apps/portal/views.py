from __future__ import annotations

import json

from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .favorites import can_access_menu_item, favorite_items_for_user, next_sort_order, reorder_favorites
from .menu import MENU_BY_KEY, MENU_GROUPS, MENU_ITEMS
from .models import PortalMenuGroupAccess, PortalNotice, UserAccessRequest, UserFavoriteMenu


SENSITIVE_COLUMN_NAMES = {"password", "session_key", "session_data"}
VALID_SORT_DIRECTIONS = {"asc", "desc"}
ADMIN_GROUP_NAME = "管理者"
GENERAL_USER_GROUP_NAME = "一般ユーザー"
ROLE_GROUP_NAMES = (GENERAL_USER_GROUP_NAME, ADMIN_GROUP_NAME)
DEFAULT_DEPARTMENT_GROUP_NAME = "全社"
MANAGEMENT_MENU_GROUP_KEY = "management"
MENU_GROUP_CHOICES = [group for group in MENU_GROUPS if group.key != MANAGEMENT_MENU_GROUP_KEY]


def display_database_value(column_name: str, value: object) -> str:
    if value is None:
        return ""
    normalized_column = column_name.lower()
    if normalized_column in SENSITIVE_COLUMN_NAMES or "token" in normalized_column or "secret" in normalized_column:
        return "********"

    text = str(value)
    return text if len(text) <= 200 else f"{text[:200]}..."


def database_view_context(request: HttpRequest) -> dict[str, object]:
    table_names = sorted(connection.introspection.table_names())
    selected_table = (request.GET.get("table") or "").strip()
    requested_sort_column = (request.GET.get("sort") or "").strip()
    requested_sort_direction = (request.GET.get("dir") or "asc").strip().lower()
    context: dict[str, object] = {
        "title": "データベース",
        "table_names": table_names,
        "selected_table": selected_table,
        "columns": [],
        "column_headers": [],
        "rows": [],
        "total_count": None,
        "row_limit": 100,
        "sort_column": "",
        "sort_direction": "asc",
        "error": "",
    }

    if not selected_table:
        return context

    if selected_table not in table_names:
        context["error"] = "選択されたテーブルが見つかりません。"
        return context

    quoted_table = connection.ops.quote_name(selected_table)
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM {quoted_table}")
        context["total_count"] = cursor.fetchone()[0]

        cursor.execute(f"SELECT * FROM {quoted_table} LIMIT 0")
        columns = [column[0] for column in cursor.description]
        sort_column = requested_sort_column if requested_sort_column in columns else ""
        sort_direction = requested_sort_direction if requested_sort_direction in VALID_SORT_DIRECTIONS else "asc"
        order_clause = ""
        if sort_column:
            order_clause = f" ORDER BY {connection.ops.quote_name(sort_column)} {sort_direction.upper()}"

        cursor.execute(f"SELECT * FROM {quoted_table}{order_clause} LIMIT 100")
        context["columns"] = columns
        context["column_headers"] = [
            {
                "name": column,
                "sort_direction": "desc" if column == sort_column and sort_direction == "asc" else "asc",
                "is_sorted": column == sort_column,
            }
            for column in columns
        ]
        context["sort_column"] = sort_column
        context["sort_direction"] = sort_direction
        context["rows"] = [
            [display_database_value(column_name, value) for column_name, value in zip(columns, row, strict=True)]
            for row in cursor.fetchall()
        ]
    return context


def access_request_entries() -> list[dict[str, object]]:
    requests = UserAccessRequest.objects.filter(status=UserAccessRequest.Status.PENDING).select_related(
        "user", "reviewed_by"
    ).prefetch_related(
        "user__groups",
        "user__portal_menu_group_accesses",
    )
    entries = []
    for access_request in requests:
        group_names = set(access_request.user.groups.values_list("name", flat=True))
        role = ADMIN_GROUP_NAME if ADMIN_GROUP_NAME in group_names else GENERAL_USER_GROUP_NAME
        selected_menu_group_keys = set(
            access_request.user.portal_menu_group_accesses.values_list("group_key", flat=True)
        )
        if access_request.status == UserAccessRequest.Status.PENDING and not selected_menu_group_keys:
            selected_menu_group_keys = {"company"}
        entries.append(
            {
                "access_request": access_request,
                "role": role,
                "selected_menu_group_keys": selected_menu_group_keys,
            }
        )
    return entries


def menu_group_choices_in_order() -> list[dict[str, str]]:
    return [{"key": group.key, "title": group.title} for group in MENU_GROUP_CHOICES]


USER_MANAGEMENT_SORT_LABELS = {
    "username": "社員番号",
    "last_name": "姓",
    "first_name": "名",
    "full_name": "表示名",
    "role": "権限",
    "menu_groups": "使えるグループ",
    "status": "申請状態",
    "is_active": "有効",
    "last_login": "最終ログイン",
}


def user_management_entries(sort_key: str = "username", sort_direction: str = "asc") -> list[dict[str, object]]:
    User = get_user_model()
    access_requests = {request.user_id: request for request in UserAccessRequest.objects.select_related("reviewed_by")}
    menu_group_titles = {group.key: group.title for group in MENU_GROUPS}
    entries = []
    users = User.objects.prefetch_related("groups", "portal_menu_group_accesses").order_by("username")
    for user in users:
        role_names = [name for name in user.groups.values_list("name", flat=True) if name in ROLE_GROUP_NAMES]
        menu_groups = [
            menu_group_titles.get(access.group_key, access.group_key)
            for access in user.portal_menu_group_accesses.all()
        ]
        role = "管理者" if "管理者" in role_names else "一般ユーザー"
        selected_menu_group_keys = list(user.portal_menu_group_accesses.values_list("group_key", flat=True))
        entries.append(
            {
                "user": user,
                "full_name": f"{user.last_name} {user.first_name}".strip() or user.username,
                "role": "、".join(role_names) or "-",
                "editable_role": role,
                "menu_groups": "、".join(menu_groups) or "-",
                "selected_menu_group_keys": selected_menu_group_keys,
                "access_request": access_requests.get(user.id),
                "status_label": access_requests[user.id].get_status_display() if user.id in access_requests else "-",
            }
        )
    valid_sort_key = sort_key if sort_key in USER_MANAGEMENT_SORT_LABELS else "username"
    reverse = sort_direction == "desc"
    entries.sort(key=lambda entry: str(user_management_sort_value(entry, valid_sort_key)), reverse=reverse)
    return entries


def user_management_sort_value(entry: dict[str, object], sort_key: str) -> object:
    user = entry["user"]
    if sort_key == "username":
        return user.username
    if sort_key == "last_name":
        return user.last_name
    if sort_key == "first_name":
        return user.first_name
    if sort_key == "full_name":
        return entry["full_name"]
    if sort_key == "role":
        return entry["role"]
    if sort_key == "menu_groups":
        return entry["menu_groups"]
    if sort_key == "status":
        return entry["status_label"]
    if sort_key == "is_active":
        return "1" if user.is_active else "0"
    if sort_key == "last_login":
        return user.last_login.isoformat() if user.last_login else ""
    return user.username


def user_management_column_headers(sort_key: str, sort_direction: str) -> list[dict[str, object]]:
    active_sort_key = sort_key if sort_key in USER_MANAGEMENT_SORT_LABELS else "username"
    active_direction = sort_direction if sort_direction in VALID_SORT_DIRECTIONS else "asc"
    return [
        {
            "key": key,
            "label": label,
            "sort_direction": "desc" if key == active_sort_key and active_direction == "asc" else "asc",
            "is_sorted": key == active_sort_key,
        }
        for key, label in USER_MANAGEMENT_SORT_LABELS.items()
    ]


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    inventory_order_alert_banner = None
    if can_access_menu_item(request.user, "inventory-order-alert"):
        from apps.inventory_order_alert.composition import portal_dashboard_usecase

        inventory_order_alert_banner = portal_dashboard_usecase().execute()

    return render(
        request,
        "portal/dashboard.html",
        {
            "menu_items": MENU_ITEMS,
            "favorite_items": favorite_items_for_user(request.user),
            "notices": PortalNotice.objects.filter(is_published=True).order_by("-created_at")[:10],
            "inventory_order_alert_banner": inventory_order_alert_banner,
        },
    )


@login_required
def access_status(request: HttpRequest) -> HttpResponse:
    access_request = getattr(request.user, "access_request", None)
    return render(request, "portal/access_status.html", {"access_request": access_request})


@login_required
@require_http_methods(["GET", "POST"])
def access_requests(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        request_id = request.POST.get("request_id")
        action = request.POST.get("action")
        selected_role = request.POST.get("role") or GENERAL_USER_GROUP_NAME
        selected_menu_group_keys = request.POST.getlist("menu_groups")
        note = (request.POST.get("note") or "").strip()
        access_request = UserAccessRequest.objects.select_related("user").get(id=request_id)
        access_request.reviewed_at = timezone.now()
        access_request.reviewed_by = request.user
        access_request.note = note

        if action == "approve":
            role_group_name = ADMIN_GROUP_NAME if selected_role == ADMIN_GROUP_NAME else GENERAL_USER_GROUP_NAME
            role_group, _ = Group.objects.get_or_create(name=role_group_name)
            access_request.status = UserAccessRequest.Status.APPROVED
            access_request.user.groups.set([role_group])
            PortalMenuGroupAccess.objects.filter(user=access_request.user).delete()
            if role_group_name != ADMIN_GROUP_NAME:
                valid_menu_group_keys = {group.key for group in MENU_GROUP_CHOICES}
                PortalMenuGroupAccess.objects.bulk_create(
                    [
                        PortalMenuGroupAccess(user=access_request.user, group_key=group_key)
                        for group_key in selected_menu_group_keys
                        if group_key in valid_menu_group_keys
                    ],
                    ignore_conflicts=True,
                )
        elif action == "reject":
            access_request.status = UserAccessRequest.Status.REJECTED
            access_request.user.groups.clear()
            PortalMenuGroupAccess.objects.filter(user=access_request.user).delete()
        access_request.save()
        return redirect("portal:access_requests")

    return render(
        request,
        "portal/access_requests.html",
        {
            "access_request_entries": access_request_entries(),
            "role_groups": Group.objects.filter(name__in=ROLE_GROUP_NAMES).order_by("name"),
            "menu_group_choices": menu_group_choices_in_order(),
            "admin_group_name": ADMIN_GROUP_NAME,
        },
    )


def delete_portal_user(*, actor: object, target_user: object) -> bool:
    if target_user.id == getattr(actor, "id", None):
        return False
    target_user.delete()
    return True


@login_required
@require_http_methods(["GET", "POST"])
def user_management(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        User = get_user_model()
        user_id = request.POST.get("user_id")
        try:
            target_user = User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return redirect("portal:user_management")

        action = request.POST.get("action", "save")
        if action == "delete":
            delete_portal_user(actor=request.user, target_user=target_user)
            return redirect("portal:user_management")

        target_user.last_name = (request.POST.get("last_name") or "").strip()
        target_user.first_name = (request.POST.get("first_name") or "").strip()
        target_user.email = (request.POST.get("email") or "").strip()
        target_user.save(update_fields=["last_name", "first_name", "email"])

        role_name = ADMIN_GROUP_NAME if request.POST.get("role") == ADMIN_GROUP_NAME else GENERAL_USER_GROUP_NAME
        role_group, _ = Group.objects.get_or_create(name=role_name)
        target_user.groups.set([role_group])

        valid_menu_group_keys = {group.key for group in MENU_GROUP_CHOICES}
        selected_menu_group_keys = request.POST.getlist("menu_groups")
        PortalMenuGroupAccess.objects.filter(user=target_user).delete()
        if role_name != ADMIN_GROUP_NAME:
            PortalMenuGroupAccess.objects.bulk_create(
                [
                    PortalMenuGroupAccess(user=target_user, group_key=group_key)
                    for group_key in selected_menu_group_keys
                    if group_key in valid_menu_group_keys
                ],
                ignore_conflicts=True,
            )
        return redirect("portal:user_management")

    sort_key = (request.GET.get("sort") or "username").strip()
    sort_direction = (request.GET.get("dir") or "asc").strip().lower()
    if sort_direction not in VALID_SORT_DIRECTIONS:
        sort_direction = "asc"
    return render(
        request,
        "portal/user_management.html",
        {
            "user_entries": user_management_entries(sort_key, sort_direction),
            "column_headers": user_management_column_headers(sort_key, sort_direction),
            "sort_key": sort_key if sort_key in USER_MANAGEMENT_SORT_LABELS else "username",
            "sort_direction": sort_direction,
            "role_group_names": ROLE_GROUP_NAMES,
            "menu_group_choices": menu_group_choices_in_order(),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def notice_management(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        action = request.POST.get("action")
        notice_id = request.POST.get("notice_id")
        if action == "delete" and notice_id:
            PortalNotice.objects.filter(id=notice_id).delete()
            return redirect("portal:notice_management")

        title = (request.POST.get("title") or "").strip()
        body = (request.POST.get("body") or "").strip()
        is_published = request.POST.get("is_published") == "on"
        if title and body:
            if notice_id:
                notice = PortalNotice.objects.get(id=notice_id)
                notice.title = title
                notice.body = body
                notice.is_published = is_published
                notice.save(update_fields=["title", "body", "is_published", "updated_at"])
            else:
                PortalNotice.objects.create(
                    title=title,
                    body=body,
                    is_published=is_published,
                    created_by=request.user,
                )
        return redirect("portal:notice_management")

    return render(
        request,
        "portal/notices.html",
        {
            "notices": PortalNotice.objects.order_by("-created_at"),
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
        return render(request, "portal/database.html", database_view_context(request))
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

    UserFavoriteMenu.objects.get_or_create(
        user=request.user,
        menu_key=menu_key,
        defaults={"sort_order": next_sort_order(request.user)},
    )
    return JsonResponse({"success": True})


@login_required
@require_http_methods(["DELETE"])
def favorite_menu_detail(request: HttpRequest, menu_key: str) -> JsonResponse:
    UserFavoriteMenu.objects.filter(user=request.user, menu_key=menu_key).delete()
    reorder_favorites(request.user, (favorite.menu_key for favorite in UserFavoriteMenu.objects.filter(user=request.user)))
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

    reorder_favorites(request.user, [str(key) for key in menu_keys])
    return JsonResponse({"success": True})
