"""一覧クエリの解釈のテスト（test-design.md TC-SFV-D-050〜053）。

判定軸（V-210）は廃止。`period` は判定期間（V-211）の年数（`1` / `3` / `5`）または Y キーのみを解釈し、
`axis` は無視する。流動区分の絞り込みは旧キーを新キーへ写像する。
"""

from __future__ import annotations

from dataclasses import fields
from datetime import date

import pytest

from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    DEFAULT_EVALUATION_PERIOD,
    FLOW_QUADRANT_KEYS,
    QUADRANT_LOW_FLOW_NO_INCOMING,
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    EvaluationPeriod,
    FlowSelection,
)
from application.inventory_order_alert.domain.value_objects.list_query import (
    ListQuery,
    merge_query_with_settings,
    parse_flow_quadrant,
    parse_flow_selection,
    parse_list_query,
)

TODAY = date(2026, 9, 7)
KEY_LOW_FLOW_NO_INCOMING = FLOW_QUADRANT_KEYS[QUADRANT_LOW_FLOW_NO_INCOMING]
KEY_LOW_FLOW_NO_SHIPMENT = FLOW_QUADRANT_KEYS[QUADRANT_LOW_FLOW_NO_SHIPMENT]
REMOVED_FIELD_NAMES = (
    "alert_only",
    "warning_shipment_months",
    "warning_incoming_months",
    "critical_enabled",
)


# --- TC-SFV-D-050: period の年数を解釈する ---


@pytest.mark.parametrize("raw, years", [("1", 1), ("3", 3), ("5", 5), ("Y1", 1), ("Y3", 3), ("Y5", 5), (" 3 ", 3)])
def test_d050_period_years_are_parsed(raw, years):
    assert parse_flow_selection({"period": raw}) == FlowSelection(EvaluationPeriod(years))


def test_d050_parse_list_query_carries_flow_selection():
    query = parse_list_query({"period": "3"}, today=TODAY)
    assert query.as_of_date == TODAY
    assert query.flow_selection.period.years == 3
    assert query.flow_selection.key == "Y3"


# --- TC-SFV-D-051: period 不正・旧値・空は既定 ---


@pytest.mark.parametrize("raw", ["6", "2", "abc", "", "999", "L3", "D1", "-1", "1.0"])
def test_d051_invalid_or_legacy_period_falls_back_to_default(raw):
    assert parse_flow_selection({"period": raw}).period == DEFAULT_EVALUATION_PERIOD


def test_d051_missing_period_falls_back_to_default():
    query = parse_list_query({}, today=TODAY)
    assert query.flow_selection.period == DEFAULT_EVALUATION_PERIOD
    assert query.flow_selection.key == "Y1"


# --- TC-SFV-D-052: axis は無視される ---


@pytest.mark.parametrize("axis", ["dormant", "low_flow", "foo", ""])
def test_d052_axis_is_ignored(axis):
    assert parse_flow_selection({"axis": axis, "period": "3"}).period.years == 3


def test_d052_axis_alone_does_not_change_default():
    assert parse_flow_selection({"axis": "dormant"}).period == DEFAULT_EVALUATION_PERIOD


def test_d052_flow_selection_has_no_axis():
    selection = parse_flow_selection({"period": "1"})
    assert not hasattr(selection, "axis")
    assert not hasattr(selection, "axis_label")


# --- TC-SFV-D-053: flow_quadrant の旧キーは新キーへ ---


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("supply-risk", KEY_LOW_FLOW_NO_INCOMING),
        ("excess-stock-risk", KEY_LOW_FLOW_NO_SHIPMENT),
        ("供給リスク品", KEY_LOW_FLOW_NO_INCOMING),
        ("在庫過剰リスク品", KEY_LOW_FLOW_NO_SHIPMENT),
    ],
)
def test_d053_legacy_flow_quadrant_is_mapped_to_new_key(raw, expected):
    assert parse_flow_quadrant({"flow_quadrant": raw}) == expected
    assert parse_list_query({"flow_quadrant": raw}, today=TODAY).flow_quadrant == expected


@pytest.mark.parametrize("key", sorted(FLOW_QUADRANT_KEYS.values()))
def test_d053_new_keys_are_accepted_as_is(key):
    assert parse_flow_quadrant({"flow_quadrant": key}) == key


@pytest.mark.parametrize("label, key", list(FLOW_QUADRANT_KEYS.items()))
def test_d053_labels_are_accepted_and_converted_to_key(label, key):
    assert parse_flow_quadrant({"flow_quadrant": label}) == key


@pytest.mark.parametrize("raw", ["", "謎", "foo", "normal"])
def test_d053_unknown_flow_quadrant_means_no_filter(raw):
    assert parse_flow_quadrant({"flow_quadrant": raw}) == ""


# --- 既存の断言（判定軸に依存しないもの） ---


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
    query = parse_list_query({"period": "5", "flow_quadrant": "supply-risk"}, today=TODAY)
    settings = AppSettings()

    merged = merge_query_with_settings(query, settings)

    assert merged.flow_selection.key == "Y5"
    assert merged.flow_quadrant == KEY_LOW_FLOW_NO_INCOMING
    assert merged.cust_code == query.cust_code
