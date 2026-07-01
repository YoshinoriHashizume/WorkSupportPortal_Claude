from __future__ import annotations

from pathlib import Path


DOC_PATH = Path(__file__).resolve().parents[2] / "Document" / "本番環境デプロイ手順.md"


def read_deploy_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8-sig")


def test_production_deploy_doc_exists():
    assert DOC_PATH.is_file()


def test_production_deploy_doc_describes_desknet_auth_for_current_release():
    doc = read_deploy_doc()
    assert "desknet" in doc.lower() or "desknet's NEO" in doc
    assert "AUTH_PROVIDER" in doc
    assert "DESKNETS_LOGIN_URL" in doc
    assert "Microsoft Entra ID（将来" in doc or "将来切替" in doc


def test_production_deploy_doc_requires_auth_dev_mode_off_in_production():
    doc = read_deploy_doc()
    assert "AUTH_DEV_MODE" in doc
    assert "false" in doc
    assert "bootstrap_local_dev" in doc


def test_production_deploy_doc_uses_django_debug_not_bare_debug():
    doc = read_deploy_doc()
    assert "DJANGO_DEBUG" in doc
    assert "`DEBUG` 単体は未使用" in doc or "DEBUG` 単体" in doc


def test_production_deploy_doc_lists_oracle_environment_variables():
    doc = read_deploy_doc()
    for name in (
        "ORACLE_USE_MOCK",
        "ORACLE_THICK_MODE",
        "ORACLE_CONNECT_TIMEOUT_SECONDS",
    ):
        assert name in doc
    assert "GONENKUKUMI_COMPANY_CD" not in doc


def test_production_deploy_doc_microsoft_callback_path_matches_implementation():
    doc = read_deploy_doc()
    assert "/api/auth/callback/microsoft-entra-id" in doc

    urls_source = (
        Path(__file__).resolve().parents[2] / "applications" / "identity" / "urls.py"
    ).read_text(encoding="utf-8")
    assert "api/auth/callback/microsoft-entra-id" in urls_source


def test_production_deploy_doc_checklist_covers_desknet_and_static_files():
    doc = read_deploy_doc()
    assert "desknet" in doc.lower() or "desknet's NEO" in doc
    assert "/static/" in doc or "静的ファイル" in doc
    assert "開発者専用ログインが表示されない" in doc


def test_production_deploy_doc_mentions_windows_server_vm_and_linux_containers():
    doc = read_deploy_doc()
    assert "Windows Server" in doc
    assert "Linux コンテナ" in doc or "Docker Engine" in doc


def test_production_deploy_doc_does_not_reference_missing_nginx_local_conf():
    doc = read_deploy_doc()
    assert "docker/nginx/local.conf" not in doc


def test_production_deploy_doc_references_prod_compose_files():
    doc = read_deploy_doc()
    root = Path(__file__).resolve().parents[2]
    assert "docker-compose.prod.yml" in doc
    assert "Dockerfile.prod" in doc
    assert (root / "docker-compose.prod.yml").is_file()
    assert (root / "Dockerfile.prod").is_file()


def test_production_deploy_doc_recommends_wsl_ubuntu_docker_engine():
    doc = read_deploy_doc()
    assert "WSL2 Ubuntu" in doc or "WSL2 の Ubuntu" in doc
    assert "Docker Engine" in doc
    assert "/mnt/c/Application/WorkSupportPortal" in doc
    assert "scripts/wsl/install-docker-engine.sh" in doc


def test_production_deploy_doc_describes_vm_limitations_and_windows_direct_run():
    doc = read_deploy_doc()
    assert "§2.1" in doc
    assert "ネストした仮想化" in doc
    assert "10.3 初心者向け" in doc
    assert "ここから読み始めてください" in doc
    assert "ステップ 1" in doc and "ステップ 11" in doc
    assert "requirements-windows-prod.txt" in doc
    assert "Start-ProductionApp.ps1" in doc
    assert "192.168.3.196:3000" in doc
    assert "よくあるつまずき" in doc
    assert "10.4 Linux" in doc


def test_production_deploy_doc_points_beginners_to_section_10_3():
    doc = read_deploy_doc()
    assert "10.1 どの手順を読むか" in doc
    assert "§10.3 を読んでください" in doc or "§10.3" in doc


def test_production_deploy_doc_marks_docker_desktop_as_not_recommended():
    doc = read_deploy_doc()
    assert "10.2 Docker Desktop" in doc
    assert "非推奨" in doc


def test_production_deploy_doc_has_beginner_guide_and_bootstrap_admin():
    doc = read_deploy_doc()
    assert "10.3 初心者向け" in doc
    assert "bootstrap_production_admin" in doc
    assert "check_production_env" in doc
    assert "Start-ProductionApp.cmd" in doc
    assert "bootstrap_production_admin --username 51705" in doc
    assert "DPY-3015" in doc
    assert "instantclient_23_0" in doc


def test_production_deploy_doc_documents_git_clone_on_windows():
    doc = read_deploy_doc()
    assert "```cmd" in doc
    assert "cd /d C:\\Application\\WorkSupportPortal" in doc or "C:\\Application\\WorkSupportPortal" in doc
    assert "git clone" in doc
    assert "WorkSupportPortal" in doc
    assert "§3.1" in doc


def test_production_deploy_doc_describes_github_rename_from_core_data_integration_portal():
    doc = read_deploy_doc()
    assert "CoreDataIntegrationPortal" in doc
    assert "git remote set-url" in doc
