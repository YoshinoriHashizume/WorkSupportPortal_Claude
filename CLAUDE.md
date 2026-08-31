# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

このファイルには **reference を読まなくても常に守るべきクリティカルなルール** のみを置く。
詳細な手順・レビュー観点・命名規則はスキルの reference に配置し、各フェーズで参照・検証する。

---

## 1. Project Overview

**プロジェクト名**: WorkSupportPortal

**概要**: 基幹周辺業務を支援する社内 Web ポータル。Docker/DevContainer環境で開発する。

**技術スタック**:

| 項目 | 技術 |
|------|------|
| 言語 | Python 3.12 |
| フレームワーク | Django 5.2 (フロントエンド: Django テンプレート + 素の JS/CSS。UIフレームワーク不使用、帳票は openpyxl / CSV) |
| DB | PostgreSQL 16 (ポータル、読み書き) / Oracle (基幹、**読み取り専用**・`oracledb`) |
| アーキテクチャ | Clean Architecture (`src/application/<app>/` 配下のアプリ単位でレイヤー分割) |

**関連システム**: desknet's NEO (AppSuite API / Login API・当面の認証基盤) / SLIMS (在庫CSV) / 基幹 Oracle (MARI)

**所在**: ソース `src/` (DevContainer workspace: `/django_app/src`) / スキル `src/.claude/skills/`

---

## 2. アーキテクチャの要点

- Clean Architecture採用。依存方向: interfaces → use_cases → domain ← infrastructure
- 各アプリの domain/ と use_cases/ に `import django` を書かない (Django非依存)
- Entity と ORM Model は別物。変換はリポジトリが担う
- DIコンテナ不使用。組み立ては `interfaces/wiring.py` **のみ**で行う。
  views は use_cases / infrastructure / models を直 import しない (必ず wiring 経由)
- `composition.py` および `services/` 層の新設は**禁止**
- Phase 5 では TDD を採用する

検証: `src/config/tests/test_clean_architecture.py`

---

## 3. 絶対ルール

以下のルールはプロジェクトの種類・規模に関わらず厳守すること。

### コード変更の制約

1. **読解・分析を依頼された場合、ファイルの変更は一切行わない**
2. **実装に着手する前に、必ず以下を提示し、ユーザーの承認を得る:**
   - 変更対象ファイルの一覧
   - 各ファイルの変更概要(何を追加/修正/削除するか)
   - 変更の影響範囲
3. **1回の変更は1ファイルを基本とする。** 複数ファイルの同時変更が必要な場合は事前に一覧を提示する
4. **既存コードの削除を伴う変更は、削除対象を明示してから実行する**

### 仕様の原則

1. **仕様書が Single Source of Truth(唯一の信頼できる情報源)である**
2. コードと仕様が食い違った場合、仕様が正しい。コードを修正すること
3. 実装中に仕様変更が必要になった場合、コードではなく仕様書を先に修正すること
4. すべての成果物で対象アプリケーションの `src/application/{app_name}/docs/ubiquitous_language.md` に定義されたユビキタス言語を使用すること

### 禁止事項

1. **タスクを作成しファイルへ書き出すことなく実装を開始することは禁止する**
2. 実装に移るときは、必ず確認を取ること
3. 判断に迷う場合は、必ずユーザーに確認すること

### 問題発生時

- ビルドエラーやテスト失敗が発生した場合、エラーメッセージを正確に報告し、修正案を提示してから修正する
- 意図しない変更が発生した場合、差分を確認し、ユーザーに報告する

---

## 4. SDD(スペック駆動開発)ルール

### 基本原則

- 仕様書が Single Source of Truth
- 要件定義書は**問題空間(WHAT)**、設計書は**解決空間(HOW)** を定義する
- 設計書は**機能設計**(design.md)と**テスト設計**(test-design.md)に分離する
- すべての成果物で対象アプリの `src/application/{app_name}/docs/ubiquitous_language.md` のユビキタス言語を使用する
- どんな小さなツールでも、戦略的設計(`src/docs/strategic_design.md`)の地図上で位置を確認してから着手する

- ユーザーのコメントに不明な点は積極的に質問をおこない、質問する時は常にAskUserQuestionを使って回答させる
- **選択肢にはそれぞれ、推奨度と理由を提示**し、推奨度は⭐の5段階評価にて表現する

### SDDフロー

SDD/スペック駆動開発での開発を求められた場合は、以下のフェーズに従う。
**各フェーズの承認が得られるまで次のフェーズに進んではならない。**
詳細な手順・成果物の保存先・文書ヘッダー・レビュー体系は **`sdd` スキル**(`sdd/SKILL.md`)を参照する。

| フェーズ | 成果物 | 承認 | 対応スキル |
|---------|--------|------|-----------|
| 0: 壁打ち | 整理メモ(5W1H + 制約) | 不要 | `sdd` |
| 1: ユビキタス言語整理 | `{app}/docs/ubiquitous_language.md` | **必要** | `make-ubiquitous-language` |
| 2: 要件定義書 | `{app}/docs/spec/{feature}/requirements.md` | **必要** | `make-requirements` |
| 2.5: Design Level Event Storming | イベントフロー図(オプション) | **必要**(実施時) | `sdd` |
| 3: 設計書 | `{app}/docs/spec/{feature}/design.md` + `test-design.md` | **必要** | `make-design` / `make-test-design` |
| 4: タスク分解 | `{app}/docs/spec/{feature}/tasks.md` | **必要** | `make-tasks` |
| 5: 実装 | コード + テスト | タスクごとに確認・報告 | (直接実装 / TDD) |

- 上表の `{app}` は `src/application/{app_name}` を指す
- `{feature-name}` はケバブケースで命名する。仕様書はGit管理対象とし、コードと一緒にコミットする
- 各文書の先頭には文書ID・作成日・更新日・対応文書を明記する(書式は `sdd` スキル参照)
- 全体の手順書(ローカル開発環境構築・本番デプロイ・Entra ID構築等)は `Document/` に置く

### レビュー体系

5つの独立したレビュー体系(戦略的設計 / 要件定義 / 設計 / テスト設計 / 実装)を、
それぞれ異なるタイミングで実施する。各レビューの詳細観点・Codexクロスレビュー(L2/L4)・
レビュー履歴の記録ルールは **`sdd/references/review-system.md`** に定義する。

### SDDを省略してよい場合

- 単純なバグ修正(1ファイル以内の修正)
- 既存機能の軽微な調整(UI文言変更等)
- ユーザーが明示的にバイブコーディングを指定した場合

省略する場合でも、命名は対象アプリの `src/application/{app_name}/docs/ubiquitous_language.md` に準拠する。
迷う場合はユーザーに「SDDフローで進めますか？」と確認すること。

### 運用フェーズのIssue管理

リリース後に発見された不具合・改善案は、Issueとして起票してPDCAで管理する。
**`manage-issue` スキルを使用する。** 対策が軽微(1ファイル以内)なら Issue 内で完結、
本格的(再設計・複数レイヤー)なら `{app}/docs/spec/{feature}/` を新設して通常のSDDフローに委譲する
(分岐基準は「SDDを省略してよい場合」を踏襲。双方向リンクでトレースする)。

### ユビキタス言語の2層構造

core(`src/docs/ubiquitous_language_core.md`、プロジェクト横断)と
コンテキスト固有(`src/application/{app_name}/docs/ubiquitous_language.md`)の2層。
core を更新した場合は他のプロジェクトにも反映すること。

---

## 5. カスタムスキル

配置先: `src/.claude/skills/<skill_name>/SKILL.md` (DevContainer 内: `/django_app/src/.claude/skills/<skill_name>/SKILL.md`)

### スキル整備方針

- スキルは実際の作業で繰り返しパターンが見つかったタイミングで作成する。先回りして大量に作らない
- 同じ指示を3回以上繰り返したらスキル化を検討する
- 作成したスキルは実際に使って効果を確認してから定着させる
- 使わなくなったスキルは削除する
- **スキルはできるだけプロジェクトに依存しない形で作成する**。プロジェクト固有の知識はreferenceに分離する

---


*このCLAUDE.mdはプロジェクトの実践を通じて継続的に改善していくものです。*
