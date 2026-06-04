from __future__ import annotations

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect

from .favorites import can_access_menu_item, is_portal_admin
from .models import UserAccessRequest


ALLOWED_PATHS = {
    "/app/access-status",
}


class AccessApprovalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self.requires_approval_gate(request):
            access_request = getattr(request.user, "access_request", None)
            if access_request and access_request.status != UserAccessRequest.Status.APPROVED:
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

        if request.path.startswith("/app/production/five-year-nine") and not can_access_menu_item(
            request.user, "five-year-nine"
        ):
            return HttpResponse("権限がありません。", status=403)

        if request.path.startswith("/api/gonenkukumi/") and not can_access_menu_item(request.user, "five-year-nine"):
            return JsonResponse(
                {
                    "success": False,
                    "error": {"message": "権限がありません。"},
                },
                status=403,
            )

        return None
