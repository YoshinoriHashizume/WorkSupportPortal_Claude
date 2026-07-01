from __future__ import annotations

from applications.gonenkukumi.domain.ports import GonenKukumiHistoryRepository
from applications.gonenkukumi.domain.schemas import GonenKukumiSearchParams
from applications.gonenkukumi.models import GonenKukumiSearchHistory


class DjangoGonenKukumiHistoryRepository:
    def save(self, user_id: int, params: GonenKukumiSearchParams) -> None:
        GonenKukumiSearchHistory.objects.create(
            user_id=user_id,
            cust_code=params.cust_code,
            cust_item=params.cust_item,
            option_change=params.option_change,
            year_month=params.year_month,
        )

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
