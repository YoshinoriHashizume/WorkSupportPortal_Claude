from __future__ import annotations

from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (SRC_ROOT / path).read_text(encoding="utf-8")


def test_wsl_install_docker_engine_script_exists():
    path = SRC_ROOT / "scripts" / "wsl" / "install-docker-engine.sh"
    assert path.is_file()
    source = read("scripts/wsl/install-docker-engine.sh")
    assert "docker.io" in source
    assert "docker-compose-v2" in source


def test_wsl_start_production_script_uses_prod_compose_and_env_production():
    source = read("scripts/wsl/start-production.sh")
    assert "docker-compose.production.yaml" in source or "docker-compose.prod.yml" in source
    assert ".env.production" in source
    assert "POSTGRES_PASSWORD" in source


def test_wsl_bootstrap_production_admin_script_invokes_management_command():
    source = read("scripts/wsl/bootstrap-production-admin.sh")
    assert "bootstrap_production_admin" in source
    assert "docker compose" in source
    assert "exec web-app" in source
    assert "exec django_app" not in source
    assert "--env-file .env.production" in source


def test_windows_install_wsl_ubuntu_script_enables_wsl_features():
    path = SRC_ROOT / "scripts" / "windows" / "Install-WslUbuntu.ps1"
    assert path.is_file()
    source = read("scripts/windows/Install-WslUbuntu.ps1")
    assert "Microsoft-Windows-Subsystem-Linux" in source
    assert "wsl --install" in source
