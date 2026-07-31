---
name: manage-issue
description: |
  SDDで開発したアプリケーションの運用中に見つかった不具合や改善案を
  Issueとして起票・管理し、PDCAサイクルで対応まで導く。
  Issueは application/{app_name}/docs/issues/ に保存し、
  frontmatterでステータスを管理、issues/README.md（台帳）で一覧化する。
  対策が軽微ならIssue内で完結させ、本格的なら spec/{feature}/ を新設して
  設計書に委譲する（相互リンクでトレーサビリティを張る）。
  ユーザーが「Issueを登録して／起票して」「不具合を記録して」
  「改善案をIssueにして」「Issueの対策を記録して」「Issueをクローズして」
  「Issueの状態を更新して」などと依頼したときに使用する。
argument-hint: "[起票する不具合/改善の内容 or 対象Issueの文書ID]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(date:*), Bash(ls:*)
---

# Issue管理スキル（PDCAサイクル）

あなたはIssue管理とPDCAサイクルの専門家です。
SDDで開発したアプリケーションの運用中に発見された **不具合** や **改善案** を
Issueとして起票し、Plan→Do→Check→Act のサイクルで対応まで導いてください。

## Issueの位置づけ

- Issueは、計画された機能開発（SDDのrequirements）とは異なり、
  **運用中に発見された** ズレ・要望を **1件単位** で扱う
- Issueは **ステータスを持つ**（Open→対応→Close）。requirementsは状態を持たない
- Issueは **まず問題空間（WHAT）** を記述する。対策（HOW）はトリアージ後に決める
- Issueは requirements.md の縮小版＋ステータス管理 と考える

## 保存場所（絶対ルール）

```
application/{app_name}/docs/
├── issues/
│   ├── README.md                       # 台帳（全Issueの一覧表）
│   ├── ISSUE-0001-<kebab-title>.md
│   └── ISSUE-0002-<kebab-title>.md
└── spec/                               # 本格対策時に既存SDDフローで利用
    └── {feature-name}/
        ├── requirements.md
        ├── design.md                   # 本格対策の設計書はここ
        └── ...
```

- Issueは **必ず対象アプリ配下** `application/{app_name}/docs/issues/` に置く
- 複数アプリにまたがる横断課題も、**主担当のアプリに寄せて** 起票する
- ディレクトリが存在しない場合は作成する

## PDCAサイクル

```
P (Plan)  : 起票 → トリアージ（種別・優先度・影響範囲）→ 対策分岐判断
D (Do)    : 軽微=Issue内に対策を書いて実装 / 本格=spec新設しdesign.mdへ
C (Check) : 検証（再現解消・テスト・Design-L3レビュー）→ 結果を記録
A (Act)   : 標準化（再発防止をスキル/CLAUDE.md/ユビキタス言語へ）→ クローズ
```

## 対策の分岐判断（Plan段階の中核）★最重要

トリアージ後、対策を **軽微 / 本格** に振り分ける。
これは CLAUDE.md の「SDDを省略してよい場合」を Issue の Plan 段階に組み込んだもの。

| | 軽微 | 本格 |
|---|---|---|
| 判断基準 | 1ファイル以内の修正・UI文言変更・単純バグ | 再設計・複数ファイル・新ビジネスルール・新機能規模 |
| 対策案の場所 | **Issue内の `## 対策案 (Plan)` に直接記述** | Issue内は要点＋リンクのみ |
| 設計書 | 作らない（過剰ドキュメント化を防ぐ） | **`spec/{feature}/design.md` を新設**（既存SDDフロー） |
| フロー | Issue1枚でPDCA完結 | Issueは起点・状態管理に徹し、設計はspecへ委譲 |

**判断に迷う場合は必ずユーザーに「軽微対応 / 本格SDD どちらで進めますか？」と確認する。**

### 本格対策時のトレーサビリティ（双方向リンク）

- **Issue → spec**: Issueの `## 対策案` に「詳細設計は `spec/{feature}/design.md` を参照」と記載
- **spec → Issue**: design.md 先頭の `対応文書:` に Issueの文書ID（例 `ISSUE-ACCOUNTS-IMP-2026-002`）を記載

## 文書ID・ステータスの規約

**文書ID**: `ISSUE-{APP}-{BUG|IMP}-{年}-{連番3桁}`
- APP: 対象アプリ名（大文字）例: ACCOUNTS
- BUG: 不具合 / IMP: 改善
- 例: `ISSUE-ACCOUNTS-BUG-2026-001`

**ファイル名**: `ISSUE-{連番4桁}-{kebab-title}.md`（アプリ内で連番、台帳と一致させる）

**ステータス**（frontmatterで管理）:

| ステータス | 意味 |
|---|---|
| Open | 起票直後、未トリアージ |
| Triaged | トリアージ済み、対策方針決定済み |
| InProgress | 対応（実装）中 |
| Verifying | 検証中 |
| Closed | 対応完了・検証済み |
| Rejected | 対応しないと判断 |
| Deferred | 保留（優先度・時期の都合） |

## 実行フロー

```
Step 0: 依頼内容から「新規起票」か「既存Issue更新」かを判別する
Step 1: 対象アプリを特定する（不明なら application/ 配下を確認しユーザーに確認）
Step 2: 種別（不具合BUG / 改善IMP）を判定する
Step 3: date '+%Y/%m/%d %H:%M' で現在時刻を取得する
Step 4: 連番を決定する（issues/ 内の既存ファイル・台帳を確認して次番号）
Step 4.5: 起票に必要な項目が揃っているか確認する（下記「情報充足チェック」参照）
          不足・不明な必須項目があれば、推測で埋めずユーザーに質問してから進む
Step 5: references/issue-template.md を読み、テンプレートに沿ってIssueを作成
        - 不具合ならBUGセクション、改善ならIMPセクションを使う
Step 6: トリアージし、対策の軽微/本格を分岐判断（迷えばユーザー確認）
Step 7: issues/README.md（台帳）に行を追加/更新する
        - 台帳が無ければ references/index-template.md から新規作成
Step 8: 状態が進んだら frontmatter のステータスと更新日を更新する
```

## 起票時の情報充足チェック（絶対ルール）

起票（Step 4.5〜5）では、必須項目が揃っているかを必ず確認する。
**不足・不明な必須項目を推測で創作してはならない。**

**必須項目**:

| 種別 | 必須項目 |
|---|---|
| 不具合(BUG) | 事象（現象）／再現手順／期待動作 vs 実際の動作／影響範囲 |
| 改善(IMP) | 現状の課題／改善提案 |

**進め方**:

1. ユーザーの依頼文から確定できる項目は、そのまま採用する
2. 必須項目に不足・曖昧がある場合は、**起票する前にユーザーへ質問する**
   - 不足分は **まとめて1回で質問する**（AskUserQuestion 等）。小出しにしない
3. どうしても埋まらない・現時点で未調査の項目は、創作せず
   **「調査中」「未確認」と明示的に記載**する
   - 特に **再現手順・原因分析(root cause)** は推測で書かない。
     不具合の再現条件や原因を捏造すると、誤情報が Single Source of Truth として残るため
4. 任意項目（優先度・起票者・環境の詳細等）が不明な場合は、
   質問するか既定値（優先度=中 等）で埋め、後で更新してよい

## PDCAの各段階での更新ルール

- **Plan完了時**: `## 対策案 (Plan)` を記入、ステータスを Triaged に、台帳更新
- **Do実施時**: `## 実施内容 (Do)` に変更概要・対象ファイル・コミットを記入、ステータス InProgress
- **Check時**: `## 検証結果 (Check)` に再現解消・テスト結果・レビュー結果を記入、ステータス Verifying
  - 検証には既存の 実装レビュー（implement-review-l1）や verify を活用する
- **Act・クローズ時**: `## 振り返り・標準化 (Act)` に再発防止策と反映先を記入
  - ステータス Closed、`クローズ日` を記入、台帳更新
  - 標準化で得た知見は必要に応じてスキル/CLAUDE.md/ユビキタス言語へ反映を提案する

## 時刻の正確性（絶対ルール）

- 日付・時刻は必ず `date '+%Y/%m/%d %H:%M'` で取得した実際の値を記載する
- 推測・概算で書かない。各段階を更新するたびに時刻を取得する

## ユビキタス言語の遵守

- Issueの記述には対象アプリの `docs/ubiquitous_language.md` の用語を使用する
- 新用語が登場した場合は make-ubiquitous-language での追加を提案する

## 詳細ガイド

- Issue文書テンプレート: `references/issue-template.md`
- 台帳テンプレート: `references/index-template.md`
- PDCA運用ガイド（分岐基準・既存フロー接続・Act反映先）: `references/pdca-guide.md`
