"""照合単位行（T-213）の画面・API・CSV（spec/13 test-design TC-RUR-V-001〜010）。"""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import date
from pathlib import Path

import pytest

from application.inventory_order_alert.interfaces.wiring import portal_dashboard_usecase
from application.inventory_order_alert.models import (
    InventoryOrderAlertConfirmation,
    InventoryOrderAlertSummarySnapshot,
    SlimsStockImport,
)
from application.inventory_order_alert.tests.test_reconciliation_unit_row import (
    _single_s_row,
    _unit_a_rows,
    _unit_b_rows,
)

SRC = Path(__file__).resolve().parents[3]
LIST_JS = SRC / "static" / "js" / "inventory-order-alert-list.js"
LIST_CLIENT_JS = SRC / "static" / "js" / "inventory-order-alert-list-client.js"
LIST_HTML = SRC / "templates" / "inventory_order_alert" / "list.html"
LIST_URL = "/app/production/inventory-order-alert"


@pytest.fixture
def snapshot(db):
    record = SlimsStockImport.objects.create(file_name="test.csv", row_count=5)
    rows = _unit_a_rows() + _unit_b_rows() + [_single_s_row()]
    InventoryOrderAlertSummarySnapshot.objects.create(import_record=record, as_of_date=date(2026, 11, 25), rows=rows)
    return record


def _csv_lines(response) -> list[dict[str, str]]:
    text = b"".join(response.streaming_content).decode("utf-8-sig") if response.streaming else response.content.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def test_v001_list_payload_has_unit_rows(client, admin_user, snapshot):
    client.force_login(admin_user)

    response = client.get(LIST_URL)

    assert len(response.context["list_client_payload"]["rows"]) == 3


def test_v002_confirming_the_representative_confirms_every_item(client, admin_user, snapshot):
    client.force_login(admin_user)

    response = client.put(
        "/api/inventory-order-alert/confirmation",
        data=json.dumps({"custCode": "308", "itemCd": "Q", "status": "confirmed"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert dict(InventoryOrderAlertConfirmation.objects.values_list("item_cd", "status")) == {
        "P": "confirmed",
        "Q": "confirmed",
    }


def test_v003_csv_lines_match_list_rows(client, admin_user, snapshot):
    client.force_login(admin_user)

    assert len(_csv_lines(client.get(f"{LIST_URL}/export.csv"))) == 3


def test_v004_summary_api_filtered_by_a_non_representative_customer(client, admin_user, snapshot):
    """CSV は絞り込みを反映せず常に全件（design.md §6.3）のため、絞り込みはサマリ API で確かめる。"""
    client.force_login(admin_user)

    rows = client.get("/api/inventory-order-alert/summary", {"custCode": "176"}).json()["rows"]

    assert [row["cust_code"] for row in rows] == ["104"]
    assert rows[0]["cust_codes"] == ["104", "176"]


def test_v005_summary_api_returns_unit_rows_with_existing_keys(client, admin_user, snapshot):
    client.force_login(admin_user)

    rows = client.get("/api/inventory-order-alert/summary").json()["rows"]

    assert len(rows) == 3
    for key in ("cust_code", "item_cd", "response_class", "stockout_date"):
        assert key in rows[0]


def test_v006_dashboard_band_counts_unit_rows(snapshot):
    banner = portal_dashboard_usecase().execute()

    assert banner.order_overdue == 1


def test_v007_table_draws_the_other_count_mark():
    source = LIST_CLIENT_JS.read_text(encoding="utf-8")

    assert "function renderUnitMore(" in source
    assert "他${values.length - 1}" in source
    assert "${renderUnitMore(row, column.key)}" in source


def test_v008_detail_dialog_has_the_customer_breakdown():
    html = LIST_HTML.read_text(encoding="utf-8")
    dialog = html.split('<dialog id="ioa-location-dialog"', 1)[1].split("</dialog>", 1)[0]

    assert "ioa-detail-customer-breakdown-body" in dialog
    assert "得意先別内訳" in dialog
    assert "内示推移（月別）" in dialog
    assert "renderCustomerBreakdown(custCode" in LIST_JS.read_text(encoding="utf-8")


def test_v009_filters_use_the_unit_lists():
    source = LIST_CLIENT_JS.read_text(encoding="utf-8")
    block = source.split("function applyListFilters(", 1)[1].split("\n  function ", 1)[0]

    assert 'unitValues(row, "cust_code")' in block
    assert 'unitValues(row, "cust_chrg_psn_cd")' in block
    assert "buildCustChrgCustIndex(memberRows(allRows))" in source


def test_v010_js_does_not_sum_or_pick_the_representative():
    for path in (LIST_JS, LIST_CLIENT_JS):
        source = path.read_text(encoding="utf-8")
        # 代表得意先の選び方（内示の合計）や照合単位の合算を JS で行っていない
        assert "select_representative" not in source
        assert not re.search(r"customer_breakdown[^;\n]*reduce\(", source)
