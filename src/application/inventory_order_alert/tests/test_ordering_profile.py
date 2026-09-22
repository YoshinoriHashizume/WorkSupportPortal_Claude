"""発注方式（V-227）・リードタイム（V-225）のテスト（TC-SOR-D-010〜011）。"""

from __future__ import annotations

import pytest

from application.inventory_order_alert.domain.value_objects.ordering_profile import (
    LEAD_TIME_SOURCE_DEFAULT,
    LEAD_TIME_SOURCE_MASTER,
    ORDERING_MANUAL,
    ORDERING_MRP,
    ORDERING_UNKNOWN,
    ordering_method_from_code,
    resolve_lead_time_days,
)


@pytest.mark.parametrize(
    "code, expected",
    [("4", ORDERING_MANUAL), (4, ORDERING_MANUAL), ("5", ORDERING_MRP), (5, ORDERING_MRP), ("6", ORDERING_UNKNOWN), (None, ORDERING_UNKNOWN), ("", ORDERING_UNKNOWN), (" 4 ", ORDERING_MANUAL)],
)
def test_d010_ordering_method_from_code(code, expected):
    assert ordering_method_from_code(code) == expected


@pytest.mark.parametrize(
    "value, expected",
    [(3, (3, LEAD_TIME_SOURCE_MASTER)), (0, (5, LEAD_TIME_SOURCE_DEFAULT)), (None, (5, LEAD_TIME_SOURCE_DEFAULT)), ("abc", (5, LEAD_TIME_SOURCE_DEFAULT)), ("7", (7, LEAD_TIME_SOURCE_MASTER)), (-2, (5, LEAD_TIME_SOURCE_DEFAULT)), (2.0, (2, LEAD_TIME_SOURCE_MASTER))],
)
def test_d011_resolve_lead_time_days(value, expected):
    assert resolve_lead_time_days(value, default_days=5) == expected


def test_labels_are_japanese_terms():
    assert (ORDERING_MANUAL, ORDERING_MRP, ORDERING_UNKNOWN) == ("手動発注", "MRP 発注", "不明")
