from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from applications.inventory_order_alert.domain.app_settings import AppSettings, clamp_warning_months
from applications.inventory_order_alert.domain.dates import parse_optional_ymd


@dataclass(frozen=True)
class ListQuery:
    as_of_date: date
    cust_code: str = ""
    vend_code: str = ""
    alert_only: bool = True
    hide_confirmed: bool = False
    warning_shipment_months: int = 12
    warning_incoming_months: int = 12
    critical_enabled: bool = True


def parse_list_query(params: dict[str, str], *, today: date | None = None) -> ListQuery:
    return ListQuery(
        as_of_date=parse_optional_ymd(params.get("asOfDate", ""), today=today),
        cust_code=params.get("custCode", "").strip(),
        vend_code=params.get("vendCode", "").strip(),
        alert_only=params.get("alertOnly", "true").lower() not in {"false", "0", "off"},
        hide_confirmed=params.get("hideConfirmed", "false").lower() in {"true", "1", "on"},
        warning_shipment_months=clamp_warning_months(
            int(params.get("warningShipmentMonths", "12") or 12)
        ),
        warning_incoming_months=clamp_warning_months(
            int(params.get("warningIncomingMonths", "12") or 12)
        ),
        critical_enabled=params.get("criticalEnabled", "true").lower() not in {"false", "0", "off"},
    )


def merge_query_with_settings(query: ListQuery, settings: AppSettings) -> ListQuery:
    return ListQuery(
        as_of_date=query.as_of_date,
        cust_code=query.cust_code,
        vend_code=query.vend_code,
        alert_only=query.alert_only,
        hide_confirmed=query.hide_confirmed,
        warning_shipment_months=settings.warning_shipment_months,
        warning_incoming_months=settings.warning_incoming_months,
        critical_enabled=settings.critical_enabled,
    )
