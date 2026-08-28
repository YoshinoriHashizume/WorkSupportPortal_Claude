from __future__ import annotations

from datetime import date

import pytest

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    EVALUATION_PERIODS,
    EvaluationPeriod,
    FLOW_AXIS_DORMANT,
    FLOW_AXIS_LOW_FLOW,
    FlowSelection,
    QUADRANT_DORMANT_STOCK,
    QUADRANT_EXCESS_STOCK_RISK,
    QUADRANT_NORMAL_FLOW,
    QUADRANT_SUPPLY_RISK,
)
from application.inventory_order_alert.domain.value_objects.list_query import ListQuery
from application.inventory_order_alert.domain.value_objects.list_rows import (
    apply_flow_quadrants_to_rows,
    filter_summary_rows,
)

AS_OF = date(2026, 8, 27)
SELECTION_L3 = FlowSelection(EvaluationPeriod(FLOW_AXIS_LOW_FLOW, 3))
SELECTION_D1 = FlowSelection(EvaluationPeriod(FLOW_AXIS_DORMANT, 1))
PERIOD_KEYS = {period.key for period in EVALUATION_PERIODS}
DATE_EMPTY_STRING = ""
DATE_UNPARSABLE = "2026/13/45"
QUADRANT_UNKNOWN = "謎"
ROWS_EMPTY: list[dict[str, object]] = []


def _query(
    *,
    cust_code: str = "",
    vend_code: str = "",
    flow_quadrant: str = "",
    attention_only: bool = False,
    hide_confirmed: bool = False,
    flow_selection: FlowSelection = SELECTION_L3,
) -> ListQuery:
    return ListQuery(
        as_of_date=AS_OF,
        cust_code=cust_code,
        vend_code=vend_code,
        flow_selection=flow_selection,
        flow_quadrant=flow_quadrant,
        attention_only=attention_only,
        hide_confirmed=hide_confirmed,
    )


def _source_row(
    *,
    cust_code: str = "112",
    vend_code: str = "9209",
    last_incoming_date: str = "2026/01/10",
    last_ship_date: str = "2026/08/01",
    confirmation_status: str = "未確認",
    qty: int = 100,
) -> dict[str, object]:
    return {
        "cust_code": cust_code,
        "level1_vend_cd": vend_code,
        "last_incoming_date": last_incoming_date,
        "last_ship_date": last_ship_date,
        "confirmation_status": confirmation_status,
        "post_shipment_total_qty": qty,
    }


def _filter_row(
    *,
    cust_code: str = "112",
    vend_code: str = "9209",
    flow_quadrant: str = QUADRANT_SUPPLY_RISK,
    confirmation_status: str = "未確認",
    qty: int = 100,
) -> dict[str, object]:
    return {
        "cust_code": cust_code,
        "level1_vend_cd": vend_code,
        "flow_quadrant": flow_quadrant,
        "confirmation_status": confirmation_status,
        "post_shipment_total_qty": qty,
    }


def test_apply_flow_quadrants_to_rows_adds_quadrant_key_matrix_and_flags():
    rows = [_source_row()]
    enriched = apply_flow_quadrants_to_rows(rows, as_of_date=AS_OF, query=_query())
    assert enriched[0]["flow_quadrant"] == QUADRANT_SUPPLY_RISK
    assert enriched[0]["flow_quadrant_key"] == "supply-risk"
    assert set(enriched[0]["flow_quadrants"]) == PERIOD_KEYS
    assert enriched[0]["flow_quadrants"]["L3"] == "supply-risk"
    assert enriched[0]["no_incoming_record"] is False
    assert enriched[0]["responsible_department"] == "調達G・営業G・生産管理"


def test_apply_flow_quadrants_to_rows_marks_no_incoming_record_when_date_is_missing():
    rows = [_source_row(last_incoming_date="")]
    enriched = apply_flow_quadrants_to_rows(rows, as_of_date=AS_OF, query=_query())
    assert enriched[0]["no_incoming_record"] is True
    assert enriched[0]["flow_quadrant"] == QUADRANT_SUPPLY_RISK


def test_apply_flow_quadrants_to_rows_uses_selected_evaluation_period():
    rows = [_source_row()]
    enriched = apply_flow_quadrants_to_rows(
        rows, as_of_date=AS_OF, query=_query(flow_selection=SELECTION_D1)
    )
    assert enriched[0]["flow_quadrant"] == QUADRANT_NORMAL_FLOW
    assert enriched[0]["flow_quadrant_key"] == "normal-flow"


def test_apply_flow_quadrants_to_rows_keeps_existing_row_keys():
    rows = [_source_row()]
    enriched = apply_flow_quadrants_to_rows(rows, as_of_date=AS_OF, query=_query())
    assert enriched[0]["cust_code"] == "112"
    assert enriched[0]["level1_vend_cd"] == "9209"
    assert enriched[0]["last_incoming_date"] == "2026/01/10"
    assert enriched[0]["last_ship_date"] == "2026/08/01"
    assert enriched[0]["confirmation_status"] == "未確認"
    assert enriched[0]["post_shipment_total_qty"] == 100


def test_apply_flow_quadrants_to_rows_treats_unparsable_date_as_out_of_period():
    rows = [_source_row(last_incoming_date=DATE_UNPARSABLE)]
    enriched = apply_flow_quadrants_to_rows(rows, as_of_date=AS_OF, query=_query())
    assert len(enriched) == 1
    assert enriched[0]["no_incoming_record"] is True
    assert enriched[0]["flow_quadrant"] == QUADRANT_SUPPLY_RISK


def test_apply_flow_quadrants_to_rows_treats_empty_date_string_as_out_of_period():
    rows = [_source_row(last_ship_date=DATE_EMPTY_STRING)]
    enriched = apply_flow_quadrants_to_rows(rows, as_of_date=AS_OF, query=_query())
    assert enriched[0]["flow_quadrant"] == QUADRANT_DORMANT_STOCK


def test_apply_flow_quadrants_to_rows_returns_empty_list_for_no_rows():
    assert apply_flow_quadrants_to_rows(ROWS_EMPTY, as_of_date=AS_OF, query=_query()) == []


def test_apply_flow_quadrants_to_rows_does_not_change_row_count():
    rows = [_source_row(cust_code=str(index)) for index in range(100)]
    enriched = apply_flow_quadrants_to_rows(rows, as_of_date=AS_OF, query=_query())
    assert len(enriched) == 100


def test_filter_summary_rows_by_cust_and_vend_code():
    rows = [_filter_row(cust_code="112"), _filter_row(cust_code="999"), _filter_row(vend_code="0001")]
    filtered = filter_summary_rows(rows, _query(cust_code="112", vend_code="9209"))
    assert len(filtered) == 1
    assert filtered[0]["cust_code"] == "112"


def test_filter_summary_rows_keeps_only_selected_flow_quadrant():
    rows = [
        _filter_row(flow_quadrant=QUADRANT_SUPPLY_RISK),
        _filter_row(flow_quadrant=QUADRANT_DORMANT_STOCK),
        _filter_row(flow_quadrant=QUADRANT_NORMAL_FLOW),
    ]
    filtered = filter_summary_rows(rows, _query(flow_quadrant="supply-risk"))
    assert [row["flow_quadrant"] for row in filtered] == [QUADRANT_SUPPLY_RISK]


def test_filter_summary_rows_with_attention_only_excludes_normal_flow():
    rows = [
        _filter_row(flow_quadrant=QUADRANT_SUPPLY_RISK),
        _filter_row(flow_quadrant=QUADRANT_DORMANT_STOCK),
        _filter_row(flow_quadrant=QUADRANT_EXCESS_STOCK_RISK),
        _filter_row(flow_quadrant=QUADRANT_NORMAL_FLOW),
    ]
    filtered = filter_summary_rows(rows, _query(attention_only=True))
    assert [row["flow_quadrant"] for row in filtered] == [
        QUADRANT_SUPPLY_RISK,
        QUADRANT_DORMANT_STOCK,
        QUADRANT_EXCESS_STOCK_RISK,
    ]


def test_filter_summary_rows_with_unknown_flow_quadrant_returns_all_rows():
    rows = [
        _filter_row(flow_quadrant=QUADRANT_SUPPLY_RISK),
        _filter_row(flow_quadrant=QUADRANT_NORMAL_FLOW),
    ]
    filtered = filter_summary_rows(rows, _query(flow_quadrant=QUADRANT_UNKNOWN))
    assert len(filtered) == 2


def test_filter_summary_rows_combines_flow_quadrant_with_confirmation_filter_as_and():
    rows = [
        _filter_row(flow_quadrant=QUADRANT_SUPPLY_RISK, confirmation_status="確認済み"),
        _filter_row(flow_quadrant=QUADRANT_SUPPLY_RISK, confirmation_status="未確認"),
        _filter_row(flow_quadrant=QUADRANT_NORMAL_FLOW, confirmation_status="未確認"),
    ]
    filtered = filter_summary_rows(rows, _query(flow_quadrant="supply-risk", hide_confirmed=True))
    assert len(filtered) == 1
    assert filtered[0]["flow_quadrant"] == QUADRANT_SUPPLY_RISK
    assert filtered[0]["confirmation_status"] == "未確認"


def test_filter_summary_rows_combines_flow_quadrant_with_customer_code_filter_as_and():
    rows = [
        _filter_row(cust_code="112", flow_quadrant=QUADRANT_SUPPLY_RISK),
        _filter_row(cust_code="999", flow_quadrant=QUADRANT_SUPPLY_RISK),
        _filter_row(cust_code="112", flow_quadrant=QUADRANT_NORMAL_FLOW),
    ]
    filtered = filter_summary_rows(rows, _query(cust_code="112", flow_quadrant="supply-risk"))
    assert len(filtered) == 1
    assert filtered[0]["cust_code"] == "112"
    assert filtered[0]["flow_quadrant"] == QUADRANT_SUPPLY_RISK


def test_filter_summary_rows_hide_confirmed():
    rows = [_filter_row(confirmation_status="確認済み"), _filter_row(confirmation_status="未確認")]
    filtered = filter_summary_rows(rows, _query(hide_confirmed=True))
    assert len(filtered) == 1
    assert filtered[0]["confirmation_status"] == "未確認"


def test_filter_summary_rows_does_not_accept_alert_only_keyword():
    rows = [_filter_row()]
    with pytest.raises(TypeError):
        filter_summary_rows(rows, _query(), alert_only=True)
