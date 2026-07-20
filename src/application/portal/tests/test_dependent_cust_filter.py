from __future__ import annotations

from dataclasses import dataclass

from application.portal.domain.value_objects.dependent_cust_filter import (
    build_cust_chrg_cust_index,
    cust_options_for_chrg_psn,
    sanitize_cust_code,
)


@dataclass(frozen=True)
class _Option:
    value: str
    label: str


def test_build_cust_chrg_cust_index_maps_chrg_to_cust():
    rows = [
        {"cust_chrg_psn_cd": "A01", "cust_code": "112", "cust_name": "A社"},
        {"cust_chrg_psn_cd": "A01", "cust_code": "201", "cust_name": "B社"},
        {"cust_chrg_psn_cd": "B02", "cust_code": "201", "cust_name": "B社"},
        {"cust_chrg_psn_cd": "", "cust_code": "999", "cust_name": "無視"},
        {"cust_chrg_psn_cd": "A01", "cust_code": "", "cust_name": "無視"},
    ]
    assert build_cust_chrg_cust_index(rows) == {
        "A01": {"112": "A社", "201": "B社"},
        "B02": {"201": "B社"},
    }


def test_cust_options_for_chrg_psn_empty_chrg_returns_all():
    options = (
        _Option("112", "112 - A社"),
        _Option("201", "201 - B社"),
    )
    index = {"A01": {"112": "A社"}}
    assert cust_options_for_chrg_psn(options, index, "") == options


def test_cust_options_for_chrg_psn_filters_by_chrg():
    options = (
        _Option("112", "112 - A社"),
        _Option("201", "201 - B社"),
    )
    index = {"A01": {"112": "A社"}}
    assert cust_options_for_chrg_psn(options, index, "A01") == (_Option("112", "112 - A社"),)
    assert cust_options_for_chrg_psn(options, index, "Z99") == ()


def test_sanitize_cust_code_keeps_visible_value_only():
    visible = (_Option("112", "112 - A社"),)
    assert sanitize_cust_code("112", visible) == "112"
    assert sanitize_cust_code("201", visible) == ""
    assert sanitize_cust_code(" 112 ", visible) == "112"
