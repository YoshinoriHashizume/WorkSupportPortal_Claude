from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from application.portal.interfaces.favorites import page_favorite_toggle_context
from application.shipment_trend.interfaces.wiring import (
    chart_data_usecase,
    delete_baseline_year_usecase,
    export_csv_usecase,
    list_page_usecase,
    save_alert_settings_usecase,
    save_baseline_year_usecase,
)
from application.shipment_trend.domain.value_objects.list_filter import visible_cust_options


def _query_params(request: HttpRequest) -> dict[str, str]:
    return {key: values[-1] for key, values in request.GET.lists() if values}


def _json_body(request: HttpRequest) -> dict[str, object]:
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("JSON の形式が不正です。") from exc
    if not isinstance(payload, dict):
        raise ValueError("JSON の形式が不正です。")
    return payload


@login_required
@require_http_methods(["GET", "POST"])
def list_page(request: HttpRequest) -> HttpResponse:
    refresh_requested = request.method == "POST" and request.POST.get("action") == "refresh"
    context = list_page_usecase().execute(
        query_params=_query_params(request),
        refresh_requested=refresh_requested,
        user=request.user,
    )
    favorite_context = page_favorite_toggle_context(request.user, "shipment-trend-list")
    return render(
        request,
        "shipment_trend/list.html",
        {
            **favorite_context,
            "rows": context.rows,
            "paginated": context.paginated,
            "sort_spec_labels": context.sort_spec_labels,
            "sort_specs": context.sort_specs,
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
            "error_message": context.error_message,
            "refresh_message": context.refresh_message,
            "has_list_data": context.has_list_data,
            "has_summary": context.has_summary,
            "as_of_label": context.as_of_label,
            "alert_rule_rows": context.alert_rule_rows,
            "decrease_threshold_pct": context.decrease_threshold_pct,
            "increase_threshold_pct": context.increase_threshold_pct,
            "threshold_options": context.threshold_options,
            "list_client_payload": context.list_client_payload,
        },
    )


@login_required
@require_GET
def api_chart_data(request: HttpRequest) -> JsonResponse:
    try:
        result = chart_data_usecase().execute(
            cust_code=request.GET.get("custCode", ""),
            item_cd=request.GET.get("itemCd", ""),
        )
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)
    return JsonResponse({"ok": True, "chart": result.payload})


@login_required
@require_http_methods(["PUT"])
def api_save_alert_settings(request: HttpRequest) -> JsonResponse:
    try:
        payload = _json_body(request)
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)

    try:
        settings = save_alert_settings_usecase().execute(payload, updated_by=request.user)
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)

    return JsonResponse(
        {
            "ok": True,
            "decreaseThresholdPct": settings.decrease_threshold_pct,
            "increaseThresholdPct": settings.increase_threshold_pct,
        }
    )


@login_required
@require_http_methods(["PUT", "DELETE"])
def api_baseline_year(request: HttpRequest) -> JsonResponse:
    try:
        payload = _json_body(request)
        cust_code = str(payload.get("custCode") or "")
        item_cd = str(payload.get("itemCd") or "")
        if request.method == "PUT":
            baseline_year = payload.get("baselineYear")
            if baseline_year is None or baseline_year == "":
                raise ValueError("baselineYear を指定してください。")
            try:
                year_int = int(baseline_year)
            except (TypeError, ValueError) as exc:
                raise ValueError("baselineYear は整数で指定してください。") from exc
            result = save_baseline_year_usecase().execute(
                cust_code=cust_code,
                item_cd=item_cd,
                baseline_fiscal_year=year_int,
                updated_by=request.user,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "custCode": result.cust_code,
                    "itemCd": result.item_cd,
                    "baselineYear": result.baseline_fiscal_year,
                    "dataFirstFiscalYear": result.data_first_fiscal_year,
                }
            )
        result = delete_baseline_year_usecase().execute(cust_code=cust_code, item_cd=item_cd)
        return JsonResponse(
            {
                "ok": True,
                "custCode": result.cust_code,
                "itemCd": result.item_cd,
                "deleted": result.deleted,
            }
        )
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)


@login_required
def export_csv(request: HttpRequest) -> HttpResponse:
    try:
        result = export_csv_usecase().execute(query_params=_query_params(request))
    except ValueError as exc:
        return HttpResponse(str(exc), status=404)

    response = HttpResponse(result.content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{result.filename}"'
    return response
