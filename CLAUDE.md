# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Cursor 用の `.cursor/rules` は **使用しない**。エージェント向けの常時規約は本ファイルと `src/.claude/skills/` を正とする。

---

## 1. Project Overview

**プロジェクト名**: WorkSupportPortal（業務支援ポータル）

**概要**: 基幹周辺業務を支援する社内 Web ポータル

**技術スタック**:

| 項目 | 技術 |
|------|------|
| 言語 | Python 3.12 |
| フレームワーク | Django 5.x |
| DB | PostgreSQL（アプリ）、Oracle（基幹参照） |
| アーキテクチャ | Clean Architecture + DDD（社内標準） |
| ローカル実行 | Docker Compose / DevContainer（ポート 8990 / 5440） |

**ソース**: `src/`（DevContainer workspace: `/django_app/src`）  
**仕様書**: `Document/`（Single Source of Truth）  
**スキル**: `src/.claude/skills/`（SDD・設計レビュー等）

---

## 2. プロジェクト固有のクリティカルルール

- Clean Architecture。依存方向: **interfaces → use_cases → domain ← infrastructure**
- `use_cases/` と `domain/` に Django / 自 app の `infrastructure` を import しない
- DI は `interfaces/wiring.py` の手動組み立てのみ（`composition.py`・DI コンテナ禁止）
- 変更は **`Document/` に記載**し、**単体テストを追加**する
- 応答は日本語

詳細レイヤー規約は下記 §5 および `Document/ドメイン駆動設計.md` §5.0。

---

## 3. 絶対ルール

### コード変更の制約

1. 読解・分析のみの依頼ではファイルを変更しない
2. 実装前に変更方針を示し、ユーザーの意図とずれないこと
3. 既存コードの削除を伴う変更は、削除対象を明示してから実行する
4. 秘密情報（`.env` 実体のパスワード等）を Git に含めない・文書に実パスワードを書かない

### 仕様の原則

1. **`Document/` が Single Source of Truth**
2. コードと仕様が食い違う場合は仕様を正し、必要なら仕様を先に直す
3. ユビキタス言語・機能仕様は `Document/application/` および各 app の docs（ある場合）を参照

### 禁止事項

1. タスク・仕様の確認なしに大規模リファクタを始めない
2. 判断に迷う場合はユーザーに確認する

---

## 4. SDD / スキル

ユーザーが SDD・設計レビュー等を求めた場合は `src/.claude/skills/` を使う。

| 用途 | スキル |
|------|--------|
| スペック駆動開発 | `sdd` |
| CLAUDE.md 生成・更新 | `generate-claude-md` |
| 設計レビュー | `design_review` |
| 要件レビュー | `requirements-review` |
| テスト設計 | `make-test-design` |

ガイドライン: `src/.claude/guidelines/sdd_workflow_guideline.md`

本リポジトリの仕様パスは社内テンプレの `docs/` ではなく **`Document/`** を優先する。

---

## 5. クリーンアーキテクチャ（社内標準）

新規 Django app 追加・リファクタ時は必ず従う。検証: `src/config/tests/test_clean_architecture.py`

### フォルダ構成（必須）

```text
application/<app>/
  domain/
    entities/
    value_objects/
    repositories/      # ports.py（Protocol）
  use_cases/
  infrastructure/      # oracle/, persistence/, desknet/, django/models 等
  interfaces/
    views.py
    urls.py
    wiring.py
  models.py            # ORM 定義の正（infrastructure からリエクスポート）
```

### 命名

| 種別 | 規則 | 例 |
|------|------|-----|
| ユースケースファイル | `<機能>.py` | `list_page.py` |
| ユースケースクラス | 機能名 | `ListPage` |
| wiring ファクトリ | `<snake>_usecase()` | `list_page_usecase()` |
| ポート | `domain/repositories/ports.py` | `LoadSummary` |

### 依存の向き

- `interfaces/views.py` → wiring / use_cases / domain（infrastructure をビジネスで直呼びしない）
- `interfaces/wiring.py` → use_cases + infrastructure（ここでのみ組み立て）
- `use_cases/` → domain のみ
- `infrastructure/` → domain
- `domain/` → 他レイヤー非依存

**禁止**: `composition.py`、`services/` 層の新設、`use_cases` からの Django import

### 新規 app チェックリスト

1. domain / use_cases / infrastructure / interfaces を用意
2. ports 定義 → wiring で注入 → views は HTTP のみ
3. `models.py` を正とし infrastructure からリエクスポート
4. `config/tests/test_clean_architecture.py` の `BUSINESS_APPS` に追加
5. `Document/` 更新と単体テスト追加

---

## 6. ローカル開発（要点）

```powershell
cd D:\application\WorkSupportPortal_Claude
docker compose -f docker-compose.devcontainer.yaml up --build -d
```

- アプリ: http://localhost:8990
- 開発ログイン: 社員番号 `10001` / パスワード `dev`（`AUTH_DEV_MODE=true`）
- Oracle: `ORACLE_PASSWORD`・`ORACLE_THICK_MODE=true`（詳細は `Document/ローカル開発環境構築手順.md`）
- DevContainer: ホスト `.ssh` はマウントしない（個人パス固定を禁止）
- 本番依存: **`requirements-prod.txt`** がランタイムの正（Docker は `requirements-docker.txt`）

---

## 7. 改訂

| 日付 | 内容 |
|------|------|
| 2026-07-20 | `.cursor/rules` から移行。Claude Code 向け `CLAUDE.md` を正とする |
