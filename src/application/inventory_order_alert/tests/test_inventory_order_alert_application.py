from __future__ import annotations

import pytest

from application.inventory_order_alert.use_cases.import_stock import ImportStock


def test_import_stock_usecase_delegates_to_injected_importer():
    captured: dict[str, object] = {}

    def fake_import(text, *, user=None, file_name=""):
        captured["text"] = text
        captured["file_name"] = file_name
        return object()

    use_case = ImportStock(fake_import)
    use_case.execute(b"item,loc,qty\nA,B,1", file_name="sample.csv")
    assert "item,loc,qty" in str(captured["text"])
    assert captured["file_name"] == "sample.csv"


def test_import_stock_usecase_decodes_cp932_bytes():
    captured: dict[str, object] = {}

    def fake_import(text, *, user=None, file_name=""):
        captured["text"] = text
        return object()

    ImportStock(fake_import).execute("品目".encode("cp932"), file_name="sample.csv")
    assert captured["text"] == "品目"
