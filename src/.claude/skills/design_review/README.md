# Design Review Skills — README

設計レビュー用のClaude Codeカスタムスキル群。
機能設計（L1）、テスト設計（L2）、実装（L3）の3段階でレビューを実施する。

---

## スキル一覧

| スキル | 対象 | トリガー例 |
|--------|------|----------|
| **design-review-l1** | 機能設計書（design.md） | 「設計レビューL1をお願い」「機能設計のレビューをして」 |
| **design-review-l2** | テスト設計書（test-design.md） | 「設計レビューL2をお願い」「テスト設計のレビューをして」 |
| **design-review-l3** | 実装コード | 「設計レビューL3をお願い」「実装レビューをして」 |

推奨フロー: **L1 → L2 → 実装 → L3**

---

## design-review-l1（機能設計レビュー）

### 概要

機能設計書（design.md）のドメイン設計を検証する。言語・フレームワークに依存しない。

### レビュー観点（4観点）

| 観点 | 内容 |
|------|------|
| 1. 戦略的設計との整合性 | コンテキスト境界、コンテキストマッピングとの整合 |
| 2. ドメインモデルの妥当性 | エンティティ/VO/集約の設計、貧血モデルの検出 |
| 3. ビジネスルールの配置 | 各レイヤーへの適切な配置（referenceのアーキテクチャ定義を参照） |
| 4. ユビキタス言語との整合性 | 用語の一致、使用禁止表現の検出 |

### references（3ファイル）

| ファイル | バージョン | 内容 | コピー元 |
|---------|----------|------|---------|
| swift-clean-architecture.md | v1.0 | Swift + Clean Architectureのレイヤー定義 | make-design [MASTER] |
| django-clean-architecture.md | v1.0 | Django + Clean Architectureのレイヤー定義 | make-design [MASTER] |
| csharp-clean-architecture.md | v1.0 | C# + Clean Architectureのレイヤー定義 | make-design [MASTER] |

CLAUDE.mdの技術スタックに応じて該当するreferenceが自動選択される。

---

## design-review-l2（テスト設計レビュー）

### 概要

テスト設計書（test-design.md）のテスト戦略・テストケースを検証する。

### レビュー観点（4観点）

| 観点 | 内容 |
|------|------|
| 1. テスト戦略の妥当性 | テストピラミッド準拠、Domain層テストの優先度 |
| 2. テストケースの網羅性 | 要件定義書・機能設計書の全要件に対するカバレッジ |
| 3. 境界値・異常系のカバレッジ | 最小値/最大値、null、不正な型、タイムアウト等 |
| 4. テストケースの品質 | テスト名の明確さ、入出力の具体性、意味のあるアサーション |

### references（1ファイル）

| ファイル | バージョン | 内容 | コピー元 |
|---------|----------|------|---------|
| test-strategy.md | v1.0 | テスト戦略ガイドライン（言語非依存） | make-test-design [MASTER] |

---

## design-review-l3（実装レビュー）

### 概要

実装コードが設計書通りに作られているか、Clean Architectureに準拠しているかを検証する。言語固有のコーディング規約チェックもreferenceで対応する。

### レビュー観点（5観点）

| 観点 | 内容 |
|------|------|
| 1. 設計書との整合性 | クラス・プロパティ・処理フローが設計書と一致しているか |
| 2. Clean Architectureのレイヤー違反 | 依存方向、Domain層の独立性、Infrastructure層の責務 |
| 3. ドメインモデルの実装 | エンティティの貧血モデル検出、VOの不変性、集約ルート経由アクセス |
| 4. 設計パターンの一貫性 | API連携/DB永続化のパターン統一、命名パターン統一 |
| 5. 命名の準拠 | ユビキタス言語集との一致、使用禁止表現の検出 |

### references（6ファイル）

**アーキテクチャ定義（コピー）**:

| ファイル | バージョン | コピー元 |
|---------|----------|---------|
| swift-clean-architecture.md | v1.0 | make-design [MASTER] |
| django-clean-architecture.md | v1.0 | make-design [MASTER] |
| csharp-clean-architecture.md | v1.0 | make-design [MASTER] |

**コーディング規約（プレースホルダー）**:

| ファイル | バージョン | 状態 |
|---------|----------|------|
| swift-coding-rules.md | v1.0 | プレースホルダー。プロジェクトの実践を通じて追記する |
| django-coding-rules.md | v1.0 | 同上 |
| csharp-coding-rules.md | v1.0 | 同上 |

---

## referenceのバージョン管理

### ヘッダー形式

```yaml
---
version: 1.0
updated: 2026-04-11
source-name: swift-clean-architecture
---
```

### バージョンチェックの仕組み

各スキルは実行時に、同名referenceを持つ他のスキルとバージョンの整合性を自動チェックする。

```
✅ 一致の場合:
  「アーキテクチャreference整合性チェック: ✅ 一致（version 1.0, updated 2026-04-11）」

⚠️ 不一致の場合:
  「⚠️ referenceのバージョンが不一致です。referenceを同期してください。」
```

### チェック対象

| referenceファイル | チェック対象スキル |
|-----------------|-----------------|
| swift-clean-architecture.md | make-design ↔ design-review-l1 ↔ design-review-l3 |
| django-clean-architecture.md | 同上 |
| csharp-clean-architecture.md | 同上 |
| test-strategy.md | make-test-design ↔ design-review-l2 |

### 更新手順

1. make-design（またはmake-test-design）のreferenceを編集する（MASTER）
2. version と updated を更新する
3. コピーを持つ全スキルに上書きコピーする

```bash
# 例: swift-clean-architecture.md を更新した場合
cp make-design/references/swift-clean-architecture.md design-review-l1/references/
cp make-design/references/swift-clean-architecture.md design-review-l3/references/

# 例: test-strategy.md を更新した場合
cp make-test-design/references/test-strategy.md design-review-l2/references/
```

---

## 配置方法

```bash
cp -r design-review-l1/ .claude/skills/design-review-l1/
cp -r design-review-l2/ .claude/skills/design-review-l2/
cp -r design-review-l3/ .claude/skills/design-review-l3/
```

---

## ディレクトリ構成

```
design-review-l1/
├── SKILL.md
└── references/
    ├── swift-clean-architecture.md      [COPY]
    ├── django-clean-architecture.md     [COPY]
    └── csharp-clean-architecture.md     [COPY]

design-review-l2/
├── SKILL.md
└── references/
    └── test-strategy.md                 [COPY]

design-review-l3/
├── SKILL.md
└── references/
    ├── swift-clean-architecture.md      [COPY]
    ├── django-clean-architecture.md     [COPY]
    ├── csharp-clean-architecture.md     [COPY]
    ├── swift-coding-rules.md            [プレースホルダー]
    ├── django-coding-rules.md           [プレースホルダー]
    └── csharp-coding-rules.md           [プレースホルダー]
```

---

*最終更新: 2026/04/17*
