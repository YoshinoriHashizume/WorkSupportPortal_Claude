from __future__ import annotations

from pathlib import Path

from config.repo_paths import repo_root


SRC_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = repo_root(Path(__file__).resolve())
DOC_PATH = REPO_ROOT / "Document" / "本番環境デプロイ手順.md"


def read_deploy_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8-sig")


def test_production_deploy_doc_exists():
    assert DOC_PATH.is_file()


def test_production_deploy_doc_describes_desknet_auth_for_current_release():
    doc = read_deploy_doc()
    assert "desknet" in doc.lower() or "desknet's NEO" in doc
    assert "AUTH_PROVIDER" in doc
    assert "DESKNETS_LOGIN_URL" in doc


def test_production_deploy_doc_requires_auth_dev_mode_off_in_production():
    doc = read_deploy_doc()
    assert "AUTH_DEV_MODE" in doc
    assert "false" in doc
    assert "bootstrap_local_dev" in doc


def test_production_deploy_doc_lists_oracle_environment_variables():
    doc = read_deploy_doc()
    for name in (
        "ORACLE_USE_MOCK",
        "ORACLE_THICK_MODE",
        "ORACLE_CONNECT_TIMEOUT_SECONDS",
    ):
        assert name in doc


def test_production_deploy_doc_microsoft_callback_path_matches_implementation():
    doc = read_deploy_doc()
    assert "/api/auth/callback/microsoft-entra-id" in doc

    urls_source = (
        SRC_ROOT / "application" / "identity" / "interfaces" / "urls.py"
    ).read_text(encoding="utf-8")
    assert "api/auth/callback/microsoft-entra-id" in urls_source


def test_production_deploy_doc_checklist_covers_desknet_and_static_files():
    doc = read_deploy_doc()
    assert "desknet" in doc.lower() or "desknet's NEO" in doc
    assert "/static/" in doc or "静的ファイル" in doc


def test_production_deploy_doc_mentions_windows_server_vm_and_linux_containers():
    doc = read_deploy_doc()
    assert "Windows Server" in doc
    assert "Linux コンテナ" in doc or "Docker Engine" in doc


def test_production_deploy_doc_references_company_standard_compose_files():
    doc = read_deploy_doc()
    assert "docker-compose.production.yaml" in doc or "docker-compose.prod" in doc
    assert (REPO_ROOT / "docker-compose.production.yaml").is_file()
    assert (REPO_ROOT / "docker" / "django" / "Dockerfile").is_file()
    assert (REPO_ROOT / "entrypoint.sh").is_file()


def test_production_deploy_doc_recommends_wsl_or_devcontainer():
    doc = read_deploy_doc()
    assert "Docker" in doc
    assert "WSL" in doc or "DevContainer" in doc or "devcontainer" in doc


def test_production_deploy_doc_has_bootstrap_admin():
    doc = read_deploy_doc()
    assert "bootstrap_production_admin" in doc
    assert "check_production_env" in doc


def test_production_deploy_doc_uses_current_compose_service_names_and_requirements():
    doc = read_deploy_doc()
    assert "web-app" in doc
    assert "exec django_app" not in doc
    assert "django_postgres" not in doc
    assert "entrypoint-prod.sh" not in doc
    assert "entrypoint.sh" in doc
    assert "requirements-prod.txt" in doc
    assert "requirements-docker.txt" in doc
    assert "--env-file .env.production" in doc
    assert "src/scripts/wsl/" in doc
