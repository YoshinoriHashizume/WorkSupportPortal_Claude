from __future__ import annotations

import os
from pathlib import Path

from config.settings import load_dotenv


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
