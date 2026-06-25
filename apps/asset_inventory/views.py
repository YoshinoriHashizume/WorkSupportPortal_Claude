from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.asset_inventory.composition import export_csv_usecase, list_page_usecase
from apps.asset_inventory.domain.list_query import build_list_page_query_string
from apps.asset_inventory.domain.ports import PAGE_SIZE_OPTIONS, PLATE_FILTER_OPTIONS, STATUS_FILTER_OPTIONS
from apps.asset_inventory.domain.row_color_rules import build_row_color_rule_rows
from apps.asset_inventory.domain.sort_headers import build_table_headers
from apps.asset_inventory.domain.table_display import sort_spec_label
from apps.asset_inventory.usecase.usecase_list_page import parse_list_page_query
from apps.portal.favorites import is_menu_favorited


def _access_key(request: HttpRequest) -> str:
    return str(request.session.get("desknet_access_key") or "").strip()


def _query_params(request: HttpRequest) -> dict[str, str]:
    return {key: values[-1] for key, values in request.GET.lists() if values}


def _query_sites(request: HttpRequest) -> list[str]:
    return [value.strip() for value in request.GET.getlist("site") if value.strip()]


@login_required
def list_page(request: HttpRequest) -> HttpResponse:
    query = parse_list_page_query(_query_params(request), _query_sites(request))
    result = list_page_usecase().execute(_access_key(request), query)
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
    )
    export_csv_href = (
        "?"
        + build_list_page_query_string(
            management_id=result.selected_management_id,
            status=result.status_filter,
            site_filter=result.site_filter,
            plate_filter=result.plate_filter,
            sort_specs=result.sort_specs,
            page=1,
            page_size=result.page_size,
        )
    )
    has_list_data = bool(result.selected_management_id) and result.error_message is None
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
def export_csv(request: HttpRequest) -> HttpResponse:
    from datetime import datetime

    query = parse_list_page_query(_query_params(request), _query_sites(request))
    access_key = _access_key(request)
    if not access_key:
        return HttpResponse(
            "desknet's のアクセスキーがありません。再ログインしてください。",
            status=503,
            content_type="text/plain; charset=utf-8",
        )

    content, error = export_csv_usecase().execute_safe(access_key, query)
    if error:
        return HttpResponse(error, status=502, content_type="text/plain; charset=utf-8")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="asset_inventory_{timestamp}.csv"'
    return response
