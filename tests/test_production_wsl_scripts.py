from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_wsl_install_docker_engine_script_exists():
    path = ROOT / "scripts" / "wsl" / "install-docker-engine.sh"
    assert path.is_file()
    source = read("scripts/wsl/install-docker-engine.sh")
    assert "docker.io" in source
    assert "docker-compose-v2" in source


def test_wsl_start_production_script_uses_prod_compose_and_env_production():
    source = read("scripts/wsl/start-production.sh")
    assert "docker-compose.prod.yml" in source
    assert ".env.production" in source
    assert "POSTGRES_PASSWORD" in source


def test_wsl_bootstrap_production_admin_script_invokes_management_command():
    source = read("scripts/wsl/bootstrap-production-admin.sh")
    assert "bootstrap_production_admin" in source
    assert "docker compose" in source


def test_windows_install_wsl_ubuntu_script_enables_wsl_features():
    path = ROOT / "scripts" / "windows" / "Install-WslUbuntu.ps1"
    assert path.is_file()
    source = read("scripts/windows/Install-WslUbuntu.ps1")
    assert "Microsoft-Windows-Subsystem-Linux" in source
    assert "wsl --install" in source
