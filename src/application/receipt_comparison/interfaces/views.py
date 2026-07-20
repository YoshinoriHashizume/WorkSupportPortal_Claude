from __future__ import annotations

import csv
from datetime import date
from typing import TYPE_CHECKING

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_http_methods

from application.portal.interfaces.favorites import is_menu_favorited, is_portal_admin, menu_title, receipt_comparison_menu_key
from application.receipt_comparison.interfaces.wiring import (
    compare_usecase,
    comparison_page_usecase,
    export_csv_usecase,
    pending_comparison_store,
    register_comparison_usecase,
    settings_page_usecase,
    settings_post_usecase,
    slug_to_comparison_type,
    supplier_model,
    update_results_usecase,
)
from application.receipt_comparison.domain.value_objects.comparison_type import UnknownComparisonTypeError, comparison_type_from_slug
from application.receipt_comparison.domain.value_objects.comparison_urls import append_query, comparison_url_path, parse_date
from application.receipt_comparison.models import ReceiptFlag

if TYPE_CHECKING:
    from application.receipt_comparison.use_cases.compare import FlashMessage
    from application.receipt_comparison.use_cases.comparison_page import ComparisonPageContext


def _post_values(request: HttpRequest) -> dict[str, str]:
    return {key: value for key, value in request.POST.items()}


def _apply_flash_messages(request: HttpRequest, flash_messages: tuple[FlashMessage, ...]) -> None:
    for message in flash_messages:
        level = message.level
        if level == "error":
            messages.error(request, message.text)
        elif level == "warning":
            messages.warning(request, message.text)
        elif level == "info":
            messages.info(request, message.text)
        else:
            messages.success(request, message.text)


def _comparison_page_template_context(request: HttpRequest, context: ComparisonPageContext) -> dict[str, object]:
    favorite_menu_key = receipt_comparison_menu_key(context.comparison_type)
    return {
        "type_slug": context.type_slug,
        "comparison_type": context.comparison_type,
        "comparison_type_page_label": context.comparison_type_page_label,
        "favorite_menu_key": favorite_menu_key,
        "favorite_menu_title": menu_title(favorite_menu_key),
        "is_comparison_favorite": is_menu_favorited(request.user, favorite_menu_key),
        "show_settings": is_portal_admin(request.user),
        "suppliers": context.suppliers,
        "supplier": context.supplier,
        "start_date": context.start_date.isoformat(),
        "end_date": context.end_date.isoformat(),
        "rows": context.rows,
        "has_pending": context.has_pending,
        "results_panel_active": context.results_panel_active,
        "receipt_file_accept": context.receipt_file_accept,
        "flag_choices": ReceiptFlag.choices,
        "show_cancel_qty": context.show_cancel_qty,
        "show_supplier_name": context.show_supplier_name,
        "sort_key": context.sort_key,
        "sort_direction": context.sort_direction,
        "sort_headers": [
            {
                "key": header.key,
                "label": header.label,
                "sort_direction": header.sort_direction,
                "is_sorted": header.is_sorted,
                "href": header.href,
            }
            for header in context.sort_headers
        ],
        "comparison_query": context.comparison_query,
        "search_disclosure_storage_key": f"receipt-comparison-search-{context.type_slug}-v2",
    }


def _comparison_type_slug_from_request(request: HttpRequest) -> str | None:
    slug = (request.POST.get("type") or request.GET.get("type") or "").strip()
    return slug or None


@login_required
@require_http_methods(["GET", "POST"])
def comparison_page(request: HttpRequest) -> HttpResponse:
    page_usecase = comparison_page_usecase()
    type_slug = _comparison_type_slug_from_request(request)
    if type_slug is None:
        return redirect(
            append_query(
                f"{reverse('receipt_comparison:comparison')}?type=finished-product",
                request.GET.urlencode(),
            )
        )
    try:
        comparison_type = comparison_type_from_slug(type_slug)
    except UnknownComparisonTypeError as exc:
        raise Http404 from exc

    supplier_id = request.POST.get("supplier_id") or request.GET.get("supplier_id") or ""
    start_date = parse_date(request.POST.get("start_date") or request.GET.get("start_date")) or date.today()
    end_date = parse_date(request.POST.get("end_date") or request.GET.get("end_date")) or start_date
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    supplier = None
    if supplier_id:
        supplier = get_object_or_404(supplier_model(comparison_type), id=supplier_id)

    pending_store = pending_comparison_store(request)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "compare" and supplier:
            outcome = compare_usecase().execute(
                pending_store,
                type_slug=type_slug,
                comparison_type=comparison_type,
                supplier=supplier,
                start_date=start_date,
                end_date=end_date,
                file_name=request.FILES.get("receipt_file").name if request.FILES.get("receipt_file") else None,
                file_content=request.FILES.get("receipt_file").read() if request.FILES.get("receipt_file") else None,
                sort_key=request.POST.get("sort") or request.GET.get("sort") or "",
                sort_direction=request.POST.get("dir") or request.GET.get("dir") or "asc",
                results_panel_active=True,
            )
            _apply_flash_messages(request, outcome.messages)
            if outcome.redirect_url:
                return redirect(outcome.redirect_url)
            assert outcome.page is not None
            return render(
                request,
                "receipt_comparison/comparison.html",
                _comparison_page_template_context(request, outcome.page),
            )
        if action == "register" and supplier:
            outcome = register_comparison_usecase().execute(
                pending_store,
                comparison_type=comparison_type,
                supplier=supplier,
                start_date=start_date,
                end_date=end_date,
                post_values=_post_values(request),
                user_id=request.user.id,
                sort_key=request.POST.get("sort"),
                sort_direction=request.POST.get("dir"),
            )
            _apply_flash_messages(request, outcome.messages)
            return redirect(outcome.redirect_url)
        if action == "update" and supplier:
            update_results_usecase().execute(
                comparison_type=comparison_type,
                result_ids=request.POST.getlist("result_id"),
                post_values=_post_values(request),
                user_id=request.user.id,
            )
            return redirect(
                comparison_url_path(
                    reverse("receipt_comparison:comparison"),
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
    sort_key, sort_direction = page_usecase.resolve_sort(
        sort_key=request.GET.get("sort"),
        sort_direction=request.GET.get("dir"),
        reset_to_default=reset_sort,
    )
    if supplier and request.method == "GET" and request.GET.get("display") == "1":
        pending_store.clear()

    rows, has_pending = page_usecase.rows_for_page(
        pending_store,
        comparison_type,
        supplier,
        start_date,
        end_date,
        sort_key,
        sort_direction,
    )
    results_panel_active = page_usecase.is_results_panel_active(
        method=request.method,
        get_display=request.GET.get("display"),
        get_compared=request.GET.get("compared"),
        post_action=request.POST.get("action"),
        supplier=supplier,
        has_pending=has_pending,
    )
    context = page_usecase.build_context(
        type_slug=type_slug,
        comparison_type=comparison_type,
        supplier=supplier,
        start_date=start_date,
        end_date=end_date,
        rows=rows,
        has_pending=has_pending,
        results_panel_active=results_panel_active,
        sort_key=sort_key,
        sort_direction=sort_direction,
        display=1 if request.GET.get("display") == "1" else None,
        compared=1 if request.GET.get("compared") == "1" else None,
    )
    return render(
        request,
        "receipt_comparison/comparison.html",
        _comparison_page_template_context(request, context),
    )


@login_required
def legacy_comparison_redirect(request: HttpRequest, comparison_slug: str) -> HttpResponse:
    slug_to_comparison_type(comparison_slug)
    return redirect(
        append_query(
            f"{reverse('receipt_comparison:comparison')}?type={comparison_slug}",
            request.GET.urlencode(),
        )
    )


@login_required
def legacy_export_redirect(request: HttpRequest, comparison_slug: str) -> HttpResponse:
    slug_to_comparison_type(comparison_slug)
    return redirect(
        append_query(
            f"{reverse('receipt_comparison:export')}?type={comparison_slug}",
            request.GET.urlencode(),
        )
    )


@login_required
def legacy_settings_redirect(request: HttpRequest, comparison_slug: str) -> HttpResponse:
    slug_to_comparison_type(comparison_slug)
    return redirect(
        append_query(
            f"{reverse('receipt_comparison:settings')}?type={comparison_slug}",
            request.GET.urlencode(),
        )
    )


@login_required
def export_csv(request: HttpRequest) -> HttpResponse:
    type_slug = _comparison_type_slug_from_request(request)
    if type_slug is None:
        raise Http404
    comparison_type = slug_to_comparison_type(type_slug)
    supplier = get_object_or_404(supplier_model(comparison_type), id=request.GET.get("supplier_id"))
    start_date = parse_date(request.GET.get("start_date")) or date.today()
    end_date = parse_date(request.GET.get("end_date")) or start_date
    page_usecase = comparison_page_usecase()
    sort_key, sort_direction = page_usecase.resolve_sort(
        sort_key=request.GET.get("sort"),
        sort_direction=request.GET.get("dir"),
        reset_to_default=False,
    )
    outcome = export_csv_usecase().execute(
        pending_comparison_store(request),
        comparison_type=comparison_type,
        supplier=supplier,
        start_date=start_date,
        end_date=end_date,
        sort_key=sort_key,
        sort_direction=sort_direction,
    )
    response = HttpResponse(content_type="text/csv; charset=cp932")
    response["Content-Disposition"] = content_disposition_header(
        as_attachment=True,
        filename=outcome.filename,
    )
    writer = csv.writer(response)
    writer.writerow(outcome.columns)
    for row in outcome.rows:
        writer.writerow(row)
    return response


@login_required
@require_http_methods(["GET", "POST"])
def settings_page(request: HttpRequest) -> HttpResponse:
    if not is_portal_admin(request.user):
        return HttpResponse("権限がありません。", status=403)
    type_slug = _comparison_type_slug_from_request(request)
    if type_slug is None:
        return redirect(f"{reverse('receipt_comparison:settings')}?type=finished-product")
    comparison_type = slug_to_comparison_type(type_slug)
    if request.method == "POST":
        outcome = settings_post_usecase().execute(
            type_slug=type_slug,
            comparison_type=comparison_type,
            action=request.POST.get("action"),
            post_data=_post_values(request),
            user=request.user,
        )
        _apply_flash_messages(request, outcome.messages)
        return redirect(outcome.redirect_url)

    context = settings_page_usecase().execute(
        type_slug=type_slug,
        comparison_type=comparison_type,
        open_supplier_id=(request.GET.get("supplier_id") or "").strip(),
    )
    return render(
        request,
        "receipt_comparison/settings.html",
        {
            "type_slug": context.type_slug,
            "comparison_type": context.comparison_type,
            "comparison_type_page_label": context.comparison_type_page_label,
            "customer_choices": context.customer_choices,
            "choice_error": context.choice_error,
            "vendor_choices": context.vendor_choices,
            "suppliers": context.suppliers,
            "supplier_rows": context.supplier_rows,
            "open_supplier_id": context.open_supplier_id,
            "settings_target_label": context.settings_target_label,
            "settings_exclusion_label": context.settings_exclusion_label,
        },
    )
