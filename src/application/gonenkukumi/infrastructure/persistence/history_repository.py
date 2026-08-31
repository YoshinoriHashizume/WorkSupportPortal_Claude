from __future__ import annotations

from application.gonenkukumi.domain.repositories.ports import GonenKukumiHistoryRepository
from application.gonenkukumi.domain.value_objects.schemas import GonenKukumiSearchParams
from application.gonenkukumi.models import GonenKukumiSearchHistory

# 検索履歴の保持上限（ユーザーあたりの件数）。画面は条件セットごと最新 1 件・最大 20 件、
# API は最大 50 件しか返さないため、100 件あれば表示に影響しない（機能仕様書 §5.1）。
HISTORY_RETENTION_LIMIT = 100


class DjangoGonenKukumiHistoryRepository:
    def save(self, user_id: int, params: GonenKukumiSearchParams) -> None:
        GonenKukumiSearchHistory.objects.create(
            user_id=user_id,
            cust_code=params.cust_code,
            cust_item=params.cust_item,
            option_change=params.option_change,
            year_month=params.year_month,
        )
        self._purge_beyond_limit(user_id)

    @staticmethod
    def _purge_beyond_limit(user_id: int) -> None:
        """保持上限を超えた古い履歴を削除する（無制限な増加を防ぐ）。"""
        keep_ids = list(
            GonenKukumiSearchHistory.objects.filter(user_id=user_id)
            .order_by("-executed_at")
            .values_list("id", flat=True)[:HISTORY_RETENTION_LIMIT]
        )
        GonenKukumiSearchHistory.objects.filter(user_id=user_id).exclude(id__in=keep_ids).delete()

    def latest_unique(self, user_id: int, limit: int = 20) -> list[dict[str, object]]:
        histories: list[dict[str, object]] = []
        seen: set[tuple[str, str, str, str]] = set()
        queryset = GonenKukumiSearchHistory.objects.filter(user_id=user_id).order_by("-executed_at")
        for history in queryset:
            key = (history.cust_code, history.cust_item, history.option_change, history.year_month)
            if key in seen:
                continue
            seen.add(key)
            histories.append(history.to_api_dict())
            if len(histories) >= limit:
                break
        return histories

    def latest_initial_values(self, user_id: int) -> dict[str, str] | None:
        latest = GonenKukumiSearchHistory.objects.filter(user_id=user_id).first()
        if latest is None:
            return None
        return {
            "custCode": latest.cust_code,
            "custItem": latest.cust_item,
            "optionChange": latest.option_change,
            "yearMonth": latest.year_month,
        }
