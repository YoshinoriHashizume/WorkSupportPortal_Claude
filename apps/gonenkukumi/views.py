from __future__ import annotations

import json
from collections.abc import Callable
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from apps.portal.favorites import favorite_keys_for_user

from apps.gonenkukumi.domain.errors import (
    OracleNotConfiguredError,
    OracleQueryError,
    oracle_error_message,
)
from apps.gonenkukumi.composition import (
    export_excel_usecase,
    list_cust_items_usecase,
    list_customers_usecase,
    list_history_usecase,
    oracle_result_usecase,
    result_page_usecase,
    search_page_usecase,
    search_usecase,
)


def _oracle_error_http_status(exc: OracleQueryError) -> int:
    from apps.gonenkukumi.domain.errors import NAISAK_NOT_FOUND

    return 404 if str(exc) == NAISAK_NOT_FOUND else 502


def json_body(request: HttpRequest) -> dict[str, object]:
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


def error_response(message: str, status: int) -> JsonResponse:
    return JsonResponse({"success": False, "error": {"message": message}}, status=status)


def api_login_required(view_func: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        if not request.user.is_authenticated:
            return error_response("ログインが必要です。", 401)
        return view_func(request, *args, **kwargs)

    return wrapper


@login_required
@require_GET
def search_page(request: HttpRequest) -> HttpResponse:
    context = search_page_usecase().execute(request.user.pk)
    return render(
        request,
        "gonenkukumi/search.html",
        {
            "initial": context.initial,
            "customers": context.customers,
            "customer_load_error": context.customer_load_error,
            "oracle_use_mock": context.oracle_use_mock,
            "is_five_year_nine_favorite": "five-year-nine" in favorite_keys_for_user(request.user),
        },
    )


@login_required
@require_GET
def result_page(request: HttpRequest) -> HttpResponse:
    try:
        result = result_page_usecase().execute(request.GET)
    except OracleQueryError as exc:
        return render(request, "gonenkukumi/result.html", {"error": oracle_error_message(exc), "result": None})
    except (ValueError, OracleNotConfiguredError) as exc:
        return render(request, "gonenkukumi/result.html", {"error": str(exc), "result": None})
    return render(request, "gonenkukumi/result.html", {"error": None, "result": result})


@require_POST
@api_login_required
def api_search(request: HttpRequest) -> JsonResponse:
    try:
        result = search_usecase().execute(request.user.pk, json_body(request))
    except json.JSONDecodeError:
        return error_response("JSON の形式が不正です。", 400)
    except ValueError as exc:
        return error_response(str(exc), 400)
    except OracleNotConfiguredError as exc:
        return error_response(str(exc), 503)
    except OracleQueryError as exc:
        return error_response(oracle_error_message(exc), _oracle_error_http_status(exc))
    return JsonResponse({"success": True, "result": result})


@require_GET
@api_login_required
def api_customers(request: HttpRequest) -> JsonResponse:
    keyword = request.GET.get("q", "")
    try:
        customers = list_customers_usecase().execute(keyword)
    except OracleNotConfiguredError as exc:
        return error_response(str(exc), 503)
    except OracleQueryError as exc:
        return error_response(str(exc), 502)
    return JsonResponse({"success": True, "customers": customers})


@require_GET
@api_login_required
def api_history(request: HttpRequest) -> JsonResponse:
    histories = list_history_usecase().execute(request.user.pk)
    return JsonResponse({"success": True, "histories": histories})


@require_POST
@api_login_required
def api_oracle_result(request: HttpRequest) -> JsonResponse:
    try:
        result = oracle_result_usecase().execute(json_body(request))
    except json.JSONDecodeError:
        return error_response("JSON の形式が不正です。", 400)
    except ValueError as exc:
        return error_response(str(exc), 400)
    except OracleNotConfiguredError as exc:
        return error_response(str(exc), 503)
    except OracleQueryError as exc:
        return error_response(oracle_error_message(exc), _oracle_error_http_status(exc))
    return JsonResponse({"success": True, "result": result})


@require_GET
@api_login_required
def api_cust_items(request: HttpRequest) -> JsonResponse:
    cust_code = request.GET.get("custCode", "")
    keyword = request.GET.get("q", "")
    try:
        items = list_cust_items_usecase().execute(
            cust_code,
            keyword,
            request.GET.get("asOfDate"),
            request.GET.get("yearMonth"),
        )
    except ValueError as exc:
        return error_response(str(exc), 400)
    except OracleNotConfiguredError as exc:
        return error_response(str(exc), 503)
    except OracleQueryError as exc:
        return error_response(str(exc), 502)
    return JsonResponse({"success": True, "items": items})


@require_GET
@api_login_required
def api_export(request: HttpRequest) -> HttpResponse:
    try:
        content, filename = export_excel_usecase().execute(request.GET)
    except ValueError as exc:
        return error_response(str(exc), 400)
    except OracleNotConfiguredError as exc:
        return error_response(str(exc), 503)
    except OracleQueryError as exc:
        return error_response(oracle_error_message(exc), _oracle_error_http_status(exc))
    response = HttpResponse(content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
