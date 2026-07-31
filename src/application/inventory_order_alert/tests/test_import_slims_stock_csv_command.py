from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from application.inventory_order_alert.models import SlimsStockImport, SlimsStockSnapshot


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "slims_stock_sample_wkatqt.csv"


@pytest.mark.django_db
@patch("application.inventory_order_alert.infrastructure.persistence.slims_stock_repository.run_summary_aggregation")
def test_import_slims_stock_csv_command(mock_aggregate):
    mock_aggregate.return_value = ("", 0)
    before = SlimsStockImport.objects.count()

    call_command("import_slims_stock_csv", str(FIXTURE))

    assert SlimsStockImport.objects.count() == before + 1
    latest = SlimsStockImport.objects.order_by("-imported_at").first()
    assert latest is not None
    assert latest.file_name == FIXTURE.name
    assert SlimsStockSnapshot.objects.filter(import_record=latest).count() == latest.row_count
    mock_aggregate.assert_called_once()


def test_import_slims_stock_csv_command_missing_file():
    with pytest.raises(CommandError, match="見つかりません"):
        call_command("import_slims_stock_csv", "missing.csv")
