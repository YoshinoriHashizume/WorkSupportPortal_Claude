from __future__ import annotations

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect

from .favorites import can_access_menu_item, is_portal_admin, receipt_comparison_type_from_path
from application.portal.domain.value_objects.access_status import ACCESS_STATUS_APPROVED


ALLOWED_PATHS = {
    "/app/access-status",
}


def receipt_comparison_menu_key_for_request(request: HttpRequest) -> str | None:
    path = request.path
    if path.startswith("/app/production/receipt-comparison/supplied-parts"):
        return "receipt-comparison-supplied-parts"
    if path.startswith("/app/production/receipt-comparison/finished-product"):
        return "receipt-comparison-finished-product"
    if not path.startswith("/app/production/receipt-comparison"):
        return None
    type_param = request.GET.get("type") or receipt_comparison_type_from_path(path)
    if type_param == "supplied-parts":
        return "receipt-comparison-supplied-parts"
    return "receipt-comparison-finished-product"


class AccessApprovalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self.requires_approval_gate(request):
            access_request = getattr(request.user, "access_request", None)
            if access_request and access_request.status != ACCESS_STATUS_APPROVED:
                if request.path.startswith("/api/"):
                    return JsonResponse(
                        {
                            "success": False,
                            "error": {"message": "利用承認が完了していません。"},
                        },
                        status=403,
                    )
                return redirect("portal:access_status")

            permission_response = self.permission_response(request)
            if permission_response is not None:
                return permission_response
        return self.get_response(request)

    def requires_approval_gate(self, request: HttpRequest) -> bool:
        user = getattr(request, "user", None)
        if not getattr(user, "is_authenticated", False):
            return False
        if request.path in ALLOWED_PATHS:
            return False
        return request.path.startswith("/app") or request.path.startswith("/api/")

    def permission_response(self, request: HttpRequest) -> HttpResponse | None:
        if request.path.startswith("/app/management/") and not is_portal_admin(request.user):
            return HttpResponse("権限がありません。", status=403)

        if request.path.startswith("/app/production/receipt-comparison") and "/settings" in request.path and not is_portal_admin(
            request.user
        ):
            return HttpResponse("権限がありません。", status=403)

        if request.path.startswith("/app/production/five-year-nine") and not can_access_menu_item(
            request.user, "five-year-nine"
        ):
            return HttpResponse("権限がありません。", status=403)

        receipt_comparison_menu_key = receipt_comparison_menu_key_for_request(request)
        if receipt_comparison_menu_key and not can_access_menu_item(request.user, receipt_comparison_menu_key):
            return HttpResponse("権限がありません。", status=403)

        if request.path.startswith("/api/gonenkukumi/") and not can_access_menu_item(request.user, "five-year-nine"):
            return JsonResponse(
                {
                    "success": False,
                    "error": {"message": "権限がありません。"},
                },
                status=403,
            )

        if request.path.startswith("/app/production/inventory-order-alert") and not can_access_menu_item(
            request.user, "inventory-order-alert"
        ):
            return HttpResponse("権限がありません。", status=403)

        if request.path.startswith("/api/inventory-order-alert/") and not can_access_menu_item(
            request.user, "inventory-order-alert"
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": {"message": "権限がありません。"},
                },
                status=403,
            )

        if request.path.startswith("/app/general-affairs/asset-inventory") and not can_access_menu_item(
            request.user, "asset-inventory"
        ):
            return HttpResponse("権限がありません。", status=403)

        if request.path.startswith("/api/asset-inventory/") and not can_access_menu_item(
            request.user, "asset-inventory"
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": {"message": "権限がありません。"},
                },
                status=403,
            )

        if request.path.startswith("/app/sales/shipment-trend") and not can_access_menu_item(
            request.user, "shipment-trend-list"
        ):
            return HttpResponse("権限がありません。", status=403)

        if request.path.startswith("/api/shipment-trend/") and not can_access_menu_item(
            request.user, "shipment-trend-list"
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": {"message": "権限がありません。"},
                },
                status=403,
            )

        return None
