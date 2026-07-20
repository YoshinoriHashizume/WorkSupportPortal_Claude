from __future__ import annotations

from pathlib import Path

from config.repo_paths import repo_root


REPO_ROOT = repo_root(Path(__file__).resolve())


def read_program_doc() -> str:
    return (REPO_ROOT / "Document" / "プログラム作成実行書.md").read_text(encoding="utf-8")


def test_program_doc_describes_develop_feature_workflow():
    doc = read_program_doc()
    assert "### 3.3 Git ブランチ運用" in doc
    assert "develop" in doc
    assert "feature/" in doc
    assert "master" in doc


def test_program_doc_says_delete_merged_feature_branches():
    doc = read_program_doc()
    assert "マージ済み" in doc
    assert "git branch -d" in doc
