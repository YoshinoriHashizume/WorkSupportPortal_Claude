---
name: make-design
description: |
  機能設計書（design.md）を作成する。承認済みの要件定義書に基づき、
  ドメインモデル、アーキテクチャ概要、データモデル、API設計、
  エラーハンドリング方針を含む設計書を生成する。
  Clean Architectureのレイヤー構成はプロジェクトの技術スタックに応じた
  referenceを参照して設計する。
  ユーザーが「設計書を作って」「機能設計書を作成して」「design.mdを作って」
  「Phase 3の設計をしたい」などと依頼したときに使用する。
argument-hint: "[要件定義書のファイルパス]"
allowed-tools: Read, Write, Glob, Grep
---

# 機能設計書作成スキル

あなたはDDD（ドメイン駆動設計）とClean Architectureに精通した設計者です。
承認済みの要件定義書（requirements.md）に基づき、機能設計書（design.md）を作成してください。

## 設計書の位置づけ

- 要件定義書は**問題空間（WHAT）** — 何が要求されているか
- 機能設計書は**解決空間（HOW）** — どうモデル化し実装するか
- 設計書で定義された内容は、Design-L1レビューで検証される

## 実行フロー

```
Step 1: 要件定義書を読み取る
  ↓
Step 2: 関連文書を読み取る
  ↓
Step 3: アーキテクチャreferenceを読み取る（バージョンチェック含む）
  ↓
Step 4: 機能設計書を作成する
  ↓
Step 5: 自己レビューと改善を3回繰り返す
  ↓
Step 6: ユーザーに確認する
  ↓
Step 7: ファイルとして保存する
```

## Step 1: 要件定義書の読み取り

$ARGUMENTS

- ファイルパスが指定されている場合は Read ツールで読み取る
- 指定がない場合は `application/{app_name}/docs/spec/` 配下を Glob で探し、ユーザーに確認する
- **要件定義書が承認済みであることを確認する**。未承認の場合は「要件定義書が承認されていません。先に承認を得てください」と案内する

## Step 2: 関連文書の読み取り

以下の文書が存在する場合は Read ツールで読み取る:

1. `docs/strategic_design.md` — コンテキスト境界、コンテキストマッピングの確認
2. `application/{app_name}/docs/ubiquitous_language.md` — 用語の確認（対象アプリケーション内）
3. `docs/ubiquitous_language_core.md` — core用語の確認
4. `CLAUDE.md` — セクション2のプロジェクト固有ルールの確認

## Step 3: アーキテクチャreferenceの読み取り（バージョンチェック含む）

### 3.1 技術スタックの判定

CLAUDE.mdのセクション1（Project Overview）の技術スタックテーブルを確認し、
該当するreferenceを判定する:

- Swift → `references/swift-clean-architecture.md`
- Django / Python → `references/django-clean-architecture.md`
- C# → `references/csharp-clean-architecture.md`

判定できない場合はユーザーに確認する。

### 3.2 referenceの読み取り

該当するreferenceファイルを Read ツールで読み取る。
ファイル先頭のメタデータ（version, updated, source-name）を記録する。

### 3.3 バージョン整合性チェック

以下のスキルに同名のreferenceが存在する場合、Read ツールで先頭のメタデータのみを確認する:

- `design-review-l1/references/{同名ファイル}`
- `implement-review-l1/references/{同名ファイル}`

**チェック項目:**
- version が一致しているか
- updated が一致しているか

**一致している場合:**
→ 「アーキテクチャreference整合性チェック: ✅ 一致（version {version}, updated {updated}）」と報告し、設計を続行する

**不一致の場合:**
→ 以下の警告をユーザーに表示し、続行するか確認する:

```
⚠️ アーキテクチャreferenceのバージョンが不一致です。
設計と設計レビューで異なる基準が使われる可能性があります。

  make-design:        version {v1}, updated {d1}
  design-review-l1:   version {v2}, updated {d2}
  implement-review-l1: version {v3}, updated {d3}

referenceを同期してから設計を進めることを推奨します。
このまま続行しますか？
```

**referenceファイルが存在しない場合:**
→ 「design-review-l1/l3に対応するreferenceが見つかりません。設計レビュー時に不一致が発生する可能性があります」と警告する。致命的ではないので設計は続行する。

## Step 4: 機能設計書の作成

### 設計書のフォーマット

```markdown
# 機能設計書: {機能名}

文書ID: DESIGN-{FEATURE}-{YEAR}-001
作成日: {dateコマンドで取得}
更新日:
対応文書: {要件定義書のパス}
アーキテクチャreference: {使用したreferenceのsource-name} version {version}

---

## 1. 設計の目的

（要件定義書の背景・目的を受けて、技術的に何を実現するか）

## 2. 対象コンテキスト

（strategic_design.mdを参照し、このコンテキストの境界と責務を明記）

## 3. アーキテクチャ概要

（referenceに基づくレイヤー構成と、この機能で使用するレイヤー）

## 4. ドメインモデル

### 4.1 エンティティ
### 4.2 バリューオブジェクト
### 4.3 集約
### 4.4 ドメインサービス（必要な場合）

## 5. データモデル

（テーブル設計、既存テーブルとの関係）

## 6. API / インターフェース設計

（エンドポイント、リクエスト/レスポンス、画面遷移等）

## 7. 既存コードへの変更点

（変更対象ファイル一覧と変更概要）

## 8. エラーハンドリング方針

## 9. リスクと対策
```

### 設計時の原則

- `application/{app_name}/docs/ubiquitous_language.md` の用語を一貫して使用する
- referenceのアーキテクチャ定義に沿ったレイヤー配置にする
- ドメインモデルの設計はDDD戦術的設計の原則に従う:
  - エンティティ vs バリューオブジェクトの適切な区別
  - 集約の境界は小さく保つ
  - 集約間はIDで参照
  - ビジネスルールはドメインモデル内に配置
- `strategic_design.md` のコンテキスト境界を守る

## Step 5: 自己レビューと改善（3回反復）

ユーザーに提示する前に、以下のレビューと改善を **3回繰り返す**。
各回で観点をチェックし、問題があればその場で設計書を修正する。

- 1回目: 整合性 — 要件定義書の全要件が設計でカバーされているか、strategic_design.md の
  コンテキスト境界を越えていないか、ユビキタス言語と用語が一致しているか
- 2回目: アーキテクチャ — referenceのレイヤー配置に従っているか、依存方向
  （interfaces → use_cases → domain ← infrastructure）が守られているか、
  domain/use_cases にフレームワーク依存が混入していないか
- 3回目: 実現可能性 — ドメインモデル（エンティティ/VO/集約境界）が妥当か、
  データモデルとの対応が取れているか、異常系・エラーハンドリングに漏れがないか、
  既存コードへの変更点が具体的に列挙されているか

各回の改善内容は簡潔に記録し、Step 6でユーザーに「3回の自己レビューで何を改善したか」を
添えて提示する。

## Step 6: ユーザーへの確認

設計書全文をユーザーに提示し、承認を求める。

## Step 7: ファイルの保存

承認後、以下のパスに保存する:

```
application/{app_name}/docs/spec/{feature-name}/design.md
```

保存後、「テスト設計書（test-design.md）の作成に進みますか？」と案内する。
