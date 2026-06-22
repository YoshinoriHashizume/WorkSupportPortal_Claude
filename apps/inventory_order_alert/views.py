from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.inventory_order_alert.application.confirmation_reset_result import build_confirmation_reset_result
from apps.inventory_order_alert.application.confirmation_save_result import build_confirmation_save_result
from apps.inventory_order_alert.application.dashboard_summary import RowCounts, count_rows
from apps.inventory_order_alert.application.save_alert_settings import parse_alert_settings_payload, save_alert_settings
from apps.inventory_order_alert.application.reconcile_confirmations import lookup_alert_level_for_row
from apps.inventory_order_alert.application.settings_service import MAX_WARNING_MONTHS, get_app_settings
from apps.inventory_order_alert.application.stock_storage import (
    decode_slims_csv_bytes,
    import_slims_csv_text,
)
from apps.inventory_order_alert.application.list_filter import (
    ListFilterParams,
    apply_list_filters,
    build_display_query_string,
    build_filter_options,
    parse_list_filter_params,
)
from apps.inventory_order_alert.application.summary_storage import load_latest_summary
from apps.inventory_order_alert.application.table_display import (
    PAGE_SIZE_OPTIONS,
    SORTABLE_COLUMNS,
    TableDisplayParams,
    apply_table_display,
    parse_table_display_params,
    single_column_sort_specs,
    sort_spec_label,
)
from apps.inventory_order_alert.domain.dev_data_guard import looks_like_test_import
from apps.inventory_order_alert.domain.export_csv import render_export_csv
from apps.inventory_order_alert.domain.alert_rules import build_alert_rule_rows
from apps.inventory_order_alert.domain.row_display import row_alert_class
from apps.inventory_order_alert.application.confirmation import confirmation_status_key
from apps.inventory_order_alert.application.memo_history import (
    add_confirmation_memo,
    list_confirmation_memos,
    memo_entry_to_dict,
    parse_memo_entry_payload,
)
from apps.inventory_order_alert.application.user_display import resolve_user_display_names
from apps.inventory_order_alert.application.save_confirmation import parse_confirmation_payload, save_confirmation
from apps.inventory_order_alert.models import ConfirmationStatus, InventoryOrderAlertConfirmation
from apps.portal.favorites import is_menu_favorited


def _is_stock_stale(stock_as_of_date, stock_stale_days: int) -> bool:
    if stock_as_of_date is None:
        return False
    return (timezone.localdate() - stock_as_of_date).days > stock_stale_days


def _query_params(request: HttpRequest) -> dict[str, str]:
    return {key: values[-1] for key, values in request.GET.lists() if values}


def _rows_for_template(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    enriched: list[dict[str, object]] = []
    for row in rows:
        copied = dict(row)
        copied["alert_row_class"] = row_alert_class(row)
        copied["confirmation_status_key"] = confirmation_status_key(row)
        enriched.append(copied)
    return enriched


@login_required
def list_page(request: HttpRequest) -> HttpResponse:
    app_settings = get_app_settings()
    error_message = ""
    import_message = ""
    summary = load_latest_summary()
    stock_info = summary.stock_info if summary else None
    stock_as_of_label = stock_info.stock_as_of_label if stock_info else ""

    if request.method == "POST" and request.FILES.get("slims_csv"):
        uploaded = request.FILES["slims_csv"]
        try:
            stock_info = import_slims_csv_text(
                decode_slims_csv_bytes(uploaded.read()),
                user=request.user,
                file_name=uploaded.name,
            )
            summary = load_latest_summary()
            stock_as_of_label = stock_info.stock_as_of_label
            if stock_info.aggregation_error:
                error_message = f"集計に失敗しました: {stock_info.aggregation_error}"
            else:
                import_message = (
                    f"SLIMS 在庫 CSV を取り込み、{stock_info.summary_row_count} 件を集計しました"
                    f"（{stock_info.stock_as_of_label}）。"
                )
                if stock_info.confirmation_reset_count:
                    import_message += (
                        f" {stock_info.confirmation_reset_count} 件の確認状態を未確認に戻しました"
                        f"（アラート悪化）。"
                    )
        except ValueError as exc:
            error_message = str(exc)

    all_rows: list[dict[str, object]] = summary.rows if summary else []
    if summary and summary.aggregation_error and not import_message:
        error_message = error_message or f"集計に失敗しました: {summary.aggregation_error}"

    summary_total = len(all_rows)
    filter_options = build_filter_options(all_rows)
    list_filter = parse_list_filter_params(_query_params(request), filter_options)
    filtered_rows = apply_list_filters(all_rows, list_filter)
    counts = count_rows(filtered_rows) if filtered_rows else RowCounts()
    table_params = parse_table_display_params(_query_params(request))
    has_list_data = bool(summary and summary.has_summary and not summary.aggregation_error)
    paginated = apply_table_display(filtered_rows, table_params) if has_list_data else None
    sort_index_map = {spec.column: index + 1 for index, spec in enumerate(table_params.sort_specs)}
    table_headers = [
        {
            "key": column,
            "label": label,
            "sorted": column in sort_index_map,
            "sort_index": sort_index_map.get(column),
            "direction": next(spec.direction for spec in table_params.sort_specs if spec.column == column)
            if column in sort_index_map
            else "",
            "href": "?" + build_display_query_string(
                table_params=table_params,
                filter_params=list_filter,
                page=1,
                sort_specs=single_column_sort_specs(table_params, column),
            ),
        }
        for column, label in SORTABLE_COLUMNS
    ]
    prev_href = ""
    next_href = ""
    if paginated:
        if paginated.has_previous:
            prev_href = "?" + build_display_query_string(
                table_params=table_params,
                filter_params=list_filter,
                page=paginated.page - 1,
            )
        if paginated.has_next:
            next_href = "?" + build_display_query_string(
                table_params=table_params,
                filter_params=list_filter,
                page=paginated.page + 1,
            )

    return render(
        request,
        "inventory_order_alert/list.html",
        {
            "rows": _rows_for_template(paginated.rows) if paginated else [],
            "paginated": paginated,
            "table_params": table_params,
            "sort_spec_labels": [sort_spec_label(spec) for spec in table_params.sort_specs],
            "list_filter": list_filter,
            "filter_options": filter_options,
            "summary_total": summary_total,
            "filtered_total": len(filtered_rows),
            "table_headers": table_headers,
            "page_size_options": PAGE_SIZE_OPTIONS,
            "prev_href": prev_href,
            "next_href": next_href,
            "counts": counts,
            "error_message": error_message,
            "import_message": import_message,
            "stock_as_of_label": stock_as_of_label,
            "stock_import_info": stock_info,
            "has_slims_stock": bool(stock_info and stock_info.has_data),
            "has_summary": bool(summary and summary.has_summary and not summary.aggregation_error),
            "has_list_data": has_list_data,
            "stock_stale": _is_stock_stale(
                stock_info.stock_as_of_date if stock_info else None,
                app_settings.stock_stale_days,
            ),
            "is_inventory_order_alert_favorite": is_menu_favorited(request.user, "inventory-order-alert"),
            "confirmation_status_choices": ConfirmationStatus.choices,
            "alert_rule_rows": build_alert_rule_rows(
                warning_shipment_months=app_settings.warning_shipment_months,
                warning_incoming_months=app_settings.warning_incoming_months,
            ),
            "warning_shipment_months": app_settings.warning_shipment_months,
            "warning_incoming_months": app_settings.warning_incoming_months,
            "warning_month_options": list(range(1, MAX_WARNING_MONTHS + 1)),
            "can_reset_confirmations": InventoryOrderAlertConfirmation.objects.filter(
                status__in=(ConfirmationStatus.IN_PROGRESS, ConfirmationStatus.CONFIRMED),
            ).exists(),
            "test_data_warning": looks_like_test_import(
                stock_info.file_name if stock_info else "",
                all_rows,
            ),
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
        input_data = parse_confirmation_payload(payload)
        summary = load_latest_summary()
        alert_level = lookup_alert_level_for_row(
            summary.rows if summary else [],
            cust_code=input_data.cust_code,
            item_cd=input_data.item_cd,
        )
        save_confirmation(
            input_data,
            confirmed_by=request.user.username,
            alert_level=alert_level,
        )
        filter_params = ListFilterParams(
            cust_code=str(payload.get("custCodeFilter") or "").strip(),
            cust_chrg_psn_cd=str(payload.get("custChrgPsnCdFilter") or "").strip(),
        )
        result = build_confirmation_save_result(input_data, filter_params=filter_params)
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)

    return JsonResponse(result)


@login_required
def api_confirmation_memos(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        cust_code = request.GET.get("custCode", "").strip()
        item_cd = request.GET.get("itemCd", "").strip()
        if not cust_code or not item_cd:
            return JsonResponse({"ok": False, "message": "custCode と itemCd は必須です。"}, status=400)
        return JsonResponse(
            {
                "ok": True,
                "memos": list_confirmation_memos(cust_code=cust_code, item_cd=item_cd),
            }
        )

    if request.method != "POST":
        return JsonResponse({"ok": False, "message": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "message": "JSON の形式が不正です。"}, status=400)

    try:
        input_data = parse_memo_entry_payload(payload)
        entry = add_confirmation_memo(input_data, created_by=request.user.username)
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)

    author_names = resolve_user_display_names({request.user.username})
    return JsonResponse(
        {"ok": True, "memo": memo_entry_to_dict(entry, author_names=author_names)},
    )


@login_required
@require_http_methods(["POST"])
def api_reset_confirmations(request: HttpRequest) -> JsonResponse:
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "message": "JSON の形式が不正です。"}, status=400)

    filter_params = ListFilterParams(
        cust_code=str(payload.get("custCodeFilter") or "").strip(),
        cust_chrg_psn_cd=str(payload.get("custChrgPsnCdFilter") or "").strip(),
    )
    result = build_confirmation_reset_result(filter_params=filter_params)
    return JsonResponse(result)


@login_required
@require_http_methods(["PUT"])
def api_save_alert_settings(request: HttpRequest) -> JsonResponse:
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "message": "JSON の形式が不正です。"}, status=400)

    try:
        input_data = parse_alert_settings_payload(payload)
        save_alert_settings(input_data, updated_by=request.user)
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)

    return JsonResponse({"ok": True})


@login_required
def export_csv(request: HttpRequest) -> HttpResponse:
    summary = load_latest_summary()
    if summary is None or summary.aggregation_error:
        return HttpResponse("集計データがありません。SLIMS 在庫 CSV を取り込んでください。", status=404)

    timestamp = timezone.localtime().strftime("%Y%m%d%H%M%S")
    response = HttpResponse(render_export_csv(summary.rows), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="inventory_order_alert_{timestamp}.csv"'
    return response
