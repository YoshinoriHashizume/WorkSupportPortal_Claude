"""仕入先マスタ（M_VEND_CTRL）の参照。spec/12 test-design.md TC-DSE-I-010〜013。DB・実 Oracle は使わない。"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from application.inventory_order_alert.domain.value_objects.errors import VendorLookupUnavailableError
from application.inventory_order_alert.infrastructure.oracle import vendor_lookup
from application.sales.infrastructure.oracle.client import OracleNotConfiguredError, OracleQueryError


def _fake_connection(rows):
    cursor = MagicMock()
    cursor.description = [("VEND_CD",), ("VEND_NAME",)]
    cursor.fetchall.return_value = rows
    connection = MagicMock()
    connection.cursor.return_value = cursor
    opened: list[bool] = []

    @contextmanager
    def oracle_connection():
        opened.append(True)
        yield connection

    return oracle_connection, cursor, opened


@pytest.fixture(autouse=True)
def _real_mode(monkeypatch):
    monkeypatch.setattr(vendor_lookup, "use_mock", lambda: False)


def test_i010_returns_names_of_found_codes_with_bind_variables(monkeypatch):
    oracle_connection, cursor, _ = _fake_connection([("9100", "丸栄豊田")])
    monkeypatch.setattr(vendor_lookup, "oracle_connection", oracle_connection)

    names = vendor_lookup.lookup_vendor_names(["9100", "9999"])

    assert names == {"9100": "丸栄豊田"}
    sql, binds = cursor.execute.call_args.args
    assert sql.strip().upper().startswith("SELECT")
    assert "M_VEND_CTRL" in sql
    assert "9100" not in sql
    assert sorted(binds.values()) == ["9100", "9999"]


def test_i011_no_codes_does_not_connect(monkeypatch):
    oracle_connection, _, opened = _fake_connection([])
    monkeypatch.setattr(vendor_lookup, "oracle_connection", oracle_connection)

    assert vendor_lookup.lookup_vendor_names([]) == {}
    assert opened == []


@pytest.mark.parametrize(
    "error",
    [OracleNotConfiguredError("未設定"), OracleQueryError("ORA-12541"), ConnectionError("refused")],
)
def test_i012_oracle_errors_are_wrapped_as_unavailable(monkeypatch, error):
    @contextmanager
    def failing_connection():
        raise error
        yield  # pragma: no cover

    monkeypatch.setattr(vendor_lookup, "oracle_connection", failing_connection)

    with pytest.raises(VendorLookupUnavailableError):
        vendor_lookup.lookup_vendor_names(["9100"])


def test_i013_mock_mode_treats_all_codes_as_existing(monkeypatch):
    oracle_connection, _, opened = _fake_connection([])
    monkeypatch.setattr(vendor_lookup, "oracle_connection", oracle_connection)
    monkeypatch.setattr(vendor_lookup, "use_mock", lambda: True)

    assert vendor_lookup.lookup_vendor_names(["9100", "9999"]) == {"9100": "9100", "9999": "9999"}
    assert opened == []
