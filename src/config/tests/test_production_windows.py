from __future__ import annotations

from pathlib import Path

from config.repo_paths import repo_root


SRC_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = repo_root(Path(__file__).resolve())


def read_src(path: str) -> str:
    return (SRC_ROOT / path).read_text(encoding="utf-8")


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_requirements_prod_is_single_runtime_source_without_servers_or_pytest():
    prod = read_repo("requirements-prod.txt")
    assert "Django==5.2" in prod
    assert "psycopg2-binary" in prod
    assert "oracledb" in prod
    assert "whitenoise" in prod
    assert "gunicorn" not in prod
    assert "waitress" not in prod
    assert "pytest" not in prod


def test_requirements_docker_extends_prod_with_gunicorn_and_dev():
    docker = read_repo("requirements-docker.txt")
    assert "-r requirements-prod.txt" in docker
    assert "gunicorn" in docker
    assert "-r requirements-dev.txt" in docker


def test_requirements_windows_prod_uses_waitress_not_gunicorn():
    lines = [
        line.strip()
        for line in read_repo("requirements-windows-prod.txt").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert "-r requirements-prod.txt" in lines
    assert any(line.startswith("waitress") for line in lines)
    assert not any(line.startswith("gunicorn") for line in lines)
    assert not any(line.startswith("pytest") for line in lines)


def test_dockerfile_installs_requirements_docker_from_repo_root():
    source = read_repo("docker/django/Dockerfile")
    assert "requirements-docker.lock.txt" in source
    assert "requirements-prod.txt" in source
    assert "uv pip install" in source
    assert "-r requirements-docker.lock.txt" in source
    assert "docker/django/requirements.txt" not in source or "COPY ./requirements" in source


def test_start_production_app_ps1_uses_waitress_and_env_production():
    source = read_src("scripts/windows/Start-ProductionApp.ps1")
    assert ".env.production" in source
    assert "AUTH_DEV_MODE" in source
    assert "waitress" in source
    assert "migrate" in source
    assert "collectstatic" in source
    assert "check_production_env" in source
    assert 'Join-Path $Root "src"' in source or "src\\manage.py" in source or 'Join-Path $Src "manage.py"' in source


def test_start_production_app_ps1_is_ascii_only_for_windows_powershell():
    source = read_src("scripts/windows/Start-ProductionApp.ps1")
    source.encode("ascii")


def test_start_production_app_cmd_launches_powershell_with_noexit():
    source = read_src("scripts/windows/Start-ProductionApp.cmd")
    assert "Start-ProductionApp.ps1" in source
    assert "-NoExit" in source


def test_settings_loads_env_production_from_repo_root():
    source = read_src("config/settings/base.py")
    assert "def load_repo_env_files" in source
    assert 'load_dotenv(REPO_ROOT / ".env.production", override=True)' in source
    assert "is_production_settings_module" in source


def test_env_production_example_disables_debug():
    source = read_repo(".env.production.example")
    assert "DEBUG=False" in source or "DJANGO_DEBUG=false" in source
    assert "AUTH_DEV_MODE=false" in source
