from __future__ import annotations

from datetime import date

import pytest

from apps.receipt_comparison.domain.comparison_type import FINISHED_PRODUCT
from apps.receipt_comparison.domain.comparison_urls import comparison_url_path, parse_date
from apps.receipt_comparison.usecase.usecase_comparison_page import ComparisonPageUsecase, comparison_export_filename


class FakeComparisonResultRepository:
    def existing_rows_for_display(
        self,
        comparison_type: str,
        supplier_id: int,
        start_date: date,
        end_date: date,
    ) -> list[object]:
        return []

    def existing_rows_for_comparison(
        self,
        comparison_type: str,
        supplier_id: int,
        start_date: date,
        end_date: date,
    ) -> list[object]:
        return []

    def save_comparison_rows(
        self,
        comparison_type: str,
        supplier_id: int,
        file_import_id: int,
        rows: list[object],
        user_id: int,
    ) -> None:
        return None

    def update_existing_results_from_post(
        self,
        comparison_type: str,
        result_ids: list[str],
        post_values: dict[str, str],
        user_id: int,
    ) -> None:
        return None


def test_comparison_export_filename_uses_type_label():
    assert comparison_export_filename(FINISHED_PRODUCT).startswith("検収書比較結果(完成品)_")


def test_comparison_page_usecase_builds_context_without_supplier():
    usecase = ComparisonPageUsecase(
        FakeComparisonResultRepository(),
        lambda comparison_type: [],
        comparison_base_path="/comparison",
    )
    context = usecase.build_context(
        type_slug="finished-product",
        comparison_type=FINISHED_PRODUCT,
        supplier=None,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        rows=[],
        has_pending=False,
        results_panel_active=False,
        sort_key="receipt_flag",
        sort_direction="asc",
    )
    assert context.receipt_file_accept == ".csv"
    assert context.comparison_query.startswith("type=finished-product")


def test_comparison_url_path_includes_sort_params():
    url = comparison_url_path(
        "/comparison",
        FINISHED_PRODUCT,
        3,
        date(2026, 6, 1),
        date(2026, 6, 30),
        display=1,
        sort_key="mari_item_cd",
        sort_direction="desc",
    )
    assert "supplier_id=3" in url
    assert "display=1" in url
    assert "sort=mari_item_cd" in url
    assert "dir=desc" in url


def test_parse_date_returns_none_for_invalid():
    assert parse_date("invalid") is None
