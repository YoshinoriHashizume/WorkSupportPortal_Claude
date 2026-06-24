from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.portal.management.commands.check_production_env import mask_database_url
from config.settings import load_dotenv

migration_module = importlib.import_module(
    "apps.receipt_comparison.migrations.0004_supplied_parts_customer_code"
)


def test_mask_database_url_hides_password():
    masked = mask_database_url("postgresql://user:secret@localhost:5432/db")
    assert masked == "postgresql://user:***@localhost:5432/db"


def test_load_dotenv_reads_utf8_bom_file(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("TEST_BOM_KEY", raising=False)
    env_file = tmp_path / "test.env"
    env_file.write_bytes(b"\xef\xbb\xbfTEST_BOM_KEY=from-bom-file\n")

    load_dotenv(env_file, override=True)

    assert os.environ["TEST_BOM_KEY"] == "from-bom-file"


def test_drop_legacy_vendor_unique_constraint_skips_sqlite():
    class FakeConnection:
        vendor = "sqlite"

    class FakeEditor:
        connection = FakeConnection()
        executed: list[str] = []

        def execute(self, sql: str) -> None:
            self.executed.append(sql)

    editor = FakeEditor()
    migration_module.drop_legacy_vendor_unique_constraint(None, editor)
    assert editor.executed == []


def test_drop_legacy_vendor_unique_constraint_runs_on_postgresql():
    class FakeConnection:
        vendor = "postgresql"

    class FakeEditor:
        connection = FakeConnection()
        executed: list[str] = []

        def execute(self, sql: str) -> None:
            self.executed.append(sql)

    editor = FakeEditor()
    migration_module.drop_legacy_vendor_unique_constraint(None, editor)
    assert len(editor.executed) == 1
    assert "DROP CONSTRAINT" in editor.executed[0]


@pytest.mark.django_db
def test_check_production_env_reports_postgresql(capsys, monkeypatch, settings):
    settings.DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "worksupportportal",
            "USER": "worksupportportal",
            "PASSWORD": "secret",
            "HOST": "localhost",
            "PORT": "5432",
        }
    }
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://worksupportportal:secret@localhost:5432/worksupportportal",
    )
    call_command("check_production_env")

    output = capsys.readouterr().out
    assert "PostgreSQL 設定 OK" in output
    assert "postgresql://worksupportportal:***@" in output
