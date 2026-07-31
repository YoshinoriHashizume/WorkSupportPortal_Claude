"""文書配置（社内標準の SDD 構成）の検証。

アプリ固有文書は `src/application/<app>/docs/`、横断設計文書は `src/docs/`、
全体の手順書は `Document/`（リポジトリルート）に置く。
配置の根拠は `Document/社内標準移行メモ.md` §8 および
`Document/アプリケーション仕様書.md` §5.4・§12。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from config.repo_paths import repo_root


SRC_ROOT = Path(__file__).resolve().parents[2]  # = src/
REPO_ROOT = repo_root(Path(__file__).resolve())

# アプリ名 -> そのアプリの docs/ に必ず存在する文書
APP_DOCS = {
    "gonenkukumi": (
        "5年9組_機能仕様書.md",
        "5年9組_テスト仕様書.md",
        "MARI_Oracle_テーブル定義.md",
    ),
    "receipt_comparison": (
        "検収書比較_機能仕様書.md",
        "検収書比較_テスト仕様書.md",
    ),
    "inventory_order_alert": (
        "在庫発注アラート_機能仕様書.md",
        "在庫発注アラート_テスト仕様書.md",
    ),
    "asset_inventory": (
        "資産棚卸結果_機能仕様書.md",
        "資産棚卸結果_テスト仕様書.md",
    ),
    "shipment_trend": (
        "出荷トレンド一覧_機能仕様書.md",
        "出荷トレンド一覧_テスト仕様書.md",
    ),
    "portal": ("ポータル一覧表_共通仕様.md",),
}

CROSS_CUTTING_DOCS = (
    "ubiquitous_language_core.md",
    "テスト配置_共通仕様.md",
)

ROOT_DOCS = (
    "アプリケーション仕様書.md",
    "ドメイン駆動設計.md",
    "ローカル開発環境構築手順.md",
    "本番環境デプロイ手順.md",
    "プログラム作成実行書.md",
    "社内標準移行メモ.md",
)


@pytest.mark.parametrize("app_name,doc_names", sorted(APP_DOCS.items()))
def test_app_specific_docs_live_under_app_docs_dir(app_name: str, doc_names: tuple[str, ...]):
    docs_dir = SRC_ROOT / "application" / app_name / "docs"
    assert docs_dir.is_dir(), f"{app_name} missing docs/"
    for name in doc_names:
        assert (docs_dir / name).is_file(), f"{app_name}/docs/{name} not found"


@pytest.mark.parametrize("doc_name", CROSS_CUTTING_DOCS)
def test_cross_cutting_docs_live_under_src_docs(doc_name: str):
    assert (SRC_ROOT / "docs" / doc_name).is_file(), f"src/docs/{doc_name} not found"


@pytest.mark.parametrize("doc_name", ROOT_DOCS)
def test_project_wide_procedure_docs_stay_in_document_dir(doc_name: str):
    assert (REPO_ROOT / "Document" / doc_name).is_file(), f"Document/{doc_name} not found"


def test_legacy_document_application_dir_is_removed():
    """アプリ固有文書は Document/application/ に残さない（社内標準移行メモ §8）。"""
    assert not (REPO_ROOT / "Document" / "application").exists()


def test_legacy_document_ubiquitous_language_is_renamed():
    """ユビキタス言語 core は src/docs/ubiquitous_language_core.md が正。"""
    assert not (REPO_ROOT / "Document" / "ubiquitous_language.md").exists()
