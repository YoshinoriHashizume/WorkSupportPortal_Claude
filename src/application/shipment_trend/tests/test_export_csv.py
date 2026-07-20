from __future__ import annotations

from application.shipment_trend.domain.value_objects.export_csv import (
    CSV_BASE_COLUMNS,
    build_csv_export,
    build_month_range,
    format_monthly_cell,
    normalize_row_monthly,
)


def _row(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {
        "cust_chrg_psn_cd": "A01",
        "cust_code": "101",
        "cust_name": "テスト",
        "item_cd": "ITEM-1",
        "first_fiscal_year": 2023,
        "change_rate_pct": 50.0,
        "change_qty": 50,
        "monthly": {"2025-04": 100, "2025-05": 50},
    }
    base.update(kwargs)
    return base


def test_csv_base_columns_item_cd_label():
    from application.shipment_trend.domain.value_objects.export_csv import CSV_BASE_COLUMNS
    from application.shipment_trend.domain.value_objects.table_display import COLUMN_LABELS

    assert dict(CSV_BASE_COLUMNS)["item_cd"] == "得意先品番"
    assert COLUMN_LABELS["item_cd"] == "得意先品番"


def test_build_month_range_spans_global_min_to_max():
    rows = [
        _row(monthly={"2025-04": 10}),
        _row(item_cd="ITEM-2", monthly={"2025-06": 20, "2025-08": 30}),
    ]
    assert build_month_range(rows) == ["2025-04", "2025-05", "2025-06", "2025-07", "2025-08"]


def test_format_monthly_cell_returns_empty_when_missing():
    monthly = normalize_row_monthly(_row())
    assert format_monthly_cell(monthly, "2025-04") == "100"
    assert format_monthly_cell(monthly, "2025-03") == ""


def test_build_csv_export_uses_monthly_columns_instead_of_fy_totals():
    rows = [
        _row(monthly={"2025-04": 100, "2025-05": 50}),
        _row(
            item_cd="ITEM-2",
            monthly={"2025-06": 80},
            change_rate_pct=-10.0,
            change_qty=-20,
        ),
    ]
    result = build_csv_export(rows, as_of_date_label="2025/06/01")
    lines = result.content.splitlines()
    header = lines[0].lstrip("\ufeff")
    assert "初年度" in header
    assert "変動率" in header
    assert "初年度出荷合計" not in header
    assert "2025-04" in header
    assert "2025-06" in header
    assert "2025-07" not in header
    assert len(CSV_BASE_COLUMNS) == 7
    row1 = lines[1].split(",")
    assert row1[4] == "2023"
    assert row1[7] == "100"
    assert row1[8] == "50"
    assert row1[9] == ""
    row2 = lines[2].split(",")
    assert row2[7] == ""
    assert row2[9] == "80"


def test_build_csv_export_with_no_monthly_data():
    rows = [_row(monthly={})]
    result = build_csv_export(rows, as_of_date_label="2025/06/01")
    header = result.content.splitlines()[0].lstrip("\ufeff")
    assert header.count(",") == len(CSV_BASE_COLUMNS) - 1
