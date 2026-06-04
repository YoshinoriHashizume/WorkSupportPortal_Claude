from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import replace
from datetime import date
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.portal.favorites import favorite_keys_for_user

from .domain.excel_export import build_gonenkukumi_workbook
from .domain.schemas import GonenKukumiSearchParams, parse_as_of_date, validate_search_params
from .domain.search_params_from_url import search_params_from_url
from .domain.year_month_nav import YearMonth
from .infrastructure.oracle.client import (
    OracleNotConfiguredError,
    OracleQueryError,
    list_cust_items,
    list_customers,
    run_gonenkukumi_oracle_search,
)
from .models import GonenKukumiSearchHistory


FILENAME_UNSAFE_PATTERN = re.compile(r'[\\/:*?"<>|]+')


def safe_filename_part(value: object) -> str:
    return FILENAME_UNSAFE_PATTERN.sub("_", str(value or "").strip()) or "-"


def json_body(request: HttpRequest) -> dict[str, object]:
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


def error_response(message: str, status: int) -> JsonResponse:
    return JsonResponse({"success": False, "error": {"message": message}}, status=status)


def oracle_error_message(exc: OracleQueryError) -> str:
    if str(exc) == "NAISAK_NOT_FOUND":
        return "内作品番が見つかりません。得意先品目、設変値、対象日付を確認してください。"
    return str(exc)


def oracle_error_status(exc: OracleQueryError) -> int:
    return 404 if str(exc) == "NAISAK_NOT_FOUND" else 502


def api_login_required(view_func: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        if not request.user.is_authenticated:
            return error_response("ログインが必要です。", 401)
        return view_func(request, *args, **kwargs)

    return wrapper


def save_history(request: HttpRequest, params: GonenKukumiSearchParams) -> None:
    GonenKukumiSearchHistory.objects.create(
        user=request.user,
        cust_code=params.cust_code,
        cust_item=params.cust_item,
        option_change=params.option_change,
        year_month=params.year_month,
    )


def latest_unique_histories(user: object, limit: int = 20) -> list[dict[str, object]]:
    histories = []
    seen: set[tuple[str, str, str, str]] = set()
    queryset = GonenKukumiSearchHistory.objects.filter(user=user).order_by("-executed_at")
    for history in queryset:
        key = (history.cust_code, history.cust_item, history.option_change, history.year_month)
        if key in seen:
            continue
        seen.add(key)
        histories.append(history.to_api_dict())
        if len(histories) >= limit:
            break
    return histories


def params_for_month(params: GonenKukumiSearchParams, year_month: str) -> GonenKukumiSearchParams:
    parsed = YearMonth.parse(year_month)
    return replace(params, year_month=parsed.format())


def year_month_index(year_month: str) -> int:
    parsed = YearMonth.parse(year_month)
    return parsed.year * 12 + parsed.month


def month_label(base_year_month: str, panel_year_month: str) -> str:
    delta = year_month_index(panel_year_month) - year_month_index(base_year_month)
    if delta == -2:
        return "前々月"
    if delta == -1:
        return "前月"
    if delta == 0:
        return "基準"
    if delta == 1:
        return "次月"
    if delta == 2:
        return "次々月"
    if delta < 0:
        return f"{abs(delta)}か月前"
    return f"{delta}か月後"


def export_filename(params: GonenKukumiSearchParams) -> str:
    year_month = YearMonth.parse(params.year_month)
    timestamp = timezone.localtime().strftime("%Y%m%d%H%M%S")
    return (
        f"{safe_filename_part(params.cust_code)}_"
        f"{safe_filename_part(params.cust_item)}_"
        f"{year_month.year:04d}_"
        f"{year_month.month:02d}_"
        f"{timestamp}.xlsx"
    )


def display_months_from_query(params: GonenKukumiSearchParams, query: object) -> list[str]:
    base_year_month = YearMonth.parse(params.year_month).format()
    raw_months = query.get("months", "") if hasattr(query, "get") else ""
    values = [base_year_month]
    if raw_months:
        values.extend(str(raw_months).split(","))

    unique_months = {YearMonth.parse(value.strip()).format() for value in values if str(value).strip()}
    return sorted(unique_months, key=year_month_index)


def block_group_key(block: dict[str, object]) -> tuple[object, ...]:
    meta = block.get("meta") if isinstance(block.get("meta"), dict) else {}
    if block.get("kind") == "supplier":
        return (
            "supplier",
            meta.get("kaiso"),
            meta.get("itemCd"),
            meta.get("vendCd"),
        )
    return (
        "customer",
        meta.get("custCode"),
        meta.get("custItem"),
    )


def build_multi_month_result(params: GonenKukumiSearchParams, year_months: list[str]) -> dict[str, object]:
    base_year_month = YearMonth.parse(params.year_month).format()
    month_specs = [
        (year_month, month_label(base_year_month, year_month), year_month)
        for year_month in year_months
    ]
    month_results = [
        {
            "key": key,
            "label": label,
            "result": run_gonenkukumi_oracle_search(params_for_month(params, year_month)),
        }
        for key, label, year_month in month_specs
    ]

    current_result = next(item["result"] for item in month_results if item["result"].get("yearMonth") == base_year_month)
    grouped_blocks: dict[tuple[object, ...], dict[str, object]] = {}

    for month_result in month_results:
        result = month_result["result"]
        for block in result.get("blocks", []):
            group_key = block_group_key(block)
            grouped_block = grouped_blocks.setdefault(
                group_key,
                {
                    "kind": block.get("kind", "customer"),
                    "label": block.get("label", ""),
                    "meta": block.get("meta", {}),
                    "theme": block.get("theme", {}),
                    "monthPanels": [],
                },
            )
            grouped_block["monthPanels"].append(
                {
                    "key": month_result["key"],
                    "label": month_result["label"],
                    "yearMonth": result.get("yearMonth"),
                    "activeDays": result.get("activeDays"),
                    "holidayDays": result.get("holidayDays", []),
                    "days": result.get("days", []),
                    "rows": block.get("rows", []),
                }
            )

    return {
        **current_result,
        "months": [
            {"key": item["key"], "label": item["label"], "yearMonth": item["result"].get("yearMonth")}
            for item in month_results
        ],
        "blocks": list(grouped_blocks.values()),
    }


@login_required
@require_GET
def search_page(request: HttpRequest) -> HttpResponse:
    latest = GonenKukumiSearchHistory.objects.filter(user=request.user).first()
    today = date.today()
    initial = {
        "custCode": latest.cust_code if latest else "",
        "custItem": latest.cust_item if latest else "",
        "optionChange": latest.option_change if latest else "*",
        "yearMonth": latest.year_month if latest else f"{today.year:04d}-{today.month:02d}",
    }
    return render(
        request,
        "gonenkukumi/search.html",
        {
            "initial": initial,
            "is_five_year_nine_favorite": "five-year-nine" in favorite_keys_for_user(request.user),
        },
    )


@login_required
@require_GET
def result_page(request: HttpRequest) -> HttpResponse:
    try:
        params = search_params_from_url(request.GET)
        result = build_multi_month_result(params, display_months_from_query(params, request.GET))
    except OracleQueryError as exc:
        return render(request, "gonenkukumi/result.html", {"error": oracle_error_message(exc), "result": None})
    except (ValueError, OracleNotConfiguredError) as exc:
        return render(request, "gonenkukumi/result.html", {"error": str(exc), "result": None})
    return render(request, "gonenkukumi/result.html", {"error": None, "result": result})


@require_POST
@api_login_required
def api_search(request: HttpRequest) -> JsonResponse:
    try:
        params = validate_search_params(json_body(request))
        result = run_gonenkukumi_oracle_search(params)
    except json.JSONDecodeError:
        return error_response("JSON の形式が不正です。", 400)
    except ValueError as exc:
        return error_response(str(exc), 400)
    except OracleNotConfiguredError as exc:
        return error_response(str(exc), 503)
    except OracleQueryError as exc:
        return error_response(oracle_error_message(exc), oracle_error_status(exc))
    save_history(request, params)
    return JsonResponse({"success": True, "result": result})


@require_GET
@api_login_required
def api_customers(request: HttpRequest) -> JsonResponse:
    keyword = request.GET.get("q", "")
    try:
        customers = list_customers(keyword)
    except OracleNotConfiguredError as exc:
        return error_response(str(exc), 503)
    except OracleQueryError as exc:
        return error_response(str(exc), 502)
    return JsonResponse({"success": True, "customers": customers})


@require_GET
@api_login_required
def api_history(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"success": True, "histories": latest_unique_histories(request.user)})


@require_POST
@api_login_required
def api_oracle_result(request: HttpRequest) -> JsonResponse:
    try:
        params = validate_search_params(json_body(request))
        result = run_gonenkukumi_oracle_search(params)
    except json.JSONDecodeError:
        return error_response("JSON の形式が不正です。", 400)
    except ValueError as exc:
        return error_response(str(exc), 400)
    except OracleNotConfiguredError as exc:
        return error_response(str(exc), 503)
    except OracleQueryError as exc:
        return error_response(oracle_error_message(exc), oracle_error_status(exc))
    return JsonResponse({"success": True, "result": result})


@require_GET
@api_login_required
def api_cust_items(request: HttpRequest) -> JsonResponse:
    cust_code = request.GET.get("custCode", "")
    keyword = request.GET.get("q", "")
    if not cust_code:
        return error_response("得意先コードを指定してください。", 400)
    try:
        as_of_date = parse_as_of_date(request.GET.get("asOfDate"), request.GET.get("yearMonth") or date.today().strftime("%Y-%m"))
        items = list_cust_items(cust_code, keyword, as_of_date)
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
        params = search_params_from_url(request.GET)
        result = build_multi_month_result(params, display_months_from_query(params, request.GET))
    except ValueError as exc:
        return error_response(str(exc), 400)
    except OracleNotConfiguredError as exc:
        return error_response(str(exc), 503)
    except OracleQueryError as exc:
        return error_response(oracle_error_message(exc), oracle_error_status(exc))
    content = build_gonenkukumi_workbook(result)
    response = HttpResponse(content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    filename = export_filename(params)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
