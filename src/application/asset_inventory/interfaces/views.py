from __future__ import annotations

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse

from application.asset_inventory.interfaces.wiring import (
    export_asp_import_usecase,
    export_csv_usecase,
    fetch_attachment_usecase,
    list_page_usecase,
    resolve_access_key_usecase,
)
from application.asset_inventory.domain.value_objects.errors import DesknetApiError
from application.asset_inventory.domain.value_objects.reconcile_cache import has_amendment_snapshot
from application.asset_inventory.domain.value_objects.list_client_data import build_list_client_payload
from application.asset_inventory.domain.value_objects.list_query import (
    build_list_page_query_string,
    empty_list_page_result,
    parse_list_page_query,
)
from application.asset_inventory.domain.repositories.ports import PAGE_SIZE_OPTIONS, PLATE_FILTER_OPTIONS, STATUS_FILTER_OPTIONS
from application.asset_inventory.domain.value_objects.row_color_rules import build_row_color_rule_rows
from application.asset_inventory.domain.value_objects.row_detail import build_row_details_index
from application.asset_inventory.domain.value_objects.sort_headers import build_table_headers
from application.asset_inventory.domain.value_objects.table_display import sort_spec_label
from application.portal.interfaces.favorites import is_menu_favorited


def _resolve_access_key(request: HttpRequest) -> tuple[str, str | None]:
    session_key = str(request.session.get("desknet_access_key") or "").strip()
    return resolve_access_key_usecase().execute(session_key)


def _query_params(request: HttpRequest) -> dict[str, str]:
    return {key: values[-1] for key, values in request.GET.lists() if values}


def _query_sites(request: HttpRequest) -> list[str]:
    return [value.strip() for value in request.GET.getlist("site") if value.strip()]


@login_required
def list_page(request: HttpRequest) -> HttpResponse:
    access_key, access_error = _resolve_access_key(request)
    query_params = _query_params(request)
    query = parse_list_page_query(query_params, _query_sites(request))
    if access_error:
        result = empty_list_page_result(error_message=access_error)
    else:
        result = list_page_usecase().execute(access_key, query, session=request.session)
    table_params = query.table_params

    selected_row = next(
        (row for row in result.management_rows if row.data_id == result.selected_management_id),
        None,
    )
    query_base = {
        "management_id": result.selected_management_id,
        "status": result.status_filter,
        "site_filter": result.site_filter,
        "plate_filter": result.plate_filter,
        "asset_number_filter": result.asset_number_filter,
        "sort_specs": result.sort_specs,
        "page_size": result.page_size,
    }
    prev_href = ""
    next_href = ""
    if result.has_previous:
        prev_href = "?" + build_list_page_query_string(**query_base, page=result.page - 1)
    if result.has_next:
        next_href = "?" + build_list_page_query_string(**query_base, page=result.page + 1)
    table_headers = build_table_headers(
        table_params=table_params,
        management_id=result.selected_management_id,
        status=result.status_filter,
        site_filter=result.site_filter,
        plate_filter=result.plate_filter,
        asset_number_filter=result.asset_number_filter,
    )
    export_csv_href = (
        "?"
        + build_list_page_query_string(
            management_id=result.selected_management_id,
            status=result.status_filter,
            site_filter=result.site_filter,
            plate_filter=result.plate_filter,
            asset_number_filter=result.asset_number_filter,
            sort_specs=result.sort_specs,
            page=1,
            page_size=result.page_size,
        )
    )
    has_list_data = bool(result.selected_management_id) and result.error_message is None
    # 取り込み用データの作成は、表示中の突合結果スナップショットだけを入力とする（DD-01・DD-05）
    can_export_asp_import = has_list_data and has_amendment_snapshot(
        request.session, result.selected_management_id
    )
    attachment_proxy_base_path = reverse("asset_inventory:attachment")
    row_details_index = (
        build_row_details_index(result.all_rows, attachment_proxy_base_path=attachment_proxy_base_path)
        if has_list_data
        else {}
    )
    list_client_payload = (
        build_list_client_payload(
            all_rows=result.all_rows,
            row_details_index=row_details_index,
            management_id=result.selected_management_id,
            site_options=result.site_options,
            asset_number_options=result.asset_number_options,
            export_csv_path=reverse("asset_inventory:export_csv"),
        )
        if has_list_data
        else None
    )
    return render(
        request,
        "asset_inventory/list.html",
        {
            "management_rows": result.management_rows,
            "selected_management_id": result.selected_management_id,
            "selected_inventory_name": selected_row.inventory_name if selected_row else "",
            "selected_fiscal_year": selected_row.fiscal_year if selected_row else "",
            "rows": result.rows,
            "counts": result.filtered_counts,
            "site_options": result.site_options,
            "site_filter": result.site_filter,
            "status_filter": result.status_filter,
            "status_filter_options": STATUS_FILTER_OPTIONS,
            "plate_filter": result.plate_filter,
            "plate_filter_options": PLATE_FILTER_OPTIONS,
            "asset_number_filter": result.asset_number_filter,
            "asset_number_options": result.asset_number_options,
            "list_client_payload": list_client_payload,
            "table_headers": table_headers,
            "table_params": table_params,
            "sort_spec_labels": [sort_spec_label(spec) for spec in result.sort_specs],
            "page": result.page,
            "total_pages": result.total_pages,
            "page_size": result.page_size,
            "page_size_options": PAGE_SIZE_OPTIONS,
            "start_index": result.start_index,
            "end_index": result.end_index,
            "has_previous": result.has_previous,
            "has_next": result.has_next,
            "prev_href": prev_href,
            "next_href": next_href,
            "export_csv_href": export_csv_href,
            "row_color_rules": build_row_color_rule_rows(),
            "has_list_data": has_list_data,
            "can_export_asp_import": can_export_asp_import,
            "error_message": result.error_message,
            "warning_message": result.warning_message,
            "is_asset_inventory_favorite": is_menu_favorited(request.user, "asset-inventory"),
            "filtered_total": len(result.filtered_rows),
        },
    )


@login_required
def attachment_proxy(request: HttpRequest) -> HttpResponse:
    source_url = (request.GET.get("src") or "").strip()
    access_key, access_error = _resolve_access_key(request)
    if access_error:
        return HttpResponse(access_error, status=503, content_type="text/plain; charset=utf-8")

    try:
        fetched = fetch_attachment_usecase().execute(
            source_url=source_url,
            access_key=access_key,
            timeout=float(settings.DESKNETS_TIMEOUT_SECONDS),
        )
    except DesknetApiError as exc:
        return HttpResponse(str(exc), status=502, content_type="text/plain; charset=utf-8")

    if fetched is None:
        return HttpResponseForbidden("invalid attachment source")

    content, content_type = fetched
    response = HttpResponse(content, content_type=content_type)
    response["Cache-Control"] = "private, max-age=300"
    return response


@login_required
def export_csv(request: HttpRequest) -> HttpResponse:
    from datetime import datetime

    query = parse_list_page_query(_query_params(request), _query_sites(request))
    access_key, access_error = _resolve_access_key(request)
    if access_error:
        return HttpResponse(access_error, status=503, content_type="text/plain; charset=utf-8")

    content, error = export_csv_usecase().execute_safe(access_key, query, session=request.session)
    if error:
        return HttpResponse(error, status=502, content_type="text/plain; charset=utf-8")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="asset_inventory_{timestamp}.csv"'
    return response


@login_required
def export_asp_import(request: HttpRequest) -> HttpResponse:
    """ASP 取り込み用データ（V-306）を作成する（要件定義書 REQ-ASP-IMPORT-DATA-2026-001 §REQ-F-005〜009）。"""
    from datetime import datetime
    from urllib.parse import quote

    # 画面が表示した突合結果スナップショットだけを入力とするため、desknet's は呼ばない（DD-01・REQ-NF-003）
    query = parse_list_page_query(_query_params(request), _query_sites(request))
    result = export_asp_import_usecase().execute(query, session=request.session)

    # 出力対象が 0 件、またはスナップショットが無いときはダウンロードさせずメッセージを出す（REQ-F-008・REQ-F-009）
    if result.content is None:
        response = HttpResponse(result.message, content_type="text/plain; charset=utf-8")
        response["X-Asp-Import-Status"] = result.status.value
        return response

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    response = HttpResponse(result.content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="asp_import_{timestamp}.csv"'
    response["X-Asp-Import-Status"] = result.status.value
    response["X-Asp-Import-Rows"] = str(result.row_count)
    if result.warning_message:
        # HTTP ヘッダは latin-1 のみのため URL エンコードして渡す（REQ-F-007）
        response["X-Asp-Import-Warning"] = quote(result.warning_message)
    return response
