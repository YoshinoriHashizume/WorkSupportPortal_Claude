from datetime import date

import pytest

from application.gonenkukumi.domain.value_objects.schemas import validate_search_params
from application.gonenkukumi.domain.value_objects.year_month_nav import compare_ym, next_month, normalize_year_month, previous_month
from application.gonenkukumi.infrastructure.oracle.client import (
    attach_supplier_master,
    fetch_customer_previous_balance,
    fetch_monthly_order_work,
    fetch_supplier_demand_series,
    fetch_supplier_previous_purchase_balance,
    fetch_supplier_root_items,
    parse_day_number,
    parse_quantity,
    with_row_totals,
)
from application.gonenkukumi.templatetags.gonenkukumi_format import quantity


def test_compare_ym():
    assert compare_ym("2026-05", "2026-04") == 1
    assert compare_ym("2026-05", "2026-05") == 0
    assert compare_ym("2026-04", "2026-05") == -1


def test_month_navigation_crosses_year_boundary():
    assert previous_month("2026-01") == "2025-12"
    assert next_month("2026-12") == "2027-01"


def test_validate_search_params_accepts_valid_input():
    params = validate_search_params({"custCode": "101", "custItem": "ITEM-001", "yearMonth": "2026-05", "asOfDate": "2026-05-21", "optionChange": "*"})
    assert params.cust_code == "101"
    assert params.option_change == "*"
    assert params.as_of_date.isoformat() == "2026-05-21"


def test_validate_search_params_defaults_as_of_date_to_month_start():
    params = validate_search_params({"custCode": "101", "custItem": "ITEM-001", "yearMonth": "2026-05", "optionChange": "*"})
    assert params.as_of_date.isoformat() == "2026-05-01"


def test_validate_search_params_keeps_text_option_change():
    params = validate_search_params({"custCode": "101", "custItem": "ITEM-001", "yearMonth": "2026-05", "optionChange": "A1"})
    assert params.option_change == "A1"


def test_validate_search_params_accepts_japanese_year_month():
    params = validate_search_params({"custCode": "101", "custItem": "ITEM-001", "yearMonth": "2026年05月", "optionChange": "*"})
    assert params.year_month == "2026-05"


def test_normalize_year_month_accepts_slash_and_single_digit_month():
    assert normalize_year_month("2026/5") == "2026-05"


def test_normalize_year_month_accepts_spaced_japanese_date():
    assert normalize_year_month("２０２６年　０５月２０日") == "2026-05"


def test_normalize_year_month_ignores_escaped_unicode_noise():
    assert normalize_year_month("2026-¥u3000 6 日") == "2026-06"


def test_normalize_year_month_accepts_fullwidth_month_after_separator():
    assert normalize_year_month("2026-\u3000６日") == "2026-06"


def test_validate_search_params_accepts_fullwidth_month_after_separator():
    params = validate_search_params({"custCode": "101", "custItem": "ITEM-001", "yearMonth": "2026-\u3000６日", "optionChange": "*"})
    assert params.year_month == "2026-06"


def test_validate_search_params_accepts_month_only_locale_value():
    params = validate_search_params({"custCode": "101", "custItem": "ITEM-001", "yearMonth": "\u3000６日", "optionChange": "*"})
    assert params.year_month.endswith("-06")


def test_validate_search_params_rejects_invalid_cust_code():
    with pytest.raises(ValueError):
        validate_search_params({"custCode": "10A", "yearMonth": "2026-05"})


def test_parse_day_number_accepts_oracle_monthly_work_day_text():
    assert parse_day_number("\u3000６日") == 6
    assert parse_day_number("26") == 26
    assert parse_day_number("32日") is None


def test_parse_quantity_accepts_text_number():
    assert parse_quantity("1,234") == 1234


def test_quantity_filter_hides_zero_and_formats_with_commas():
    assert quantity(0) == ""
    assert quantity(None) == ""
    assert quantity(1234) == "1,234"
    assert quantity(-1234567) == "-1,234,567"


def test_with_row_totals_includes_previous_balance():
    result = {
        "blocks": [
            {
                "rows": [
                    {"item": "確定受注", "values": [10, 20], "balance": 5},
                    {"item": "本日在庫", "values": [0, 0], "total": 100},
                ]
            }
        ]
    }

    with_row_totals(result)

    rows = result["blocks"][0]["rows"]
    assert rows[0]["total"] == 35
    assert rows[1]["total"] == 100
    assert rows[1]["balance"] is None
    assert rows[1]["values"] == [0, 0]


def test_fetch_supplier_demand_series_joins_purchase_order(monkeypatch):
    executed = {}

    class FakeCursor:
        def execute(self, sql, params):
            executed["sql"] = sql
            executed["params"] = params

        def fetchall(self):
            return [(1, 10), (3, "2")]

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr("application.gonenkukumi.infrastructure.oracle.client.oracle_config", lambda: {"company_cd": ""})

    values = fetch_supplier_demand_series(
        FakeConnection(),
        item_cd="PART-001",
        vend_cd="V001",
        start_date=date(2026, 5, 1),
        next_month_date=date(2026, 6, 1),
    )

    assert "FROM T_OD od" in executed["sql"]
    assert "SUM(NVL(od.ODR_QTY, 0)) AS QTY" in executed["sql"]
    assert "od.PRD_DUE_DATE >= :start_date" in executed["sql"]
    assert "od.OD_TYP = '2'" in executed["sql"]
    assert "LEFT JOIN T_RLSD_PUCH_ODR purchase" in executed["sql"]
    assert "purchase.OD_NO = od.OD_NO" in executed["sql"]
    assert "purchase.ODR_CANCEL_SLIP_ISS_FLG IN ('0')" in executed["sql"]
    assert "vend_cd" not in executed["params"]
    assert values[0] == 10
    assert values[2] == 2


def test_fetch_customer_previous_balance_uses_vba_remaining_order_logic(monkeypatch):
    executed = {}

    class FakeCursor:
        def execute(self, sql, params):
            executed["sql"] = sql
            executed["params"] = params

        def fetchone(self):
            return (30,)

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr("application.gonenkukumi.infrastructure.oracle.client.oracle_config", lambda: {"company_cd": ""})
    params = validate_search_params(
        {"custCode": "101", "custItem": "ITEM-001", "yearMonth": "2026-05", "asOfDate": "2026-05-01", "optionChange": "*"}
    )

    value = fetch_customer_previous_balance(
        FakeConnection(),
        params=params,
        internal_item_cd="ITEM-001",
        start_date=date(2026, 5, 1),
    )

    assert "SUM(ODR_QTY) - SUM(TOTAL_SHIP_QTY)" in executed["sql"]
    assert "DESINATED_DLV_DATE <= :legacy_cutoff_date" in executed["sql"]
    assert "ODR_CMPLT_FLG != '1'" in executed["sql"]
    assert "DEL_FLG != '1'" in executed["sql"]
    assert executed["params"]["legacy_cutoff_date"] == date(2022, 10, 1)
    assert value == 30


def test_fetch_supplier_root_items_includes_related_items():
    class FakeCursor:
        def execute(self, sql, params):
            self.sql = sql
            self.params = params

        def fetchall(self):
            return [("SUB-001", None, "SUB-002", "SUB-001", "")]

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

    assert fetch_supplier_root_items(FakeConnection(), "ROOT-001") == ["ROOT-001", "SUB-001", "SUB-002"]


def test_attach_supplier_master_uses_vba_last_row():
    executed = {}

    class FakeCursor:
        def execute(self, sql, params):
            executed["sql"] = sql
            executed["params"] = params

        def fetchall(self):
            return [("V001", "仕入先1", "A1"), ("V002", "仕入先2", None)]

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

    supplier = attach_supplier_master(FakeConnection(), {"itemCd": "PART-001"})

    assert "vend.VEND_ANAME" in executed["sql"]
    assert "ORDER BY" not in executed["sql"]
    assert "cost.VEND_CD = vend.VEND_CD" in executed["sql"]
    assert "wh.ITEM_CD = cost.ITEM_CD" in executed["sql"]
    assert supplier["vendCd"] == "V002"
    assert supplier["vendName"] == "仕入先2"
    assert supplier["whCd"] == "?"


def test_fetch_monthly_order_work_uses_vba_exact_keys():
    executed = {}

    class FakeCursor:
        def execute(self, sql, params):
            executed["sql"] = sql
            executed["params"] = params

        def fetchall(self):
            return [
                ("1日", 10, "2日", 20, *([None, None] * 24)),
                ("1日", 30, *([None, None] * 25)),
            ]

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

    values = fetch_monthly_order_work(FakeConnection(), item_cd="PART-001", vend_cd="V001", year_month="2026-06")

    assert "TRIM(" not in executed["sql"]
    assert "LPAD(" not in executed["sql"]
    assert "MNGMNT_MONTH = :month" in executed["sql"]
    assert executed["params"]["month"] == "6"
    assert values[0] == 30
    assert values[1] == 20


def test_fetch_supplier_previous_purchase_balance_subtracts_accepted(monkeypatch):
    executed = {}

    class FakeCursor:
        def execute(self, sql, params):
            executed["sql"] = sql
            executed["params"] = params

        def fetchone(self):
            return (120,)

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr("application.gonenkukumi.infrastructure.oracle.client.oracle_config", lambda: {"company_cd": ""})

    value = fetch_supplier_previous_purchase_balance(
        FakeConnection(),
        item_cd="PART-001",
        vend_cd="V001",
        start_date=date(2026, 5, 1),
    )

    assert "LEFT OUTER JOIN T_PAST_INSPC_ACPT accepted" in executed["sql"]
    assert "MAX(purchase.PUCH_ODR_QTY) - NVL(SUM(accepted.ACPT_QTY), 0) AS ZANSU" in executed["sql"]
    assert "purchase.PUCH_ODR_STS_TYP = '2'" in executed["sql"]
    assert "purchase.ODR_CANCEL_SLIP_ISS_FLG = '0'" in executed["sql"]
    assert executed["params"]["vend_cd"] == "V001"
    assert value == 120
