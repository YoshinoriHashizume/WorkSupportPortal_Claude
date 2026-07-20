from __future__ import annotations

from application.gonenkukumi.infrastructure.oracle.client import use_mock


def test_use_mock_true_values(monkeypatch):
    for value in ("true", "TRUE", "1", "yes", "on", " Yes "):
        monkeypatch.setenv("ORACLE_USE_MOCK", value)
        assert use_mock() is True


def test_use_mock_false_and_typos_use_real_connection(monkeypatch):
    for value in ("false", "", "0", "no", "tru", "false ", "mock"):
        monkeypatch.setenv("ORACLE_USE_MOCK", value)
        assert use_mock() is False
    monkeypatch.delenv("ORACLE_USE_MOCK", raising=False)
    assert use_mock() is False
