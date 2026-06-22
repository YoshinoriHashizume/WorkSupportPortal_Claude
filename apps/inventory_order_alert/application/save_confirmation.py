from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.inventory_order_alert.domain.alert_level import ALERT_NONE, normalize_alert_level
from apps.inventory_order_alert.models import ConfirmationStatus, InventoryOrderAlertConfirmation

MAX_MEMO_LENGTH = 500


@dataclass(frozen=True)
class ConfirmationInput:
    cust_code: str
    item_cd: str
    status: str


def parse_confirmation_payload(data: object) -> ConfirmationInput:
    if not isinstance(data, dict):
        raise ValueError("JSON の形式が不正です。")

    cust_code = str(data.get("custCode") or "").strip()
    item_cd = str(data.get("itemCd") or "").strip()
    status = str(data.get("status") or "").strip()

    if not cust_code:
        raise ValueError("custCode は必須です。")
    if not item_cd:
        raise ValueError("itemCd は必須です。")
    if status not in ConfirmationStatus.values:
        raise ValueError("status が不正です。")

    return ConfirmationInput(
        cust_code=cust_code,
        item_cd=item_cd,
        status=status,
    )


def parse_memo_payload(data: object) -> str:
    if not isinstance(data, dict):
        raise ValueError("JSON の形式が不正です。")
    memo = str(data.get("memo") or "").strip()
    if len(memo) > MAX_MEMO_LENGTH:
        raise ValueError(f"メモは {MAX_MEMO_LENGTH} 文字以内で入力してください。")
    return memo


def save_confirmation(
    input_data: ConfirmationInput,
    *,
    confirmed_by: str,
    alert_level: str = "",
) -> InventoryOrderAlertConfirmation:
    confirmed_at = None
    confirmed_by_value = ""
    confirmed_alert_level = ""
    if input_data.status in {ConfirmationStatus.IN_PROGRESS, ConfirmationStatus.CONFIRMED}:
        confirmed_at = timezone.now()
        confirmed_by_value = confirmed_by
        confirmed_alert_level = normalize_alert_level(alert_level or ALERT_NONE)

    confirmation, _created = InventoryOrderAlertConfirmation.objects.update_or_create(
        cust_code=input_data.cust_code,
        item_cd=input_data.item_cd,
        defaults={
            "status": input_data.status,
            "confirmed_at": confirmed_at,
            "confirmed_by": confirmed_by_value,
            "confirmed_alert_level": confirmed_alert_level,
        },
    )
    return confirmation
