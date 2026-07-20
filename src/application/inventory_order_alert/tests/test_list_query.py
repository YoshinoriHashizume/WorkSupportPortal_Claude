from __future__ import annotations

from datetime import date

import pytest

from application.inventory_order_alert.domain.value_objects.list_query import ListQuery, merge_query_with_settings
from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings


def test_merge_query_with_settings_applies_warning_months():
    query = ListQuery(as_of_date=date(2026, 6, 17), warning_shipment_months=6, warning_incoming_months=6)
    settings = AppSettings(
        warning_shipment_months=24,
        warning_incoming_months=18,
        critical_enabled=False,
    )

    merged = merge_query_with_settings(query, settings)

    assert merged.warning_shipment_months == 24
    assert merged.warning_incoming_months == 18
    assert merged.critical_enabled is False
    assert merged.cust_code == query.cust_code
