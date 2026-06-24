from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from apps.inventory_order_alert.composition import (
    confirmation_memos_usecase,
    export_csv_usecase,
    list_page_usecase,
    reset_confirmations_usecase,
    save_alert_settings_usecase,
    save_confirmation_usecase,
)
from apps.portal.favorites import is_menu_favorited


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
            "confirmation_status_choices": context.confirmation_status_choices,
            "alert_rule_rows": context.alert_rule_rows,
            "warning_shipment_months": context.warning_shipment_months,
            "warning_incoming_months": context.warning_incoming_months,
            "warning_month_options": context.warning_month_options,
            "can_reset_confirmations": context.can_reset_confirmations,
            "test_data_warning": context.test_data_warning,
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
@require_http_methods(["PUT"])
def api_save_alert_settings(request: HttpRequest) -> JsonResponse:
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "message": "JSON の形式が不正です。"}, status=400)

    try:
        save_alert_settings_usecase().execute(payload, updated_by=request.user)
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)

    return JsonResponse({"ok": True})


@login_required
def export_csv(request: HttpRequest) -> HttpResponse:
    try:
        result = export_csv_usecase().execute()
    except ValueError as exc:
        return HttpResponse(str(exc), status=404)

    response = HttpResponse(result.content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{result.filename}"'
    return response
