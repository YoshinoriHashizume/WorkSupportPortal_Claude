from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from apps.inventory_order_alert.infrastructure.persistence.slims_stock_repository import (
    import_slims_csv_text,
    load_latest_stock_lines,
)
from apps.inventory_order_alert.domain.slims_stock import read_csv_text
from apps.inventory_order_alert.models import SlimsStockImport, SlimsStockSnapshot

FIXTURE = Path("tests/fixtures/slims_stock_sample_wkatqt.csv")


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="10010", last_name="取込", first_name="担当")


@pytest.mark.django_db
@patch("apps.inventory_order_alert.infrastructure.persistence.slims_stock_repository.run_summary_aggregation")
def test_import_slims_csv_text_replaces_snapshot(mock_aggregate, user):
    mock_aggregate.return_value = ("", 0)
    text = read_csv_text(FIXTURE)
    info = import_slims_csv_text(text, user=user, file_name="sample.csv")

    assert info.row_count == 5
    assert SlimsStockImport.objects.count() == 1
    assert SlimsStockSnapshot.objects.count() == 5
    mock_aggregate.assert_called_once()

    lines, loaded = load_latest_stock_lines()
    assert loaded is not None
    assert loaded.file_name == "sample.csv"
    grouped_qty = sum(line.stock_qty for line in lines if line.item_cd == "43522-D1020-00")
    assert grouped_qty == Decimal("100")


@pytest.mark.django_db
@patch("apps.inventory_order_alert.infrastructure.persistence.slims_stock_repository.run_summary_aggregation")
def test_import_slims_csv_text_replaces_previous_snapshot(mock_aggregate, user):
    mock_aggregate.return_value = ("", 0)
    text = read_csv_text(FIXTURE)
    import_slims_csv_text(text, user=user, file_name="first.csv")
    import_slims_csv_text(text, user=user, file_name="second.csv")

    assert SlimsStockImport.objects.count() == 2
    assert SlimsStockSnapshot.objects.count() == 5
    latest = SlimsStockImport.objects.order_by("-imported_at").first()
    assert latest.file_name == "second.csv"
