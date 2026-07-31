from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from application.inventory_order_alert.domain.value_objects.slims_stock import (
    WLOCCD_PATTERN,
    SlimsStockLocationLine,
    aggregate_location_lines,
    build_location_summary,
    format_location_detail_csv,
    group_locations_by_item,
    is_target_wloccd,
    parse_location_detail,
    parse_slims_stock_csv,
    read_csv_text,
    resolve_stock_qty_field,
    total_stock_qty,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "slims_stock_sample_wkatqt.csv"


def test_parse_slims_stock_csv_reads_wksbqt_format():
    lines = parse_slims_stock_csv(read_csv_text(FIXTURE))
    assert len(lines) == 5
    assert lines[0].item_cd == "43522-D1020-00"
    assert lines[0].wloccd == "2D0-03-5"
    assert lines[0].stock_qty == Decimal("90")
    assert lines[0].wnyudt == "20161228"


def test_resolve_stock_qty_field_requires_wksbqt():
    header_index = {"WSHOCD": 1, "WLOCCD": 4, "WKATQT": 7, "WKSBQT": 8}
    assert resolve_stock_qty_field(header_index) == "WKSBQT"


def test_parse_slims_stock_csv_keeps_duplicate_locations_as_separate_lines():
    csv_text = read_csv_text(FIXTURE) + read_csv_text(FIXTURE).splitlines()[2] + "\n"
    lines = parse_slims_stock_csv(csv_text)
    grouped = group_locations_by_item(lines)
    item_lines = grouped["43522-D1020-00"]
    assert len(item_lines) == 3
    assert total_stock_qty(item_lines) == Decimal("190")
    aggregated = aggregate_location_lines(item_lines)
    assert len(aggregated) == 2
    by_location = {line.wloccd: line.stock_qty for line in aggregated}
    assert by_location["2D0-03-5"] == Decimal("180")
    assert by_location["2E1-03-4"] == Decimal("10")


def test_group_locations_by_item_for_multiple_wloccd():
    lines = parse_slims_stock_csv(read_csv_text(FIXTURE))
    grouped = group_locations_by_item(lines)
    item_lines = grouped["43522-D1020-00"]
    assert len(item_lines) == 2
    assert total_stock_qty(item_lines) == Decimal("100")
    assert {line.wloccd for line in item_lines} == {"2D0-03-5", "2E1-03-4"}


def test_build_location_summary_single_and_multiple():
    lines = parse_slims_stock_csv(read_csv_text(FIXTURE))
    grouped = group_locations_by_item(lines)
    assert build_location_summary(grouped["51916-60050"]) == "2D0-08-4"
    aggregated = aggregate_location_lines(grouped["43522-D1020-00"])
    assert build_location_summary(aggregated) == "2D0-03-5 他1"


def test_format_location_detail_csv_includes_incoming_date_and_duplicate_rows():
    lines = parse_slims_stock_csv(read_csv_text(FIXTURE))
    grouped = group_locations_by_item(lines)
    detail = format_location_detail_csv(grouped["43522-D1020-00"])
    assert detail == "2D0-03-5=90@20161228;2E1-03-4=10@20161228"

    duplicate_csv = read_csv_text(FIXTURE) + read_csv_text(FIXTURE).splitlines()[2] + "\n"
    duplicate_lines = group_locations_by_item(parse_slims_stock_csv(duplicate_csv))["43522-D1020-00"]
    duplicate_detail = format_location_detail_csv(duplicate_lines)
    assert duplicate_detail.count("2D0-03-5=90@20161228") == 2


def test_format_location_detail_csv_sorts_by_incoming_date_asc():
    lines = [
        SlimsStockLocationLine("A", "2E1-03-4", Decimal("10"), wnyudt="20170101"),
        SlimsStockLocationLine("A", "2D0-03-5", Decimal("90"), wnyudt="20161228"),
        SlimsStockLocationLine("A", "2D0-03-5", Decimal("50"), wnyudt="20170101"),
    ]
    detail = format_location_detail_csv(lines)
    assert detail == "2D0-03-5=90@20161228;2D0-03-5=50@20170101;2E1-03-4=10@20170101"


def test_parse_slims_stock_csv_requires_wloccd_column():
    csv_text = "WSHOCD,WKSBQT\n商品コード,在庫\nA,1\n"
    with pytest.raises(ValueError, match="WLOCCD"):
        parse_slims_stock_csv(csv_text)


def test_parse_slims_stock_csv_excludes_invalid_location():
    extra_row = (
        "10,43522-D1020-00,43522-D1020-00,,INVALID,0,0,99.000,99,0,0,99.000,99,"
        "20161228,,43522-D1020-00,,,,,,,,,,,,A,出荷可,0100,\n"
    )
    lines = parse_slims_stock_csv(read_csv_text(FIXTURE) + extra_row)
    assert len(lines) == 5
    assert total_stock_qty(group_locations_by_item(lines)["43522-D1020-00"]) == Decimal("100")


def test_is_target_wloccd_matches_slims_format():
    assert is_target_wloccd("2D0-03-5") is True
    assert is_target_wloccd("2E1-03-4") is True
    assert is_target_wloccd("INVALID") is False
    assert is_target_wloccd("2D0-3-5") is False


def test_parse_slims_stock_csv_uses_wksbqt_not_wkatqt():
    csv_text = (
        "WLOCCD,WSHOCD,WMFGLT,WKATQT,WKSBQT\n"
        "ロケーション,商品コード,製造ロット,引当可能バラ数,引当可能総バラ数\n"
        "2D0-03-5,43522-D1020-00,43522-D1020-00,90,120\n"
    )
    lines = parse_slims_stock_csv(csv_text)
    assert lines[0].stock_qty == Decimal("120")


def test_parse_slims_stock_csv_filters_non_target_wloccd():
    csv_text = (
        "WLOCCD,WSHOCD,WMFGLT,WKSBQT\n"
        "ロケーション,商品コード,製造ロット,引当可能総バラ数\n"
        "2D0-03-5,43522-D1020-00,43522-D1020-00,90\n"
        "INVALID,43522-D1020-00,43522-D1020-00,50\n"
        "2D0-3-5,43522-D1020-00,43522-D1020-00,30\n"
    )
    lines = parse_slims_stock_csv(csv_text)
    assert len(lines) == 1
    assert lines[0].wloccd == "2D0-03-5"


def test_parse_slims_stock_csv_parses_wmfglt():
    csv_text = (
        "WLOCCD,WSHOCD,WMFGLT,WKSBQT\n"
        "ロケーション,商品コード,製造ロット,引当可能総バラ数\n"
        "2D0-03-5,43522-D1020-00,43522-D1020-00,90\n"
    )
    lines = parse_slims_stock_csv(csv_text)
    assert lines[0].wmfglt == "43522-D1020-00"


def test_parse_slims_stock_csv_requires_stock_qty_column():
    csv_text = "WSHOCD,WLOCCD,WSOJQT\n商品コード,ロケーション,実在庫\nA,2D0-03-5,1\n"
    with pytest.raises(ValueError, match="WKSBQT"):
        parse_slims_stock_csv(csv_text)


def test_parse_location_detail_splits_multiple_locations_with_incoming_date():
    detail = parse_location_detail("2D0-03-5=90@20161228;2E1-03-4=10@20161228")
    assert detail == [
        {"wloccd": "2D0-03-5", "stock_qty": "90", "wnyudt": "20161228"},
        {"wloccd": "2E1-03-4", "stock_qty": "10", "wnyudt": "20161228"},
    ]


def test_parse_location_detail_supports_legacy_format_without_incoming_date():
    detail = parse_location_detail("2D0-03-5=90;2E1-03-4=10")
    assert detail == [
        {"wloccd": "2D0-03-5", "stock_qty": "90", "wnyudt": ""},
        {"wloccd": "2E1-03-4", "stock_qty": "10", "wnyudt": ""},
    ]


def test_parse_location_detail_returns_empty_for_blank():
    assert parse_location_detail("") == []
    assert parse_location_detail("invalid") == []


def test_wloccd_pattern_is_exported():
    assert WLOCCD_PATTERN.pattern
