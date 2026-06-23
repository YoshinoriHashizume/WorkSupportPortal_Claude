from __future__ import annotations

import base64
import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_http_methods

from apps.portal.favorites import is_menu_favorited, is_portal_admin, menu_title, receipt_comparison_menu_key
from apps.gonenkukumi.infrastructure.oracle.client import OracleNotConfiguredError, OracleQueryError

from .domain.comparison import ComparisonRow, compare_receipts
from .domain.file_parser import parse_receipt_file
from .infrastructure.oracle.client import fetch_mari_rows
from .infrastructure.oracle.customers import list_receipt_customers, lookup_receipt_customer_name
from .infrastructure.oracle.vendors import (
    VENDOR_CODE_DIGIT_LENGTH,
    list_receipt_vendors,
    lookup_receipt_vendor_name,
)
from .models import (
    FinishedProductReceiptSupplier,
    ReceiptComparisonType,
    ReceiptFlag,
    SuppliedPartsReceiptSupplier,
    SuppliedPartsSubcontractor,
)
from .services.comparison_sort import (
    comparison_sort_headers,
    default_sort_params,
    normalize_sort_direction,
    normalize_sort_key,
    resolve_sort_params,
    sort_display_rows,
)
from .services.pending_comparison import (
    clear_pending_comparison,
    get_pending_comparison,
    pending_display_rows,
    pending_matches,
    pending_rows_for_register,
    saved_display_rows,
    store_pending_comparison,
)
from .services.supplier_codes import mari_vendor_codes_for_supplier, vendor_match_codes_for_supplier
from .type_registry import (
    comparison_result_model,
    customer_digit_length,
    file_import_model,
    is_finished_product,
    list_suppliers,
    list_suppliers_for_settings,
    settings_exclusion_label,
    settings_target_label,
    receiving_setting_model,
    supplier_model,
)


RESULT_COLUMNS = [
    "結果",
    "品目番号(MARI)",
    "売上計上日(MARI)",
    "売上実績数量(MARI)",
    "得意先指定納品場所コード",
    "品番(取引先)",
    "納入月日(取引先)",
    "納入数(取引先)",
    "キャンセル数(取引先)",
    "取引先名",
    "備考",
]

COMPARISON_TYPE_SLUGS = {
    "finished-product": ReceiptComparisonType.FINISHED_PRODUCT,
    "supplied-parts": ReceiptComparisonType.SUPPLIED_PARTS,
}
COMPARISON_SLUG_BY_TYPE = {value: slug for slug, value in COMPARISON_TYPE_SLUGS.items()}
COMPARISON_TYPE_PAGE_LABELS = {
    ReceiptComparisonType.FINISHED_PRODUCT: "完成品",
    ReceiptComparisonType.SUPPLIED_PARTS: "支給品",
}


def comparison_type_page_label(comparison_type: str) -> str:
    return COMPARISON_TYPE_PAGE_LABELS[comparison_type]


def comparison_export_filename(comparison_type: str, at: datetime | None = None) -> str:
    label = comparison_type_page_label(comparison_type)
    moment = timezone.localtime(at) if at is not None else timezone.localtime()
    return f"検収書比較結果({label})_{moment:%Y%m%d%H%M%S}.csv"


def comparison_type_from_slug(slug: str) -> str:
    comparison_type = COMPARISON_TYPE_SLUGS.get(slug)
    if comparison_type is None:
        raise Http404
    return comparison_type


def comparison_type_slug_from_request(request: HttpRequest) -> str | None:
    slug = (request.POST.get("type") or request.GET.get("type") or "").strip()
    return slug or None


def append_query(url: str, query: str) -> str:
    if not query:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{query}"


@login_required
@require_http_methods(["GET", "POST"])
def comparison_page(request: HttpRequest) -> HttpResponse:
    type_slug = comparison_type_slug_from_request(request)
    if type_slug is None:
        return redirect(append_query(f"{reverse('receipt_comparison:comparison')}?type=finished-product", request.GET.urlencode()))
    comparison_type = comparison_type_from_slug(type_slug)
    supplier_id = request.POST.get("supplier_id") or request.GET.get("supplier_id") or ""
    start_date = parse_date(request.POST.get("start_date") or request.GET.get("start_date")) or date.today()
    end_date = parse_date(request.POST.get("end_date") or request.GET.get("end_date")) or start_date
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    supplier = None
    if supplier_id:
        supplier = get_object_or_404(supplier_model(comparison_type), id=supplier_id)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "compare" and supplier:
            return compare_only(request, type_slug, comparison_type, supplier, start_date, end_date)
        if action == "register" and supplier:
            return register_pending_comparison(request, type_slug, comparison_type, supplier, start_date, end_date)
        if action == "update" and supplier:
            update_existing_results(request, comparison_type)
            return redirect(
                comparison_url(
                    comparison_type,
                    supplier.id,
                    start_date,
                    end_date,
                    display=1,
                    sort_key=request.POST.get("sort"),
                    sort_direction=request.POST.get("dir"),
                )
            )

    reset_sort = (
        request.method == "GET"
        and (request.GET.get("display") == "1" or request.GET.get("compared") == "1")
        and not request.GET.get("sort")
    )
    sort_key, sort_direction = resolve_sort_params(
        sort_key=request.GET.get("sort"),
        sort_direction=request.GET.get("dir"),
        reset_to_default=reset_sort,
    )
    if supplier and request.method == "GET" and request.GET.get("display") == "1":
        clear_pending_comparison(request)

    rows, has_pending = rows_for_comparison_page(
        request,
        comparison_type,
        supplier,
        start_date,
        end_date,
        sort_key,
        sort_direction,
    )
    results_panel_active = is_results_panel_active(request, supplier, has_pending)
    return render_comparison_page(
        request,
        type_slug,
        comparison_type,
        supplier,
        start_date,
        end_date,
        rows,
        has_pending=has_pending,
        results_panel_active=results_panel_active,
        sort_key=sort_key,
        sort_direction=sort_direction,
    )


def is_results_panel_active(
    request: HttpRequest,
    supplier: FinishedProductReceiptSupplier | SuppliedPartsReceiptSupplier | None,
    has_pending: bool,
) -> bool:
    if supplier is None:
        return False
    if has_pending:
        return True
    if request.method == "GET":
        return request.GET.get("display") == "1" or request.GET.get("compared") == "1"
    return request.POST.get("action") == "compare"


def rows_for_comparison_page(
    request: HttpRequest,
    comparison_type: str,
    supplier: FinishedProductReceiptSupplier | SuppliedPartsReceiptSupplier | None,
    start_date: date,
    end_date: date,
    sort_key: str,
    sort_direction: str,
) -> tuple[list[Any], bool]:
    if supplier is None:
        return [], False

    pending = get_pending_comparison(request)
    if pending_matches(pending, comparison_type, supplier.id, start_date, end_date):
        rows = sort_display_rows(pending_display_rows(pending), sort_key, sort_direction)
        return rows, True

    saved_rows = existing_rows_for_display(comparison_type, supplier, start_date, end_date)
    rows = sort_display_rows(saved_display_rows(saved_rows), sort_key, sort_direction)
    return rows, False


@login_required
def legacy_comparison_redirect(request: HttpRequest, comparison_slug: str) -> HttpResponse:
    comparison_type_from_slug(comparison_slug)
    return redirect(append_query(f"{reverse('receipt_comparison:comparison')}?type={comparison_slug}", request.GET.urlencode()))


@login_required
def legacy_export_redirect(request: HttpRequest, comparison_slug: str) -> HttpResponse:
    comparison_type_from_slug(comparison_slug)
    return redirect(append_query(f"{reverse('receipt_comparison:export')}?type={comparison_slug}", request.GET.urlencode()))


@login_required
def legacy_settings_redirect(request: HttpRequest, comparison_slug: str) -> HttpResponse:
    comparison_type_from_slug(comparison_slug)
    return redirect(append_query(f"{reverse('receipt_comparison:settings')}?type={comparison_slug}", request.GET.urlencode()))


def compare_only(
    request: HttpRequest,
    type_slug: str,
    comparison_type: str,
    supplier: FinishedProductReceiptSupplier | SuppliedPartsReceiptSupplier,
    start_date: date,
    end_date: date,
) -> HttpResponse:
    upload = request.FILES.get("receipt_file")
    if upload is None:
        messages.error(request, "受領書データを選択してください。")
        sort_key = normalize_sort_key(request.POST.get("sort") or request.GET.get("sort") or "")
        sort_direction = normalize_sort_direction(request.POST.get("dir") or request.GET.get("dir") or "asc")
        rows, has_pending = rows_for_comparison_page(
            request, comparison_type, supplier, start_date, end_date, sort_key, sort_direction
        )
        return render_comparison_page(
            request,
            type_slug,
            comparison_type,
            supplier,
            start_date,
            end_date,
            rows,
            has_pending=has_pending,
            results_panel_active=True,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )

    try:
        content = upload.read()
        receiving_places = receiving_places_for_supplier(supplier)
        match_codes = subcontractor_codes(supplier)
        if comparison_type == ReceiptComparisonType.SUPPLIED_PARTS and not match_codes:
            messages.warning(
                request,
                "子取引先が未登録です。設定画面で購買取引先コードを追加してください。",
            )
        parent_customer_code = supplier.customer_code if isinstance(supplier, SuppliedPartsReceiptSupplier) else ""
        receipt_rows = parse_receipt_file(
            comparison_type=comparison_type,
            file_name=upload.name,
            content=content,
            subcontractor_codes=match_codes,
            receiving_places=receiving_places,
            exclusion=supplier.exclusion,
            parent_customer_code=parent_customer_code,
        )
        mari_rows = fetch_mari_rows(
            comparison_type=comparison_type,
            supplier=supplier,
            start_date=start_date,
            end_date=end_date,
            receiving_places=receiving_places,
        )
        rows = compare_receipts(
            mari_rows,
            receipt_rows,
            existing_rows_for_comparison(comparison_type, supplier, start_date, end_date),
            supplied_parts=comparison_type == ReceiptComparisonType.SUPPLIED_PARTS,
        )
        if receipt_rows and mari_rows and not any(row.supplier_item_cd for row in rows if row.mari_item_cd):
            messages.warning(
                request,
                "受領ファイルは読み取れましたが、MARIデータと一致する行がありませんでした。品番・日付・数量を確認してください。",
            )
        elif not receipt_rows and content.strip():
            messages.warning(
                request,
                "取込ファイルから比較対象行を読み取れませんでした。子取引先・品番・品番設定を確認してください。",
            )
        store_pending_comparison(
            request,
            comparison_type=comparison_type,
            supplier_id=supplier.id,
            start_date=start_date,
            end_date=end_date,
            file_name=upload.name,
            file_content=content,
            rows=rows,
        )
    except (ValueError, OracleNotConfiguredError, OracleQueryError) as exc:
        messages.error(request, str(exc))
        sort_key = normalize_sort_key(request.POST.get("sort") or "")
        sort_direction = normalize_sort_direction(request.POST.get("dir") or "asc")
        rows, has_pending = rows_for_comparison_page(
            request, comparison_type, supplier, start_date, end_date, sort_key, sort_direction
        )
        return render_comparison_page(
            request,
            type_slug,
            comparison_type,
            supplier,
            start_date,
            end_date,
            rows,
            has_pending=has_pending,
            results_panel_active=True,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )

    return redirect(
        comparison_url(
            comparison_type,
            supplier.id,
            start_date,
            end_date,
            compared=1,
            sort_key=default_sort_params()[0],
            sort_direction=default_sort_params()[1],
        )
    )


def register_pending_comparison(
    request: HttpRequest,
    type_slug: str,
    comparison_type: str,
    supplier: FinishedProductReceiptSupplier | SuppliedPartsReceiptSupplier,
    start_date: date,
    end_date: date,
) -> HttpResponse:
    pending = get_pending_comparison(request)
    if not pending_matches(pending, comparison_type, supplier.id, start_date, end_date):
        messages.error(request, "登録する比較結果がありません。先に比較を実行してください。")
        return redirect(comparison_url(comparison_type, supplier.id, start_date, end_date))

    try:
        content = base64.b64decode(str(pending.get("file_content_b64") or ""))
        rows = pending_rows_for_register(request, pending)
        file_import = save_upload_file(
            comparison_type,
            supplier,
            str(pending.get("file_name") or "receipt.dat"),
            content,
            end_date,
            request.user,
        )
        save_comparison_rows(comparison_type, supplier, file_import, rows, request.user)
    except (ValueError, OracleNotConfiguredError, OracleQueryError) as exc:
        messages.error(request, str(exc))
        return redirect(
            comparison_url(
                comparison_type,
                supplier.id,
                start_date,
                end_date,
                compared=1,
                sort_key=request.POST.get("sort"),
                sort_direction=request.POST.get("dir"),
            )
        )

    clear_pending_comparison(request)
    return redirect(
        comparison_url(
            comparison_type,
            supplier.id,
            start_date,
            end_date,
            display=1,
            sort_key=default_sort_params()[0],
            sort_direction=default_sort_params()[1],
        )
    )


def render_comparison_page(
    request: HttpRequest,
    type_slug: str,
    comparison_type: str,
    supplier: FinishedProductReceiptSupplier | SuppliedPartsReceiptSupplier | None,
    start_date: date,
    end_date: date,
    rows: list[Any],
    *,
    has_pending: bool = False,
    results_panel_active: bool = False,
    sort_key: str = "receipt_flag",
    sort_direction: str = "asc",
) -> HttpResponse:
    favorite_menu_key = receipt_comparison_menu_key(comparison_type)
    return render(
        request,
        "receipt_comparison/comparison.html",
        {
            "type_slug": type_slug,
            "comparison_type": comparison_type,
            "comparison_type_page_label": comparison_type_page_label(comparison_type),
            "favorite_menu_key": favorite_menu_key,
            "favorite_menu_title": menu_title(favorite_menu_key),
            "is_comparison_favorite": is_menu_favorited(request.user, favorite_menu_key),
            "show_settings": is_portal_admin(request.user),
            "suppliers": list_suppliers(comparison_type),
            "supplier": supplier,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "rows": rows,
            "has_pending": has_pending,
            "results_panel_active": results_panel_active,
            "receipt_file_accept": ".csv" if is_finished_product(comparison_type) else ".txt",
            "flag_choices": ReceiptFlag.choices,
            "show_cancel_qty": is_finished_product(comparison_type),
            "show_supplier_name": not is_finished_product(comparison_type),
            "sort_key": normalize_sort_key(sort_key),
            "sort_direction": normalize_sort_direction(sort_direction),
            "sort_headers": comparison_sort_links(
                comparison_type,
                supplier.id if supplier else None,
                start_date,
                end_date,
                sort_key,
                sort_direction,
            ),
            "comparison_query": comparison_query(
                comparison_type,
                supplier.id if supplier else None,
                start_date,
                end_date,
            ),
        },
    )


@login_required
def export_csv(request: HttpRequest) -> HttpResponse:
    type_slug = comparison_type_slug_from_request(request)
    if type_slug is None:
        raise Http404
    comparison_type = comparison_type_from_slug(type_slug)
    supplier = get_object_or_404(supplier_model(comparison_type), id=request.GET.get("supplier_id"))
    start_date = parse_date(request.GET.get("start_date")) or date.today()
    end_date = parse_date(request.GET.get("end_date")) or start_date
    sort_key = normalize_sort_key(request.GET.get("sort") or "")
    sort_direction = normalize_sort_direction(request.GET.get("dir") or "asc")
    rows, _has_pending = rows_for_comparison_page(
        request,
        comparison_type,
        supplier,
        start_date,
        end_date,
        sort_key,
        sort_direction,
    )

    response = HttpResponse(content_type="text/csv; charset=cp932")
    response["Content-Disposition"] = content_disposition_header(
        as_attachment=True,
        filename=comparison_export_filename(comparison_type),
    )
    writer = csv.writer(response)
    writer.writerow(RESULT_COLUMNS)
    for row in rows:
        writer.writerow(
            [
                row.flag_label,
                row.mari_item_cd,
                row.mari_date,
                row.mari_qty,
                row.delivery_place,
                row.supplier_item_cd,
                row.supplier_delivery_month_day,
                row.supplier_qty,
                row.supplier_cancel_qty,
                row.supplier_name,
                row.remarks,
            ]
        )
    return response


@login_required
@require_http_methods(["GET", "POST"])
def settings_page(request: HttpRequest) -> HttpResponse:
    if not is_portal_admin(request.user):
        return HttpResponse("権限がありません。", status=403)
    type_slug = comparison_type_slug_from_request(request)
    if type_slug is None:
        return redirect(f"{reverse('receipt_comparison:settings')}?type=finished-product")
    comparison_type = comparison_type_from_slug(type_slug)
    if request.method == "POST":
        action = request.POST.get("action")
        handle_settings_post(request, comparison_type)
        supplier_id = request.POST.get("supplier_id")
        if action == "delete_supplier":
            supplier_id = None
        return redirect(settings_redirect_url(type_slug, supplier_id))

    customer_choices, choice_error = receipt_customer_choices(comparison_type)
    vendor_choices: list[dict[str, str]] = []
    vendor_choice_error = ""
    if comparison_type == ReceiptComparisonType.SUPPLIED_PARTS:
        vendor_choices, vendor_choice_error = receipt_vendor_choices()
    suppliers = list(list_suppliers_for_settings(comparison_type))
    supplier_rows = [{"supplier": supplier} for supplier in suppliers]
    open_supplier_id = (request.GET.get("supplier_id") or "").strip()
    combined_choice_error = " / ".join(part for part in (choice_error, vendor_choice_error) if part)
    return render(
        request,
        "receipt_comparison/settings.html",
        {
            "type_slug": type_slug,
            "comparison_type": comparison_type,
            "comparison_type_page_label": comparison_type_page_label(comparison_type),
            "customer_choices": customer_choices,
            "choice_error": combined_choice_error,
            "vendor_choices": vendor_choices,
            "suppliers": suppliers,
            "supplier_rows": supplier_rows,
            "open_supplier_id": open_supplier_id,
            "settings_target_label": settings_target_label(comparison_type),
            "settings_exclusion_label": settings_exclusion_label(comparison_type),
        },
    )


def settings_redirect_url(type_slug: str, supplier_id: object = None) -> str:
    url = f"{reverse('receipt_comparison:settings')}?type={type_slug}"
    if supplier_id:
        url += f"&supplier_id={supplier_id}"
    return url


def handle_settings_post(request: HttpRequest, comparison_type: str) -> None:
    action = request.POST.get("action")
    if is_finished_product(comparison_type):
        handle_finished_product_settings_post(request, action)
        return
    handle_supplied_parts_settings_post(request, action)


def handle_finished_product_settings_post(request: HttpRequest, action: str | None) -> None:
    if action == "add_supplier":
        customer_code = (request.POST.get("customer_code") or "").strip()
        if not is_fixed_digit_code(customer_code, 3):
            messages.error(request, "得意先は3桁で選択してください。")
            return
        direct_delivery_customer_code = (request.POST.get("direct_delivery_customer_code") or "").strip()
        FinishedProductReceiptSupplier.objects.update_or_create(
            customer_code=customer_code,
            defaults={
                "name": customer_name_for_code(customer_code, comparison_type=ReceiptComparisonType.FINISHED_PRODUCT),
                "direct_delivery_customer_code": direct_delivery_customer_code,
                "exclusion": request.POST.get("exclusion") == "on",
            },
        )
        messages.success(request, "得意先を保存しました。")
        return

    supplier = get_object_or_404(FinishedProductReceiptSupplier, id=request.POST.get("supplier_id"))
    if action == "update_supplier":
        posted_customer_code = (request.POST.get("customer_code") or "").strip()
        if posted_customer_code and posted_customer_code != supplier.customer_code:
            messages.error(request, "得意先コードは編集できません。変更する場合は削除してから再度追加してください。")
            return
        supplier.direct_delivery_customer_code = (request.POST.get("direct_delivery_customer_code") or "").strip()
        supplier.exclusion = request.POST.get("exclusion") == "on"
        supplier.save(
            update_fields=[
                "direct_delivery_customer_code",
                "exclusion",
                "updated_at",
            ]
        )
        messages.success(request, "設定を更新しました。")
    elif action in {"add_receiving", "delete_receiving", "delete_supplier"}:
        handle_supplier_child_settings_post(request, action, supplier, ReceiptComparisonType.FINISHED_PRODUCT)


def handle_supplied_parts_settings_post(request: HttpRequest, action: str | None) -> None:
    digit_length = customer_digit_length(ReceiptComparisonType.SUPPLIED_PARTS)
    if action == "add_supplier":
        customer_code = (request.POST.get("customer_code") or "").strip()
        if not is_fixed_digit_code(customer_code, digit_length):
            messages.error(request, "得意先は3桁で選択してください。")
            return
        SuppliedPartsReceiptSupplier.objects.update_or_create(
            customer_code=customer_code,
            defaults={
                "name": customer_name_for_code(customer_code, comparison_type=ReceiptComparisonType.SUPPLIED_PARTS),
                "exclusion": request.POST.get("exclusion") == "on",
            },
        )
        messages.success(request, "得意先を保存しました。子取引先（購買取引先コード）を登録してください。")
        return

    supplier = get_object_or_404(SuppliedPartsReceiptSupplier, id=request.POST.get("supplier_id"))
    if action == "update_supplier":
        posted_customer_code = (request.POST.get("customer_code") or "").strip()
        if posted_customer_code and posted_customer_code != supplier.customer_code:
            messages.error(request, "得意先コードは編集できません。変更する場合は削除してから再度追加してください。")
            return
        supplier.exclusion = request.POST.get("exclusion") == "on"
        supplier.save(update_fields=["exclusion", "updated_at"])
        messages.success(request, "設定を更新しました。")
    elif action in {"add_subcontractor", "delete_subcontractor"}:
        handle_supplied_parts_subcontractor_post(request, action, supplier)
    elif action in {"add_receiving", "delete_receiving", "delete_supplier"}:
        handle_supplier_child_settings_post(request, action, supplier, ReceiptComparisonType.SUPPLIED_PARTS)


def handle_supplied_parts_subcontractor_post(
    request: HttpRequest,
    action: str,
    supplier: SuppliedPartsReceiptSupplier,
) -> None:
    if action == "add_subcontractor":
        vendor_code = (request.POST.get("vendor_code") or "").strip()
        if not is_fixed_digit_code(vendor_code, VENDOR_CODE_DIGIT_LENGTH):
            messages.error(request, "子取引先は4桁の購買取引先コードで選択してください。")
            return
        vendor_name = lookup_receipt_vendor_name(vendor_code)
        _, created = SuppliedPartsSubcontractor.objects.get_or_create(
            supplier=supplier,
            vendor_code=vendor_code,
            defaults={"vendor_name": vendor_name},
        )
        if created:
            messages.success(request, "子取引先を追加しました。")
        else:
            messages.info(request, "同じ購買取引先コードは既に登録されています。")
        return

    subcontractor = get_object_or_404(
        SuppliedPartsSubcontractor,
        id=request.POST.get("subcontractor_id"),
        supplier=supplier,
    )
    subcontractor.delete()
    messages.success(request, "子取引先を削除しました。")


def handle_supplier_child_settings_post(
    request: HttpRequest,
    action: str,
    supplier: FinishedProductReceiptSupplier | SuppliedPartsReceiptSupplier,
    comparison_type: str,
) -> None:
    if action == "add_receiving":
        save_receiving_setting(request, supplier, comparison_type)
    elif action == "delete_receiving":
        delete_receiving_setting(request, supplier, comparison_type)
    elif action == "delete_supplier":
        delete_receipt_supplier(request, comparison_type, supplier)


def save_receiving_setting(
    request: HttpRequest,
    supplier: FinishedProductReceiptSupplier | SuppliedPartsReceiptSupplier,
    comparison_type: str,
) -> None:
    delivery_place = (request.POST.get("delivery_place") or "").strip()
    if not delivery_place:
        return
    receiving_setting_model(comparison_type).objects.update_or_create(
        supplier=supplier,
        delivery_place=delivery_place,
        defaults={
            "updated_by": request.user,
            "created_by": request.user,
        },
    )
    messages.success(request, f"{settings_target_label(comparison_type)}を保存しました。")


def delete_receiving_setting(
    request: HttpRequest,
    supplier: FinishedProductReceiptSupplier | SuppliedPartsReceiptSupplier,
    comparison_type: str,
) -> None:
    setting = get_object_or_404(
        receiving_setting_model(comparison_type),
        id=request.POST.get("setting_id"),
        supplier=supplier,
    )
    setting.delete()
    messages.success(request, f"{settings_target_label(comparison_type)}を削除しました。")


def delete_receipt_supplier(
    request: HttpRequest,
    comparison_type: str,
    supplier: FinishedProductReceiptSupplier | SuppliedPartsReceiptSupplier,
) -> None:
    with transaction.atomic():
        comparison_result_model(comparison_type).objects.filter(supplier=supplier).delete()
        file_import_model(comparison_type).objects.filter(supplier=supplier).delete()
        supplier.delete()
    messages.success(request, "得意先を削除しました。")


def receipt_customer_choices(comparison_type: str) -> tuple[list[dict[str, str]], str]:
    errors = []
    digit_length = customer_digit_length(comparison_type)
    try:
        customers = [
            row
            for row in list_receipt_customers(digit_length=digit_length)
            if is_fixed_digit_code(row["custCode"], digit_length)
        ]
    except (OracleNotConfiguredError, OracleQueryError) as exc:
        customers = []
        errors.append(str(exc))
    return customers, " / ".join(errors)


def receipt_vendor_choices() -> tuple[list[dict[str, str]], str]:
    errors: list[str] = []
    try:
        vendors = [
            row
            for row in list_receipt_vendors()
            if is_fixed_digit_code(row.get("vendorCode"), VENDOR_CODE_DIGIT_LENGTH)
        ]
    except (OracleNotConfiguredError, OracleQueryError) as exc:
        vendors = []
        errors.append(str(exc))
    return vendors, " / ".join(errors)


def is_fixed_digit_code(value: object, length: int) -> bool:
    text = str(value or "").strip()
    return len(text) == length and text.isdigit()


def customer_name_for_code(customer_code: str, *, comparison_type: str | None = None, fallback: object = "") -> str:
    if not customer_code:
        return str(fallback or "").strip()
    try:
        name = lookup_receipt_customer_name(customer_code)
    except (OracleNotConfiguredError, OracleQueryError):
        name = None
    if name:
        return name
    return str(fallback or "").strip() or customer_code


def parse_date(value: object) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def comparison_url(
    comparison_type: str,
    supplier_id: int,
    start_date: date,
    end_date: date,
    *,
    display: int | None = None,
    compared: int | None = None,
    sort_key: str | None = None,
    sort_direction: str | None = None,
) -> str:
    type_slug = COMPARISON_SLUG_BY_TYPE[comparison_type]
    query = comparison_query(
        comparison_type,
        supplier_id,
        start_date,
        end_date,
        display=display,
        compared=compared,
        sort_key=sort_key,
        sort_direction=sort_direction,
    )
    return f"{reverse('receipt_comparison:comparison')}?{query}"


def comparison_query(
    comparison_type: str,
    supplier_id: int | None,
    start_date: date,
    end_date: date,
    *,
    display: int | None = None,
    compared: int | None = None,
    sort_key: str | None = None,
    sort_direction: str | None = None,
) -> str:
    type_slug = COMPARISON_SLUG_BY_TYPE[comparison_type]
    parts = [
        f"type={type_slug}",
        f"start_date={start_date.isoformat()}",
        f"end_date={end_date.isoformat()}",
    ]
    if supplier_id:
        parts.append(f"supplier_id={supplier_id}")
    if display == 1:
        parts.append("display=1")
    if compared == 1:
        parts.append("compared=1")
    active_sort_key = normalize_sort_key(sort_key or "")
    active_sort_direction = normalize_sort_direction(sort_direction or "asc")
    parts.append(f"sort={active_sort_key}")
    parts.append(f"dir={active_sort_direction}")
    return "&".join(parts)


def comparison_sort_links(
    comparison_type: str,
    supplier_id: int | None,
    start_date: date,
    end_date: date,
    sort_key: str,
    sort_direction: str,
    *,
    display: int | None = None,
    compared: int | None = None,
) -> list[dict[str, object]]:
    headers = comparison_sort_headers(sort_key, sort_direction)
    for header in headers:
        header["href"] = (
            f"{reverse('receipt_comparison:comparison')}?"
            f"{comparison_query(comparison_type, supplier_id, start_date, end_date, display=display, compared=compared, sort_key=header['key'], sort_direction=header['sort_direction'])}"
        )
    return headers


def receiving_places_for_supplier(supplier: FinishedProductReceiptSupplier | SuppliedPartsReceiptSupplier) -> list[str]:
    return list(supplier.receiving_settings.values_list("delivery_place", flat=True))


def subcontractor_codes(supplier: FinishedProductReceiptSupplier | SuppliedPartsReceiptSupplier) -> list[str]:
    if isinstance(supplier, FinishedProductReceiptSupplier):
        return []
    return vendor_match_codes_for_supplier(supplier)


def existing_rows_for_display(
    comparison_type: str,
    supplier: FinishedProductReceiptSupplier | SuppliedPartsReceiptSupplier | None,
    start_date: date,
    end_date: date,
) -> list[Any]:
    if supplier is None:
        return []
    result_model = comparison_result_model(comparison_type)
    in_range = result_model.objects.filter(
        supplier=supplier,
        file_import__receipt_date__range=(start_date, end_date),
    )
    carry_over = result_model.objects.filter(
        supplier=supplier,
        file_import__receipt_date__lt=start_date,
    ).exclude(receipt_flag=ReceiptFlag.OK)
    return list((in_range | carry_over).select_related("file_import").order_by("receipt_flag", "mari_item_cd", "supplier_item_cd"))


def existing_rows_for_comparison(
    comparison_type: str,
    supplier: FinishedProductReceiptSupplier | SuppliedPartsReceiptSupplier,
    start_date: date,
    end_date: date,
) -> list[ComparisonRow]:
    return [
        ComparisonRow(
            existing_id=row.id,
            receipt_flag=row.receipt_flag,
            mari_item_cd=row.mari_item_cd,
            mari_date=row.mari_date,
            mari_qty=row.mari_qty,
            delivery_place=row.delivery_place,
            supplier_item_cd=row.supplier_item_cd,
            supplier_delivery_month_day=row.supplier_delivery_month_day,
            supplier_qty=row.supplier_qty,
            supplier_cancel_qty=row.supplier_cancel_qty,
            supplier_name=row.supplier_name,
            remarks=row.remarks,
        )
        for row in existing_rows_for_display(comparison_type, supplier, start_date, end_date)
    ]


def save_upload_file(
    comparison_type: str,
    supplier: FinishedProductReceiptSupplier | SuppliedPartsReceiptSupplier,
    original_name: str,
    content: bytes,
    receipt_date: date,
    user: object,
) -> Any:
    storage = FileSystemStorage(location=Path(settings.BASE_DIR) / "var" / "receipt_uploads")
    stored_name = f"{timezone.localtime():%Y%m%d%H%M%S}_{comparison_type}_{supplier.id}_{Path(original_name).name}"
    storage.save(stored_name, content=io_content(content))
    return file_import_model(comparison_type).objects.create(
        supplier=supplier,
        original_file_name=original_name,
        stored_file_name=stored_name,
        receipt_date=receipt_date,
        imported_by=user,
    )


def io_content(content: bytes):
    from django.core.files.base import ContentFile

    return ContentFile(content)


def save_comparison_rows(
    comparison_type: str,
    supplier: FinishedProductReceiptSupplier | SuppliedPartsReceiptSupplier,
    file_import: Any,
    rows: list[ComparisonRow],
    user: object,
) -> None:
    result_model = comparison_result_model(comparison_type)
    for row in rows:
        values = {
            "supplier": supplier,
            "file_import": file_import,
            "receipt_flag": row.receipt_flag,
            "mari_item_cd": row.mari_item_cd,
            "mari_date": row.mari_date,
            "mari_qty": row.mari_qty,
            "delivery_place": row.delivery_place,
            "supplier_item_cd": row.supplier_item_cd,
            "supplier_delivery_month_day": row.supplier_delivery_month_day,
            "supplier_qty": row.supplier_qty,
            "supplier_cancel_qty": row.supplier_cancel_qty,
            "supplier_name": row.supplier_name,
            "remarks": row.remarks,
            "updated_by": user,
        }
        if row.existing_id:
            result_model.objects.filter(id=row.existing_id, supplier=supplier).update(**values)
        else:
            result_model.objects.create(**values)


def update_existing_results(request: HttpRequest, comparison_type: str) -> None:
    result_model = comparison_result_model(comparison_type)
    for result_id in request.POST.getlist("result_id"):
        result = result_model.objects.get(id=result_id)
        result.receipt_flag = int(request.POST.get(f"receipt_flag_{result_id}", result.receipt_flag))
        result.remarks = request.POST.get(f"remarks_{result_id}", "")
        result.updated_by = request.user
        result.save(update_fields=["receipt_flag", "remarks", "updated_by", "updated_at"])
