"""メニュー利用ログ（E-601）を記録するミドルウェア。"""

from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse

from . import wiring
from application.portal.domain.value_objects.usage_record import resolve_usage_record_target

logger = logging.getLogger(__name__)


class UsageLoggingMiddleware:
    """応答が確定してから、記録対象であればメニュー利用ログを 1 件追記する。"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        try:
            self._record(request, response)
        except Exception:  # 記録の失敗で業務操作を止めない（REQ-F-004）
            logger.warning("メニュー利用ログの記録に失敗しました: path=%s", request.path, exc_info=True)
        return response

    def _record(self, request: HttpRequest, response: HttpResponse) -> None:
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return

        target = resolve_usage_record_target(
            path=request.path,
            comparison_type=request.GET.get("type", ""),
            status_code=response.status_code,
            content_type=response.headers.get("Content-Type", ""),
            is_attachment="attachment" in response.headers.get("Content-Disposition", ""),
        )
        if target is None:
            return

        wiring.record_usage_usecase().record(user=user, target=target)
