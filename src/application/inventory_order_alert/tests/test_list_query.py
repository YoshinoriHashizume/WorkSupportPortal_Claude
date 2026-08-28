from __future__ import annotations

from dataclasses import fields
from datetime import date

from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    FLOW_AXIS_DORMANT,
    FLOW_AXIS_LOW_FLOW,
)
from application.inventory_order_alert.domain.value_objects.list_query import (
    ListQuery,
    merge_query_with_settings,
    parse_list_query,
)

TODAY = date(2026, 6, 17)
AXIS_UNKNOWN = "foo"
PERIOD_NON_NUMERIC = "abc"
PERIOD_OUT_OF_RANGE = "999"
QUADRANT_UNKNOWN = "謎"
REMOVED_FIELD_NAMES = (
    "alert_only",
    "warning_shipment_months",
    "warning_incoming_months",
    "critical_enabled",
)


def test_parse_list_query_defaults_to_low_flow_axis_three_months():
    query = parse_list_query({}, today=TODAY)
    assert query.as_of_date == TODAY
    assert query.flow_selection.axis == FLOW_AXIS_LOW_FLOW
    assert query.flow_selection.key == "L3"


def test_parse_list_query_accepts_dormant_axis_with_default_one_year():
    query = parse_list_query({"axis": FLOW_AXIS_DORMANT}, today=TODAY)
    assert query.flow_selection.axis == FLOW_AXIS_DORMANT
    assert query.flow_selection.key == "D1"


def test_parse_list_query_accepts_explicit_period_for_axis():
    query = parse_list_query({"axis": FLOW_AXIS_DORMANT, "period": "5"}, today=TODAY)
    assert query.flow_selection.key == "D5"


def test_parse_list_query_falls_back_when_period_does_not_belong_to_axis():
    query = parse_list_query({"axis": FLOW_AXIS_DORMANT, "period": "3"}, today=TODAY)
    assert query.flow_selection.key == "D1"


def test_parse_list_query_falls_back_when_axis_is_unknown():
    query = parse_list_query({"axis": AXIS_UNKNOWN, "period": "6"}, today=TODAY)
    assert query.flow_selection.axis == FLOW_AXIS_LOW_FLOW
    assert query.flow_selection.key == "L3"


def test_parse_list_query_falls_back_when_period_is_not_numeric():
    query = parse_list_query({"axis": FLOW_AXIS_LOW_FLOW, "period": PERIOD_NON_NUMERIC}, today=TODAY)
    assert query.flow_selection.key == "L3"


def test_parse_list_query_falls_back_when_period_is_out_of_range():
    query = parse_list_query({"period": PERIOD_OUT_OF_RANGE}, today=TODAY)
    assert query.flow_selection.key == "L3"


def test_parse_list_query_accepts_flow_quadrant_key():
    query = parse_list_query({"flow_quadrant": "supply-risk"}, today=TODAY)
    assert query.flow_quadrant == "supply-risk"


def test_parse_list_query_clears_unknown_flow_quadrant():
    query = parse_list_query({"flow_quadrant": QUADRANT_UNKNOWN}, today=TODAY)
    assert query.flow_quadrant == ""


def test_parse_list_query_accepts_attention_only_flag():
    query = parse_list_query({"attentionOnly": "true"}, today=TODAY)
    assert query.attention_only is True


def test_parse_list_query_defaults_attention_only_to_false():
    query = parse_list_query({}, today=TODAY)
    assert query.attention_only is False
    assert query.flow_quadrant == ""


def test_parse_list_query_keeps_customer_and_vendor_and_hide_confirmed():
    query = parse_list_query(
        {"custCode": "112", "vendCode": "9209", "hideConfirmed": "true"},
        today=TODAY,
    )
    assert query.cust_code == "112"
    assert query.vend_code == "9209"
    assert query.hide_confirmed is True


def test_list_query_has_no_alert_only_or_warning_month_fields():
    field_names = {field.name for field in fields(ListQuery)}
    for removed in REMOVED_FIELD_NAMES:
        assert removed not in field_names


def test_merge_query_with_settings_keeps_flow_selection_and_filters():
    query = parse_list_query({"axis": FLOW_AXIS_DORMANT, "period": "5", "flow_quadrant": "supply-risk"}, today=TODAY)
    settings = AppSettings()

    merged = merge_query_with_settings(query, settings)

    assert merged.flow_selection.key == "D5"
    assert merged.flow_quadrant == "supply-risk"
    assert merged.cust_code == query.cust_code
