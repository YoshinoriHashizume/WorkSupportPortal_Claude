from __future__ import annotations

import os
from pathlib import Path

from config.settings.base import (
    is_production_settings_module,
    load_dotenv,
    load_repo_env_files,
)


def test_load_dotenv_override_uses_last_value(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("TEST_OVERRIDE_KEY", raising=False)
    env_file = tmp_path / "test.env"
    env_file.write_text("TEST_OVERRIDE_KEY=first\nTEST_OVERRIDE_KEY=second\n", encoding="utf-8")

    load_dotenv(env_file, override=True)

    assert os.environ["TEST_OVERRIDE_KEY"] == "second"


def test_load_dotenv_setdefault_keeps_existing_value(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TEST_SETDEFAULT_KEY", "existing")
    env_file = tmp_path / "test.env"
    env_file.write_text("TEST_SETDEFAULT_KEY=from-file\n", encoding="utf-8")

    load_dotenv(env_file, override=False)

    assert os.environ["TEST_SETDEFAULT_KEY"] == "existing"


def test_is_production_settings_module():
    assert is_production_settings_module("config.settings.production") is True
    assert is_production_settings_module("config.settings.development") is False
    assert is_production_settings_module("config.settings") is False


def test_load_repo_env_files_skips_production_in_development(tmp_path: Path, monkeypatch):
    """開発時は .env.production を読まず、Docker 注入の POSTGRES_* を壊さない。"""
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "config.settings.development")
    monkeypatch.setenv("POSTGRES_PASSWORD", "from-docker")
    monkeypatch.setattr("config.settings.base.REPO_ROOT", tmp_path)

    (tmp_path / ".env.production").write_text(
        "POSTGRES_PASSWORD=from-production\n",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "POSTGRES_PASSWORD=from-dotenv\nEXTRA_DEV_KEY=dev-only\n",
        encoding="utf-8",
    )

    load_repo_env_files()

    assert os.environ["POSTGRES_PASSWORD"] == "from-docker"
    assert os.environ["EXTRA_DEV_KEY"] == "dev-only"


def test_load_repo_env_files_uses_production_override(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "config.settings.production")
    monkeypatch.setenv("POSTGRES_PASSWORD", "from-process")
    monkeypatch.setattr("config.settings.base.REPO_ROOT", tmp_path)

    (tmp_path / ".env.production").write_text(
        "POSTGRES_PASSWORD=from-production\n",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "POSTGRES_PASSWORD=from-dotenv\n",
        encoding="utf-8",
    )

    load_repo_env_files()

    assert os.environ["POSTGRES_PASSWORD"] == "from-production"
