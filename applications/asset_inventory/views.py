from __future__ import annotations

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse

from applications.identity.domain.errors import DesknetAuthError

from applications.asset_inventory.composition import export_csv_usecase, list_page_usecase
from applications.asset_inventory.domain.attachment_proxy import fetch_attachment_content, is_allowed_attachment_url
from applications.asset_inventory.domain.errors import DesknetApiError
from applications.asset_inventory.infrastructure.desknet.service_access_key import resolve_asset_inventory_access_key
from applications.asset_inventory.domain.list_client_data import build_list_client_payload
from applications.asset_inventory.domain.list_query import build_list_page_query_string
from applications.asset_inventory.domain.ports import PAGE_SIZE_OPTIONS, PLATE_FILTER_OPTIONS, STATUS_FILTER_OPTIONS
from applications.asset_inventory.domain.row_color_rules import build_row_color_rule_rows
from applications.asset_inventory.domain.row_detail import build_row_details_index
from applications.asset_inventory.domain.sort_headers import build_table_headers
from applications.asset_inventory.domain.table_display import sort_spec_label
from applications.asset_inventory.usecase.usecase_list_page import _empty_result, parse_list_page_query
from applications.portal.favorites import is_menu_favorited


def _resolve_access_key(request: HttpRequest) -> tuple[str, str | None]:
    session_key = str(request.session.get("desknet_access_key") or "").strip()
    try:
        access_key = resolve_asset_inventory_access_key(session_key)
    except DesknetAuthError:
        return (
            "",
            "desknet's サービス連携アカウントでログインできません。"
            "管理者に DESKNETS_ASSET_INVENTORY_LOGIN_ID の設定をご確認ください。",
        )
    if not access_key:
        return "", "desknet's のアクセスキーがありません。再ログインしてください。"
    return access_key, None


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
        result = _empty_result(error_message=access_error)
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
            "error_message": result.error_message,
            "is_asset_inventory_favorite": is_menu_favorited(request.user, "asset-inventory"),
            "filtered_total": len(result.filtered_rows),
        },
    )


@login_required
def attachment_proxy(request: HttpRequest) -> HttpResponse:
    source_url = (request.GET.get("src") or "").strip()
    if not source_url or not is_allowed_attachment_url(source_url, settings.DESKNETS_LOGIN_URL):
        return HttpResponseForbidden("invalid attachment source")

    access_key, access_error = _resolve_access_key(request)
    if access_error:
        return HttpResponse(access_error, status=503, content_type="text/plain; charset=utf-8")

    try:
        content, content_type = fetch_attachment_content(
            source_url=source_url,
            access_key=access_key,
            timeout=float(settings.DESKNETS_TIMEOUT_SECONDS),
        )
    except DesknetApiError as exc:
        return HttpResponse(str(exc), status=502, content_type="text/plain; charset=utf-8")

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
