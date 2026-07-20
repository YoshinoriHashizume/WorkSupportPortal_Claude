# SDD × DDD Skills — README

Claude Code用のカスタムスキル群。SDD（スペック駆動開発）とDDD（ドメイン駆動設計）を統合した開発フローを支援する。

作成日: 2026/04/24

---

## 1. 概要

### 背景

 SDD（スペック駆動開発）にDDD（ドメイン駆動設計）の戦略的設計・戦術的設計を統合した開発フレームワークをClaude Code上に構築した。

### 基本思想

- **仕様書が Single Source of Truth**
- 要件定義書 = **問題空間（WHAT）**、設計書 = **解決空間（HOW）**
- 設計書は**機能設計（design.md）**と**テスト設計（test-design.md）**に分離
- **どんな小さなツールでも、戦略的設計の地図上で位置を確認してから着手する**
- スキルはできるだけ**プロジェクトに依存しない**形で作成する

### 参考資料


---

## 2. 配置方法

すべてのスキルフォルダを `.claude/skills/` 配下にコピーする。

```bash
cp -r sdd/ .claude/skills/sdd/
cp -r skill-tester/ .claude/skills/skill-tester/
cp -r generate-claude-md/ .claude/skills/generate-claude-md/
cp -r make-design/ .claude/skills/make-design/
cp -r make-test-design/ .claude/skills/make-test-design/
cp -r design-review-l1/ .claude/skills/design-review-l1/
cp -r design-review-l2/ .claude/skills/design-review-l2/
cp -r design-review-l3/ .claude/skills/design-review-l3/
cp -r requirements-review-l1/ .claude/skills/requirements-review-l1/
cp -r requirements-review-l2/ .claude/skills/requirements-review-l2/
cp -r requirements-review-l3/ .claude/skills/requirements-review-l3/
cp -r strategic-design-review-l1/ .claude/skills/strategic-design-review-l1/
cp -r strategic-design-review-l2/ .claude/skills/strategic-design-review-l2/
cp -r strategic-design-review-l3/ .claude/skills/strategic-design-review-l3/
cp -r make-ubiquitous-language/ .claude/skills/make-ubiquitous-language/
cp -r make-drawio-bmc/ .claude/skills/make-drawio-bmc/
cp -r make-drawio-context-map/ .claude/skills/make-drawio-context-map/
cp -r make-plantuml-sequence/ .claude/skills/make-plantuml-sequence/
```

---

## 3. 全18スキル一覧

### SDDワークフロー

| スキル | トリガー例 | 役割 |
|--------|----------|------|
| **sdd/** | 「SDDで開発して」「壁打ちから始めたい」 | SDDフロー全体（Phase 0〜5）のガイド |

### CLAUDE.md管理

| スキル | トリガー例 | 役割 |
|--------|----------|------|
| **generate-claude-md/** | 「CLAUDE.mdを作成して」 | テンプレートからCLAUDE.mdを生成・更新 |

### スキルテスト

| スキル | トリガー例 | 役割 |
|--------|----------|------|
| **skill-tester/** | 「sddスキルをテストして」 | スキルの4段階テストと結果記録 |

### 設計書・テスト設計書の作成

| スキル | トリガー例 | 役割 |
|--------|----------|------|
| **make-design/** | 「機能設計書を作成して」 | design.md の生成（Phase 3） |
| **make-test-design/** | 「テスト設計書を作成して」 | test-design.md の生成（Phase 3） |

### 設計レビュー

| スキル | トリガー例 | 役割 |
|--------|----------|------|
| **design-review-l1/** | 「設計レビューL1をお願い」 | 機能設計のレビュー（ドメインモデル、ビジネスルール配置） |
| **design-review-l2/** | 「設計レビューL2をお願い」 | テスト設計のレビュー（テスト戦略、テストケース網羅性） |
| **design-review-l3/** | 「設計レビューL3をお願い」 | 実装コードのレビュー（レイヤー違反、設計書との整合性） |

### 要件定義書レビュー

| スキル | トリガー例 | 役割 |
|--------|----------|------|
| **requirements-review-l1/** | 「要件定義書のL1レビューをお願い」 | 形式・用語・構造チェック |
| **requirements-review-l2/** | 「要件定義書のL2レビューをお願い」 | 用語再定義 → ユビキタス言語反映 |
| **requirements-review-l3/** | 「要件定義書のL3レビューをお願い」 | 妥当性・網羅性チェック |

### 戦略的設計レビュー

| スキル | トリガー例 | 役割 |
|--------|----------|------|
| **strategic-design-review-l1/** | 「戦略的設計レビューL1をお願い」 | BMCのレビュー |
| **strategic-design-review-l2/** | 「戦略的設計レビューL2をお願い」 | Big Picture Event Stormingのレビュー |
| **strategic-design-review-l3/** | 「戦略的設計レビューL3をお願い」 | サブドメイン＋コンテキストのレビュー |

### ユビキタス言語・図の作成

| スキル | トリガー例 | 役割 |
|--------|----------|------|
| **make-ubiquitous-language/** | 「ユビキタス言語集を作って」 | core/コンテキスト固有の2層対応の用語集 |
| **make-drawio-bmc/** | 「BMCをdraw.ioで出力して」 | BMC draw.io図の生成 |
| **make-drawio-context-map/** | 「コンテキストマップをdraw.ioで出力して」 | コンテキストマップ draw.io図の生成 |
| **make-plantuml-sequence/** | 「シーケンス図を作って」 | PlantUMLシーケンス図の生成 |

---

## 4. SDDワークフローとスキルの対応

```
戦略的設計（プロジェクト全体で1回）
  BMC                    → make-drawio-bmc, strategic-design-review-l1
  Event Storming         → strategic-design-review-l2
  サブドメイン+コンテキスト → make-drawio-context-map, strategic-design-review-l3
  ユビキタス言語（core）   → make-ubiquitous-language

各コンテキストの開発サイクル
  Phase 0: 壁打ち          → sdd
  Phase 1: ユビキタス言語    → make-ubiquitous-language
    承認①
  Phase 2: 要件定義書       → sdd
    レビュー               → requirements-review-l1/l2/l3
    承認②
  Phase 2.5: Event Storming → sdd（オプション）
  Phase 3: 設計書           → make-design, make-test-design
    レビュー               → design-review-l1, design-review-l2
    承認③
  Phase 4: タスク分解        → sdd
    承認④
  Phase 5: 実装
    レビュー               → design-review-l3
```

---

## 5. 成果物の保存先

```
docs/                                              # プロジェクト全体
├── strategic_design.md                            # 戦略的設計書
└── ubiquitous_language_core.md                    # ユビキタス言語 core（プロジェクト横断）

application/{app_name}/docs/                       # アプリケーション（コンテキスト）ごと
├── ubiquitous_language.md                         # ユビキタス言語（コンテキスト固有）
└── specs/{feature-name}/
    ├── requirements.md                            # 要件定義書（WHAT）
    ├── design.md                                  # 機能設計書（HOW）
    ├── test-design.md                             # テスト設計書
    └── tasks.md                                   # タスクリスト
```

---

## 6. レビュー体系

3つの独立したレビュー体系。すべてL1→L2→L3の一貫したナンバリング。

```
戦略的設計レビュー:  L1(BMC)      → L2(Event Storming) → L3(サブドメイン+コンテキスト)
要件定義書レビュー:  L1(形式)     → L2(用語再定義)     → L3(妥当性・網羅性)
設計レビュー:        L1(機能設計) → L2(テスト設計)     → L3(実装)
```

---

## 7. referenceのバージョン管理

### ヘッダー形式

```yaml
---
version: 1.0
updated: 2026-04-11
source-name: swift-clean-architecture
---
```

### MASTER / COPY の関係

| referenceファイル | MASTER | COPY |
|-----------------|--------|------|
| swift-clean-architecture.md | make-design | design-review-l1, design-review-l3 |
| django-clean-architecture.md | make-design | design-review-l1, design-review-l3 |
| csharp-clean-architecture.md | make-design | design-review-l1, design-review-l3 |
| test-strategy.md | make-test-design | design-review-l2 |

### 更新手順

```bash
# アーキテクチャreferenceを更新した場合
cp make-design/references/{file}.md design-review-l1/references/
cp make-design/references/{file}.md design-review-l3/references/

# テスト戦略referenceを更新した場合
cp make-test-design/references/test-strategy.md design-review-l2/references/
```

---

## 8. CLAUDE.mdテンプレート

### 構成

```
1. Project Overview              ← プロジェクト依存
2. プロジェクト固有の設定          ← プロジェクト依存（最小限、段階的に育てる）
3. 絶対ルール                     ← プロジェクト非依存（常に認識される）
4. SDD（スペック駆動開発）ルール    ← プロジェクト非依存（常に認識される）
5. Task Documentation            ← プロジェクト非依存（常に認識される）
```

### セクション2の方針

- 最小限の要点のみ（3〜5行）。詳細はスキルのreferenceに委ねる
- 普段のコーディング: CLAUDE.mdの要点で80%カバー
- レビュー時: referenceで残り20%を検出

---

## 9. 設計判断の記録

| # | 判断 | 選んだもの | 理由 |
|---|------|----------|------|
| 1 | レビュー分割 | レベルごとに独立スキル | トリガーが確実 |
| 2 | reference共有 | 各スキルにコピー（Anthropic推奨） | フォルダ1つで完結 |
| 3 | TDD | SDDのPhase 5の実現手段 | プロセスの選択であり、アーキテクチャ依存ではない |
| 4 | 設計書分離 | design.md + test-design.md | 関心事・レビュー観点が異なる |
| 5 | CLAUDE.mdセクション2 | 最小限（3〜5行） | 段階的に育てる。詳細はreference |
| 6 | ガイドライン配置 | スキルのreference内 | docs/の成果物と性質が異なる |
| 7 | サブエージェント | 現時点では不要 | 機能設計は文脈の一貫性が重要 |
| 8 | バージョン管理 | ヘッダー + 自動チェック | コピー間の不整合を検出 |
| 9 | プロジェクト固有設定 | 自動生成不可 | 設計者の判断が必要 |
| 10 | スキルの自動トリガー | 不可 | ユーザーのプロンプトで起動 |
| 11 | ドキュメント配置 | アプリ内 docs/ | ソースとドキュメントが同居 |

---

## 10. 関連ドキュメント

| ファイル | 内容 |
|---------|------|
| claude_md_template.md | CLAUDE.mdのテンプレート |
| sdd_ddd_guideline_for_ai.md | AI共有用の詳細ガイドライン |
| sdd_ddd_guideline_for_human.md | 人間用の作業手順書 |
| skill_test_guide_for_human.md | スキルテストの手順書（人間用） |
| sdd_workflow_v3.svg | SDDワークフロー図（スキル配置入り） |
| context_map_source.md | コンテキストマップ作成に用いた情報 |

---

## 11. 今後の課題

- design-review-l3のcoding-rules（swift/django/csharp）はプレースホルダー。実践で追記
- 全18スキルの実プロジェクトでのテスト未実施
- ubiquitous_language_core.md の作成（coreの分離）
- 各プロジェクト間のユビキタス言語同期ルールの運用確認

---

*最終更新: 2026/04/24*
