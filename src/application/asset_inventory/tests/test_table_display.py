from __future__ import annotations

from application.asset_inventory.domain.value_objects.list_query import build_list_page_query_string
from application.asset_inventory.domain.repositories.ports import ReconcileRow, RowTone, MatchStatus
from application.asset_inventory.domain.value_objects.table_display import (
    DEFAULT_SORT_SPECS,
    PaginatedRows,
    SortSpec,
    paginate_rows,
    parse_page_size,
    parse_sort_specs,
    sort_rows,
    sort_spec_label,
)


def _row(asset_number: str, branch_number: str = "0000") -> ReconcileRow:
    return ReconcileRow(
        match_status=MatchStatus.MATCHED,
        row_tone=RowTone.MATCH_CLEAN,
        status_label="棚卸済み",
        tone_label="一致",
        asset_number=asset_number,
        branch_number=branch_number,
        site_name="",
        manufacturer="",
        model_name="",
        serial_number="",
        old_asset_number="",
        usage_category="",
        summary="",
        plate_created="",
        inventory_operator="",
        inventory_datetime="",
    )


def test_TC_AIV_DOM_080_paginate_rows_range():
    rows = tuple(_row(str(index)) for index in range(1, 6))
    paginated = paginate_rows(rows, page=1, page_size=2)
    assert paginated.total_count == 5
    assert paginated.total_pages == 3
    assert paginated.start_index == 1
    assert paginated.end_index == 2
    assert paginated.has_next is True
    assert paginated.has_previous is False


def test_TC_AIV_DOM_081_paginate_rows_last_page():
    rows = tuple(_row(str(index)) for index in range(1, 6))
    paginated = paginate_rows(rows, page=3, page_size=2)
    assert paginated.start_index == 5
    assert paginated.end_index == 5
    assert paginated.has_next is False
    assert paginated.has_previous is True


def test_TC_AIV_DOM_082_parse_page_size():
    options = (20, 50, 100)
    assert parse_page_size("50", options=options, default=20) == 50
    assert parse_page_size("999", options=options, default=20) == 20
    assert parse_page_size("bad", options=options, default=20) == 20


def test_TC_AIV_DOM_083_build_list_page_query_string():
    query = build_list_page_query_string(
        management_id="1",
        status="matched",
        site_filter="宮崎工場",
        plate_filter="1",
        sort_specs=DEFAULT_SORT_SPECS,
        page=2,
        page_size=50,
    )
    assert "managementId=1" in query
    assert "status=matched" in query
    assert "plate=1" in query
    assert query.count("site=") == 1
    assert "site=%E5%AE%AE%E5%B4%8E%E5%B7%A5%E5%A0%B4" in query
    assert "page=2" in query
    assert "page_size=50" in query
    assert "sort=asset_number%2Cbranch_number" in query
    assert "dir=asc%2Casc" in query


def test_TC_AIV_DOM_084_build_list_page_query_string_asset_number():
    query = build_list_page_query_string(
        management_id="1",
        status="all",
        site_filter="all",
        plate_filter="all",
        asset_number_filter="5262",
        sort_specs=DEFAULT_SORT_SPECS,
        page=1,
        page_size=50,
    )
    assert "assetNumber=5262" in query

def test_TC_AIV_DOM_086_parse_sort_specs_default():
    specs = parse_sort_specs({})
    assert specs == DEFAULT_SORT_SPECS


def test_TC_AIV_DOM_087_parse_sort_specs_multi():
    specs = parse_sort_specs({"sort": "site_name,asset_number", "dir": "desc,asc"})
    assert specs == (
        SortSpec("site_name", "desc"),
        SortSpec("asset_number", "asc"),
    )


def test_TC_AIV_DOM_088_sort_rows_multi_column():
    rows = (
        _row("2", "0001"),
        _row("1", "0002"),
        _row("1", "0001"),
    )
    sorted_rows = sort_rows(rows, (SortSpec("asset_number", "asc"), SortSpec("branch_number", "asc")))
    assert [row.asset_number for row in sorted_rows] == ["1", "1", "2"]
    assert [row.branch_number for row in sorted_rows] == ["0001", "0002", "0001"]


def test_TC_AIV_DOM_089_sort_spec_label():
    assert sort_spec_label(SortSpec("asset_number", "asc")) == "資産番号（昇順）"
    assert sort_spec_label(SortSpec("tone_label", "desc")) == "変化状況（降順）"


def test_TC_AIV_DOM_08B_sort_rows_by_acquisition_date_empty_last():
    rows = (
        ReconcileRow(
            match_status=MatchStatus.MATCHED,
            row_tone=RowTone.MATCH_CLEAN,
            status_label="棚卸済み",
            tone_label="一致",
            asset_number="1",
            branch_number="0",
            site_name="",
            manufacturer="",
            model_name="",
            serial_number="",
            old_asset_number="",
            usage_category="",
            summary="",
            plate_created="",
            inventory_operator="",
            inventory_datetime="",
            asset_acquisition_date="",
        ),
        ReconcileRow(
            match_status=MatchStatus.MATCHED,
            row_tone=RowTone.MATCH_CLEAN,
            status_label="棚卸済み",
            tone_label="一致",
            asset_number="2",
            branch_number="0",
            site_name="",
            manufacturer="",
            model_name="",
            serial_number="",
            old_asset_number="",
            usage_category="",
            summary="",
            plate_created="",
            inventory_operator="",
            inventory_datetime="",
            asset_acquisition_date="2026/03/01",
        ),
        ReconcileRow(
            match_status=MatchStatus.MATCHED,
            row_tone=RowTone.MATCH_CLEAN,
            status_label="棚卸済み",
            tone_label="一致",
            asset_number="3",
            branch_number="0",
            site_name="",
            manufacturer="",
            model_name="",
            serial_number="",
            old_asset_number="",
            usage_category="",
            summary="",
            plate_created="",
            inventory_operator="",
            inventory_datetime="",
            asset_acquisition_date="2025/12/31",
        ),
    )
    asc_rows = sort_rows(rows, (SortSpec("asset_acquisition_date", "asc"),))
    assert [row.asset_number for row in asc_rows] == ["3", "2", "1"]

    desc_rows = sort_rows(rows, (SortSpec("asset_acquisition_date", "desc"),))
    assert [row.asset_number for row in desc_rows] == ["2", "3", "1"]


def test_TC_AIV_DOM_08A_sort_rows_by_tone_label():
    rows = (
        ReconcileRow(
            match_status=MatchStatus.MATCHED,
            row_tone=RowTone.MATCH_DIFF,
            status_label="棚卸済み",
            tone_label="差異",
            asset_number="1",
            branch_number="0001",
            site_name="",
            manufacturer="",
            model_name="",
            serial_number="",
            old_asset_number="",
            usage_category="",
            summary="",
            plate_created="",
            inventory_operator="",
            inventory_datetime="",
        ),
        ReconcileRow(
            match_status=MatchStatus.MATCHED,
            row_tone=RowTone.MATCH_CLEAN,
            status_label="棚卸済み",
            tone_label="一致",
            asset_number="2",
            branch_number="0001",
            site_name="",
            manufacturer="",
            model_name="",
            serial_number="",
            old_asset_number="",
            usage_category="",
            summary="",
            plate_created="",
            inventory_operator="",
            inventory_datetime="",
        ),
    )
    sorted_rows = sort_rows(rows, (SortSpec("tone_label", "asc"),))
    assert [row.tone_label for row in sorted_rows] == ["一致", "差異"]
