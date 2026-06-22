from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_requirements_windows_prod_uses_waitress_not_gunicorn():
    lines = {
        line.strip()
        for line in read("requirements-windows-prod.txt").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    assert "waitress" in lines
    assert "whitenoise" in lines
    assert "gunicorn" not in lines
    assert "pytest" not in lines


def test_start_production_app_ps1_uses_waitress_and_env_production():
    source = read("scripts/windows/Start-ProductionApp.ps1")
    assert ".env.production" in source
    assert "AUTH_DEV_MODE" in source
    assert "waitress" in source
    assert "migrate" in source
    assert "collectstatic" in source
    assert "check_production_env" in source
    assert "DATABASE_URL" in source


def test_start_production_app_ps1_is_ascii_only_for_windows_powershell():
    source = read("scripts/windows/Start-ProductionApp.ps1")
    source.encode("ascii")


def test_start_production_app_cmd_launches_powershell_with_noexit():
    source = read("scripts/windows/Start-ProductionApp.cmd")
    assert "Start-ProductionApp.ps1" in source
    assert "-NoExit" in source


def test_settings_loads_env_production():
    source = read("config/settings.py")
    assert 'load_dotenv(BASE_DIR / ".env.production", override=True)' in source


def test_env_production_example_documents_windows_direct_run():
    source = read(".env.production.example")
    assert "§10.3" in source
    assert "DATABASE_URL" in source
