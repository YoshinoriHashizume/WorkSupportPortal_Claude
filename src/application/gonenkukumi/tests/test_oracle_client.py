from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from application.gonenkukumi.infrastructure.oracle.client import (
    oracle_config,
    oracle_connect_timeout_seconds,
    oracle_connection,
)


def test_oracle_connect_timeout_seconds_defaults_to_five(monkeypatch):
    monkeypatch.delenv("ORACLE_CONNECT_TIMEOUT_SECONDS", raising=False)
    assert oracle_connect_timeout_seconds() == 5.0


def test_oracle_connect_timeout_seconds_invalid_value_defaults_to_five(monkeypatch):
    monkeypatch.setenv("ORACLE_CONNECT_TIMEOUT_SECONDS", "invalid")
    assert oracle_connect_timeout_seconds() == 5.0


def test_oracle_connect_timeout_seconds_negative_becomes_zero(monkeypatch):
    monkeypatch.setenv("ORACLE_CONNECT_TIMEOUT_SECONDS", "-3")
    assert oracle_connect_timeout_seconds() == 0.0


def test_oracle_config_ignores_gonenkukumi_company_cd(monkeypatch):
    monkeypatch.setenv("GONENKUKUMI_COMPANY_CD", "99")
    monkeypatch.delenv("MARI_COMPANY_CD", raising=False)
    monkeypatch.setenv("ORACLE_HOST", "192.168.3.204")
    monkeypatch.setenv("ORACLE_PORT", "1521")
    monkeypatch.setenv("ORACLE_SID", "EXPJ")
    monkeypatch.setenv("ORACLE_USER", "EXPJ")
    monkeypatch.setenv("ORACLE_PASSWORD", "secret")

    assert oracle_config()["company_cd"] == ""


def test_oracle_config_uses_mari_company_cd_when_set(monkeypatch):
    monkeypatch.delenv("GONENKUKUMI_COMPANY_CD", raising=False)
    monkeypatch.setenv("MARI_COMPANY_CD", "01")
    monkeypatch.setenv("ORACLE_HOST", "192.168.3.204")
    monkeypatch.setenv("ORACLE_PORT", "1521")
    monkeypatch.setenv("ORACLE_SID", "EXPJ")
    monkeypatch.setenv("ORACLE_USER", "EXPJ")
    monkeypatch.setenv("ORACLE_PASSWORD", "secret")

    assert oracle_config()["company_cd"] == "01"


@patch("application.gonenkukumi.infrastructure.oracle.client.oracle_config")
def test_oracle_connection_passes_tcp_connect_timeout(mock_config, monkeypatch):
    monkeypatch.setenv("ORACLE_CONNECT_TIMEOUT_SECONDS", "7")

    mock_config.return_value = {
        "host": "db.example",
        "port": "1521",
        "sid": "ORCL",
        "service_name": "",
        "user": "user",
        "password": "pass",
        "company_cd": "",
        "thick_mode": "false",
        "client_lib_dir": "",
    }

    fake_oracledb = MagicMock()
    fake_connection = MagicMock()
    fake_oracledb.makedsn.return_value = "dsn"
    fake_oracledb.connect.return_value = fake_connection

    with patch.dict("sys.modules", {"oracledb": fake_oracledb}):
        with oracle_connection() as connection:
            assert connection is fake_connection

    fake_oracledb.connect.assert_called_once_with(
        user="user",
        password="pass",
        dsn="dsn",
        tcp_connect_timeout=7.0,
    )
    fake_connection.close.assert_called_once()


@patch("application.gonenkukumi.infrastructure.oracle.client.oracle_config")
def test_oracle_connection_omits_timeout_when_zero(mock_config, monkeypatch):
    monkeypatch.setenv("ORACLE_CONNECT_TIMEOUT_SECONDS", "0")

    mock_config.return_value = {
        "host": "db.example",
        "port": "1521",
        "sid": "ORCL",
        "service_name": "",
        "user": "user",
        "password": "pass",
        "company_cd": "",
        "thick_mode": "false",
        "client_lib_dir": "",
    }

    fake_oracledb = MagicMock()
    fake_connection = MagicMock()
    fake_oracledb.makedsn.return_value = "dsn"
    fake_oracledb.connect.return_value = fake_connection

    with patch.dict("sys.modules", {"oracledb": fake_oracledb}):
        with oracle_connection():
            pass

    assert "tcp_connect_timeout" not in fake_oracledb.connect.call_args.kwargs


def test_oracle_config_requires_sid_or_service_name(monkeypatch):
    monkeypatch.setenv("ORACLE_HOST", "db.example")
    monkeypatch.setenv("ORACLE_PORT", "1521")
    monkeypatch.setenv("ORACLE_USER", "user")
    monkeypatch.setenv("ORACLE_PASSWORD", "pass")
    monkeypatch.delenv("ORACLE_SID", raising=False)
    monkeypatch.delenv("ORACLE_SERVICE_NAME", raising=False)

    with pytest.raises(Exception, match="sid"):
        oracle_config()
