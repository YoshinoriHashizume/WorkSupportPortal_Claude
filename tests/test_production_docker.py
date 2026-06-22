from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_dockerfile_prod_uses_gunicorn_and_collectstatic():
    source = read("Dockerfile.prod")
    assert "requirements-prod.txt" in source
    assert "collectstatic" in source
    assert "entrypoint-prod.sh" in source
    assert "runserver" not in source
    assert "bootstrap_local_dev" not in source


def test_entrypoint_prod_rejects_auth_dev_mode():
    source = read("docker/entrypoint-prod.sh")
    assert "AUTH_DEV_MODE" in source
    assert "gunicorn config.wsgi:application" in source
    assert "bootstrap_local_dev" not in source
    assert "POSTGRES_PASSWORD must be set in .env.production" in source
    assert "DATABASE_URL=" in source


def test_docker_compose_prod_reads_env_production_via_env_file():
    source = read("docker-compose.prod.yml")
    assert source.count("env_file:") >= 2
    assert ".env.production" in source
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD" not in source


def test_docker_compose_prod_has_no_source_volume_mount():
    source = read("docker-compose.prod.yml")
    assert "Dockerfile.prod" in source
    assert "env_file:" in source
    assert ".env.production" in source
    assert "AUTH_DEV_MODE" not in source
    assert "volumes:" in source
    assert ".:/app" not in source


def test_env_production_example_disables_debug_and_dev_mode():
    source = read(".env.production.example")
    assert 'DJANGO_DEBUG=false' in source
    assert 'AUTH_DEV_MODE=false' in source
    assert "192.168.3.196" in source


def test_requirements_prod_includes_runtime_dependencies_only():
    lines = {
        line.strip()
        for line in read("requirements-prod.txt").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    assert "gunicorn" in lines
    assert "whitenoise" in lines
    assert "pytest" not in lines


def test_settings_enables_whitenoise_when_debug_false():
    source = read("config/settings.py")
    assert "if not DEBUG:" in source
    assert "whitenoise.middleware.WhiteNoiseMiddleware" in source
