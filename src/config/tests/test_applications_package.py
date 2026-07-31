from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]  # = src/


def test_application_directory_exists():
    assert (ROOT / "application").is_dir()


def test_legacy_apps_directory_is_removed():
    assert not (ROOT / "apps").exists()


def test_legacy_applications_directory_is_removed():
    assert not (ROOT / "applications").exists()


def test_installed_apps_use_application_prefix():
    content = (ROOT / "config" / "settings" / "base.py").read_text(encoding="utf-8")
    assert '"application.identity"' in content
    assert '"application.portal"' in content
    assert '"apps.identity"' not in content
    assert '"applications.identity"' not in content
