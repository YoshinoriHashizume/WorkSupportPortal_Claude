from pathlib import Path

from config.repo_paths import repo_root


REPO_ROOT = repo_root(Path(__file__).resolve())


def test_local_setup_doc_uses_claude_workspace_path():
    """作業ディレクトリ名は WorkSupportPortal_Claude（旧 _Cursor ではない）。"""
    source = (REPO_ROOT / "Document" / "ローカル開発環境構築手順.md").read_text(encoding="utf-8")
    assert "cd D:\\application\\WorkSupportPortal_Claude" in source
    assert "cd D:\\application\\WorkSupportPortal_Cursor" not in source
