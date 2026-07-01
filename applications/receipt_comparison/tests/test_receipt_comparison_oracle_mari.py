from __future__ import annotations

import inspect
from pathlib import Path

from applications.receipt_comparison.infrastructure.oracle import client as oracle_client


def test_finished_product_mari_sql_returns_detail_rows():
    source = inspect.getsource(oracle_client.fetch_finished_product_rows)
    assert "SUM(T_SHIP1.SHIP_QTY)" not in source
    assert "SUM(SALES_QTY)" not in source
    assert "GROUP BY" not in source
    assert "T_SHIP1.SHIP_QTY AS SHIP_QTY" in source
    assert "SALES_QTY AS SHIP_QTY" in source
    assert "T_SHIP1.SHIP_QTY > 0" in source
    assert "SALES_QTY > 0" in source


def test_verify_mari_shipment_aggregation_script_exists():
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "verify_mari_shipment_aggregation.py"
    script = script_path.read_text(encoding="utf-8")
    assert "LEGACY_T_SHIP_SQL" in script
    assert "DJANGO_T_SHIP_SQL" in script
    assert "265623-0492" in script
    assert "SUM(T_SHIP1.SHIP_QTY)" not in script.split("DJANGO_T_SHIP_SQL", 1)[1]
