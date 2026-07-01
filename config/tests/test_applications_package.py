from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_applications_directory_exists():
    assert (ROOT / "applications").is_dir()


def test_legacy_apps_directory_is_removed():
    assert not (ROOT / "apps").exists()


def test_installed_apps_use_applications_prefix():
    content = (ROOT / "config" / "settings.py").read_text(encoding="utf-8")
    assert '"applications.identity"' in content
    assert '"apps.identity"' not in content
