from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from application.inventory_order_alert.domain.value_objects.list_client_data import build_list_client_payload
from application.inventory_order_alert.domain.value_objects.list_filter import visible_cust_options
from application.inventory_order_alert.interfaces.wiring import (
    app_settings_usecase,
    can_reset_confirmations,
    confirmation_memos_usecase,
    dashboard_summary_usecase,
    export_csv_usecase,
    list_page_usecase,
    reset_confirmations_usecase,
    save_confirmation_usecase,
    stock_locations_usecase,
    summary_api_usecase,
    vendors_usecase,
)
from application.portal.interfaces.favorites import is_menu_favorited, is_portal_admin


def _query_params(request: HttpRequest) -> dict[str, str]:
    return {key: values[-1] for key, values in request.GET.lists() if values}


@login_required
def list_page(request: HttpRequest) -> HttpResponse:
    uploaded_csv = None
    if request.method == "POST" and request.FILES.get("slims_csv"):
        uploaded = request.FILES["slims_csv"]
        uploaded_csv = (uploaded.name, uploaded.read())

    context = list_page_usecase().execute(
        query_params=_query_params(request),
        uploaded_csv=uploaded_csv,
        user=request.user,
    )
    list_client_payload = (
        build_list_client_payload(
            all_rows=context.all_rows,
            filter_options=context.filter_options,
            confirmation_status_choices=context.confirmation_status_choices,
            recommended_actions=context.recommended_actions,
        )
        if context.has_list_data
        else None
    )
    return render(
        request,
        "inventory_order_alert/list.html",
        {
            "rows": context.rows,
            "paginated": context.paginated,
            "table_params": context.table_params,
            "sort_spec_labels": context.sort_spec_labels,
            "list_filter": context.list_filter,
            "filter_options": context.filter_options,
            "visible_cust_options": visible_cust_options(
                context.filter_options,
                context.list_filter.cust_chrg_psn_cd,
            ),
            "summary_total": context.summary_total,
            "filtered_total": context.filtered_total,
            "table_headers": context.table_headers,
            "page_size_options": context.page_size_options,
            "prev_href": context.prev_href,
            "next_href": context.next_href,
            "counts": context.counts,
            "error_message": context.error_message,
            "import_message": context.import_message,
            "stock_as_of_label": context.stock_as_of_label,
            "stock_import_info": context.stock_import_info,
            "has_slims_stock": context.has_slims_stock,
            "has_summary": context.has_summary,
            "has_list_data": context.has_list_data,
            "stock_stale": context.stock_stale,
            "is_inventory_order_alert_favorite": is_menu_favorited(request.user, "inventory-order-alert"),
            "is_admin": is_portal_admin(request.user),
            "confirmation_status_choices": context.confirmation_status_choices,
            "flow_selection": context.flow_selection,
            "evaluation_periods": context.evaluation_periods,
            "flow_quadrant_filter": context.flow_quadrant_filter,
            "flow_quadrant_rule_rows": context.flow_quadrant_rule_rows,
            "test_data_warning": context.test_data_warning,
            "list_client_payload": list_client_payload,
        },
    )


@login_required
@require_http_methods(["PUT"])
def api_save_confirmation(request: HttpRequest) -> JsonResponse:
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "message": "JSON の形式が不正です。"}, status=400)

    try:
        result = save_confirmation_usecase().execute(payload, confirmed_by=request.user.username)
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)

    return JsonResponse(result)


@login_required
def api_confirmation_memos(request: HttpRequest) -> JsonResponse:
    use_case = confirmation_memos_usecase()
    if request.method == "GET":
        try:
            result = use_case.list_memos(
                cust_code=request.GET.get("custCode", "").strip(),
                item_cd=request.GET.get("itemCd", "").strip(),
            )
        except ValueError as exc:
            return JsonResponse({"ok": False, "message": str(exc)}, status=400)
        return JsonResponse({"ok": True, "memos": result.memos})

    if request.method != "POST":
        return JsonResponse({"ok": False, "message": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "message": "JSON の形式が不正です。"}, status=400)

    try:
        result = use_case.add_memo(payload, created_by=request.user.username)
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)

    return JsonResponse({"ok": True, "memo": result.memo})


@login_required
@require_http_methods(["POST"])
def api_reset_confirmations(request: HttpRequest) -> JsonResponse:
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "message": "JSON の形式が不正です。"}, status=400)

    result = reset_confirmations_usecase().execute(payload)
    return JsonResponse(result)


@login_required
@require_http_methods(["GET"])
def settings_page(request: HttpRequest) -> HttpResponse:
    """設定画面 SCR-02（§4.2）。管理者のみが開ける。"""
    if not is_portal_admin(request.user):
        return HttpResponse("権限がありません。", status=403)

    settings = app_settings_usecase().load()
    return render(
        request,
        "inventory_order_alert/settings.html",
        {
            "warning_days": settings.warning_days,
            "stock_stale_days": settings.stock_stale_days,
            "can_reset_confirmations": can_reset_confirmations(),
        },
    )


@login_required
@require_http_methods(["GET", "PUT"])
def api_settings(request: HttpRequest) -> JsonResponse:
    """設定 API（§8.10）。管理者のみが参照・更新できる。"""
    if not is_portal_admin(request.user):
        return JsonResponse({"ok": False, "message": "権限がありません。"}, status=403)

    use_case = app_settings_usecase()
    if request.method == "GET":
        return JsonResponse({"ok": True, "settings": use_case.load_payload()})

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "message": "JSON の形式が不正です。"}, status=400)

    try:
        settings = use_case.save(payload, updated_by=request.user)
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)

    return JsonResponse({"ok": True, "settings": settings})


@login_required
@require_http_methods(["GET"])
def api_summary(request: HttpRequest) -> JsonResponse:
    """集計結果 API（§8.1）。Oracle へは問い合わせない。"""
    try:
        result = summary_api_usecase().execute(_query_params(request))
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)

    return JsonResponse(result)


@login_required
@require_http_methods(["GET"])
def api_stock_locations(request: HttpRequest) -> JsonResponse:
    """在庫内訳 API（§8.4）。"""
    try:
        result = stock_locations_usecase().execute(request.GET.get("itemCd", ""))
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)

    return JsonResponse(result)


@login_required
@require_http_methods(["GET"])
def api_vendors(request: HttpRequest) -> JsonResponse:
    """仕入先候補 API（§8.9）。集計スナップショットから生成する。"""
    return JsonResponse(vendors_usecase().execute())


@login_required
@require_http_methods(["GET"])
def api_dashboard_summary(request: HttpRequest) -> JsonResponse:
    """メニュー画面アラート帯の集計 API（§8.11）。"""
    return JsonResponse(dashboard_summary_usecase().execute())


@login_required
def export_csv(request: HttpRequest) -> HttpResponse:
    try:
        result = export_csv_usecase().execute(query_params=_query_params(request))
    except ValueError as exc:
        return HttpResponse(str(exc), status=404)

    response = HttpResponse(result.content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{result.filename}"'
    return response
