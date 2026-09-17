"""Django 起動経路が判定軸撤去後も import できること（05_single-flow-view タスク2中断のhotfix）。"""

from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    DEFAULT_EVALUATION_PERIOD,
    QUADRANT_LOW_FLOW_NO_INCOMING,
    EvaluationPeriod,
)
from application.inventory_order_alert.domain.value_objects.flow_quadrant_rules import (
    build_flow_quadrant_rule_rows,
)
from application.inventory_order_alert.domain.value_objects.list_client_data import build_list_client_payload
from application.inventory_order_alert.domain.value_objects.list_filter import (
    ListFilterOptions,
    ListFilterParams,
    build_display_query_string,
)
from application.inventory_order_alert.domain.value_objects.list_query import parse_flow_selection
from application.inventory_order_alert.domain.value_objects.row_counts import count_rows
from application.inventory_order_alert.domain.value_objects.table_display import (
    DEFAULT_DIRECTION,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SORT,
    SortSpec,
    TableDisplayParams,
)
from application.inventory_order_alert.use_cases.portal_dashboard import BANNER_FLOW_CONDITION_LABEL


def test_inventory_order_alert_urls_import_without_flow_axis():
    from application.inventory_order_alert.interfaces import urls
    from application.inventory_order_alert.interfaces import views
    from application.inventory_order_alert.interfaces import wiring

    assert urls.urlpatterns
    assert views.list_page is not None
    assert wiring.list_page_usecase is not None


def test_parse_flow_selection_uses_years_and_ignores_axis():
    assert parse_flow_selection({}).period == DEFAULT_EVALUATION_PERIOD
    assert parse_flow_selection({"period": "5"}).period == EvaluationPeriod(5)
    assert parse_flow_selection({"period": "Y3"}).period == EvaluationPeriod(3)
    assert parse_flow_selection({"axis": "dormant", "period": "6"}).period == DEFAULT_EVALUATION_PERIOD


def test_list_client_payload_uses_evaluation_periods_instead_of_axes():
    payload = build_list_client_payload(
        all_rows=[],
        filter_options=ListFilterOptions.empty(),
        confirmation_status_choices=[],
    )
    assert "flowAxes" not in payload
    assert "flowPeriods" not in payload
    assert payload["defaultPeriodKey"] == "Y1"
    assert [item["key"] for item in payload["evaluationPeriods"]] == ["Y1", "Y3", "Y5"]


def test_display_query_string_keeps_period_years_without_axis():
    query = build_display_query_string(
        table_params=TableDisplayParams(
            sort_specs=(SortSpec(DEFAULT_SORT, DEFAULT_DIRECTION),),
            page=1,
            page_size=DEFAULT_PAGE_SIZE,
        ),
        filter_params=ListFilterParams(),
    )
    assert "axis=" not in query
    assert "period=1" in query


def test_count_rows_uses_renamed_quadrants():
    counts = count_rows([{"flow_quadrant": QUADRANT_LOW_FLOW_NO_INCOMING}])
    assert counts.low_flow_no_incoming == 1
    assert counts.low_flow_no_shipment == 0


def test_flow_quadrant_rules_use_renamed_quadrants():
    rows = build_flow_quadrant_rule_rows()
    assert [row.quadrant for row in rows][0] == QUADRANT_LOW_FLOW_NO_INCOMING


def test_dashboard_banner_label_is_period_only():
    # タスク 23 で「判定期間 1年」に確定（TC-SFV-A-004）。判定軸の文言は含まない
    assert BANNER_FLOW_CONDITION_LABEL == "判定期間 1年"
    assert "判定軸" not in BANNER_FLOW_CONDITION_LABEL
