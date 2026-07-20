# スキルテスト手順書（人間用）

## 概要

Claude Codeのカスタムスキルが意図通りに動作するかを検証する手順書。
新規スキル作成時・スキル修正時にこの手順に従ってテストを実施する。

---

## 前提条件

- Claude Codeが使用可能であること
- テスト対象のスキルが `.claude/skills/{skill-name}/SKILL.md` に配置済みであること
- skill-testerスキルが `.claude/skills/skill-tester/SKILL.md` に配置済みであること

---

## 手順1: テストの準備

### 1.1 テスト対象の確認

テスト対象のスキルが正しく配置されていることを確認する。

```bash
# スキルの配置確認
ls -la .claude/skills/{skill-name}/SKILL.md

# referenceがある場合はそちらも確認
ls -la .claude/skills/{skill-name}/references/
```

### 1.2 skill-testerの起動

Claude Codeで以下のように依頼する。

```
「{skill-name}スキルをテストして」
```

例:
```
「sddスキルをテストして」
「design-review-l1をテストして」
「requirements-review-l1のテストをお願い」
```

### 1.3 テストプロンプトの確認

skill-testerが対象スキルのdescriptionを分析し、テストプロンプトを自動生成する。
以下の4種類のプロンプトが提示される。

| 種類 | 意味 | 期待する結果 |
|------|------|------------|
| 正常トリガー | 明らかにこのスキルが担当すべきプロンプト | スキルが起動する |
| 類似トリガー | 言い換え・曖昧な表現 | スキルが起動する |
| 非トリガー | 別のスキルや通常対話で対応すべきプロンプト | スキルが起動しない |
| 境界ケース | 複数のスキルが競合しうるプロンプト | 正しいスキルが起動する |

**確認すること:**
- [ ] 生成されたプロンプトが妥当か
- [ ] 追加したいテストケースはないか
- [ ] 期待結果の認識が合っているか

問題があれば修正を依頼する。問題なければ「進めてください」と伝える。

---

## 手順2: Phase 1 — トリガーテスト

### 目的

スキルが正しいプロンプトで起動し、誤ったプロンプトでは起動しないことを確認する。

### やること

1. **Claude Codeで新しい会話を開始する**（既存の会話ではなく新規）
2. skill-testerが提示したテストプロンプトを**1つずつ入力**する
3. 各プロンプトに対して以下を確認する:
   - どのスキルが起動したか（またはスキルが起動しなかったか）
   - 起動したスキルは期待通りか
4. **結果をskill-testerの会話に戻って報告する**

### 報告の仕方

結果をskill-testerに伝える。例:

```
Phase 1の結果:
1. 「SDDで開発して」→ sddが起動した ✅
2. 「壁打ちから始めよう」→ sddが起動した ✅
3. 「要件定義書を作りたい」→ sddが起動した ✅
4. 「バグを修正して」→ スキルは起動しなかった ✅
5. 「設計書のレビューをお願い」→ sddが起動してしまった ❌（design-review-l1が起動すべき）
```

### 判定基準

| 基準 | PASS |
|------|------|
| 正常トリガー | 100%起動 |
| 類似トリガー | 80%以上起動 |
| 非トリガー | 100%起動しない |
| 境界ケース | 正しいスキルが起動 |

---

## 手順3: Phase 2 — reference読み込みテスト

### 目的

references/フォルダを持つスキルが、正しいreferenceを読み込むことを確認する。

### 前提

references/フォルダがないスキルはこのPhaseをスキップする。
skill-testerに「Phase 2はスキップ」と伝える。

### やること

1. skill-testerが提示する状況を再現するプロンプトを入力する
2. Claude Codeの出力の中で、どのreferenceファイルが読み込まれたかを確認する
   - Claude Codeは通常「Read ツールで〇〇を読み取りました」と表示する
3. 読み込まれたreferenceが期待通りかを確認する

### 確認例（design-review-l3の場合）

```
状況1: 「Swiftプロジェクトの実装レビューをお願い」
  → 期待: swift-clean-architecture.md + swift-coding-rules.md が読まれる
  → 実際: _____ が読まれた

状況2: 「Djangoの実装レビューをして」
  → 期待: django-clean-architecture.md + django-coding-rules.md が読まれる
  → 実際: _____ が読まれた
```

### 判定基準

- 正しいreferenceが選択される → PASS
- referenceの内容がレビュー結果に反映される → PASS

---

## 手順4: Phase 3 — 出力品質テスト

### 目的

スキルの出力が期待通りのフォーマット・内容であることを確認する。

### やること

1. スキルを実際の入力データ（またはサンプルデータ）で実行する
2. 出力結果を以下のチェックリストで確認する

### チェックリスト

**フォーマット:**
- [ ] 出力形式がSKILL.mdで定義されたフォーマットに沿っているか
- [ ] テーブルが正しく表示されているか
- [ ] セクション構成（見出し、区切り）が正しいか
- [ ] レビュー系の場合: サマリー + 検出事項一覧 + 総合判定が含まれるか

**内容:**
- [ ] SKILL.mdに定義されたチェック項目がすべて検査されているか（漏れがないか）
- [ ] OK/警告/NGの判定が妥当か（厳しすぎ/緩すぎないか）
- [ ] 修正案が具体的で、実行可能な内容か
- [ ] 関連文書（strategic_design.md、ubiquitous_language.md等）を読み込んでいるか

**プロセス:**
- [ ] SDDスキルの場合: 承認ゲートで止まるべきところで止まるか
- [ ] レビュースキルの場合: 次のレビューレベルへの案内が含まれるか
- [ ] 対象ファイルが未指定の場合: ユーザーに質問しているか

### 結果の報告

チェックリストの結果をskill-testerに伝える。例:

```
Phase 3の結果:
フォーマット: PASS（テーブル表示OK、セクション構成OK）
内容: CONDITIONAL（チェック項目の漏れが1件あった — 観点3の2番目）
プロセス: PASS（関連文書の読み込みOK、次のステップ案内OK）
```

---

## 手順5: Phase 4 — エッジケーステスト

### 目的

異常な入力や想定外の状況でスキルが適切に振る舞うことを確認する。

### やること

以下のケースを1つずつ試し、振る舞いを確認する。

| # | テストケース | 操作 | 期待する振る舞い |
|---|------------|------|----------------|
| 1 | 引数なし | スキル名だけで実行 | ユーザーに対象ファイルを質問する |
| 2 | 存在しないパス | 存在しないファイルパスを指定 | エラーを報告し、正しいパスを質問する |
| 3 | strategic_design.md不在 | ファイルがない状態で実行 | 該当観点をスキップし、その旨を記載する |
| 4 | ubiquitous_language.md不在 | ファイルがない状態で実行 | 用語チェックをスキップし、その旨を記載する |

すべてのケースをテストする必要はない。対象スキルに関連するケースのみで良い。
skill-testerが対象スキルに適したエッジケースを提案してくれる。

---

## 手順6: テスト結果の記録

### 自動記録

skill-testerがPhase 1〜4の結果を集約し、テスト結果ファイルを自動生成する。

### 保存先

```
.claude/skills/{対象スキル名}/tests/test-result-{YYYY-MM-DD}.md
```

### 確認すること

- [ ] テスト結果ファイルが正しい場所に保存されたか
- [ ] 総合判定（PASS / CONDITIONAL PASS / FAIL）が記載されているか
- [ ] FAILの場合、問題と改善案が記載されているか

---

## 手順7: 問題の修正と再テスト

### FAILが発生した場合

1. skill-testerが提示する改善案を確認する
2. 改善案が妥当であれば、修正を依頼する
3. 修正後、**問題が発生したPhaseのみ再テスト**する

| 問題のPhase | 再テスト範囲 |
|------------|------------|
| Phase 1（トリガー）| Phase 1のみ |
| Phase 2（reference）| Phase 2のみ |
| Phase 3（出力品質）| Phase 3のみ |
| Phase 4（エッジケース）| Phase 4のみ |

### 修正→再テストのサイクル

```
問題発見 → 改善案確認 → SKILL.md修正 → 該当Phase再テスト → PASS確認
```

修正は1回につき1箇所を基本とする。複数箇所を同時に修正すると、
どの修正が効果があったか判断できなくなる。

---

## 手順8: テスト完了の判断

### 完了条件

- [ ] Phase 1〜4 すべて PASS（またはスキップの妥当な理由がある）
- [ ] テスト結果ファイルが保存されている
- [ ] 総合判定が PASS

### 総合判定基準

| 判定 | 条件 |
|------|------|
| **PASS** | 全Phase PASS |
| **CONDITIONAL PASS** | FAIL 1〜2件、かつ軽微な問題のみ |
| **FAIL** | FAIL 3件以上、またはPhase 1（トリガー）がFAIL |

---

## オプション手順: Skill Creatorによるdescription最適化

Phase 1（トリガーテスト）で問題が発生した場合、
Skill Creatorのdescription最適化ループを使って改善できる。

### 前提条件

- Claude Code CLIが利用可能であること（`claude -p` コマンドが実行できること）
- スキルが `.claude/skills/{skill-name}/SKILL.md` に配置済みであること

### Step 1: トリガー評価セットの作成

Phase 1で使用したテストプロンプトをJSON形式に変換する。

```json
{
  "queries": [
    {"text": "SDDで開発して", "should_trigger": true},
    {"text": "スペック駆動開発で進めて", "should_trigger": true},
    {"text": "壁打ちから始めたい", "should_trigger": true},
    {"text": "要件定義書を作りたい", "should_trigger": true},
    {"text": "バグを修正して", "should_trigger": false},
    {"text": "コードをリファクタリングして", "should_trigger": false},
    {"text": "設計書のレビューをお願い", "should_trigger": false},
    {"text": "ユビキタス言語集を作って", "should_trigger": false}
  ]
}
```

このファイルを以下のパスに保存する:

```
.claude/skills/{skill-name}/tests/trigger-eval.json
```

### 作成のポイント

- `should_trigger: true` と `should_trigger: false` を**同数程度**用意する
- `should_trigger: false` には、**他のスキルが担当すべきプロンプト**を含める
- 最低8個、理想は12〜16個のプロンプトを用意する
- シンプルすぎるプロンプト（「読んで」「やって」等）は避ける
  - Claude Codeは単純なプロンプトにはスキルなしで対応しようとするため、テスト結果が不安定になる

### Step 2: 最適化ループの実行

Claude Code上で以下のコマンドを実行する:

```bash
python -m scripts.run_loop \
  --eval-set .claude/skills/{skill-name}/tests/trigger-eval.json \
  --skill-path .claude/skills/{skill-name} \
  --max-iterations 5 \
  --verbose
```

### 実行中の確認

- 最適化ループは数分〜十数分かかる
- 各イテレーションで以下が表示される:
  - 現在のdescriptionでのトリガー率（train / test）
  - 提案された新しいdescription
  - 新しいdescriptionでのトリガー率
- 最大5回繰り返し、最良のdescriptionが選ばれる

### Step 3: 結果の確認

最適化完了後、結果のJSONに `best_description` が含まれる。

```json
{
  "best_description": "最適化されたdescriptionテキスト...",
  "train_score": 0.95,
  "test_score": 0.92
}
```

### Step 4: descriptionの更新

1. 現在のdescriptionと最適化結果を比較する
2. 最適化結果が改善されている場合は、SKILL.mdのdescriptionを更新する

```markdown
# 更新前
description: |
  （元のdescription）

# 更新後
description: |
  （best_descriptionの内容）
```

3. 更新前のdescriptionはテスト結果ファイルに記録しておく

### Step 5: 再テスト

descriptionを更新した後、**Phase 1（トリガーテスト）を再実施**する。

```
「{skill-name}スキルのPhase 1を再テストして」
```

最適化後のdescriptionで全テストプロンプトがPASSすることを確認する。

### 注意事項

- description最適化は**トリガーの精度のみ**を改善する。スキルの中身（出力品質）は改善しない
- 最適化結果が必ずしも良いとは限らない。元のdescriptionの方が良い場合は採用しない
- 最適化後にdescriptionが大幅に変わった場合は、**他のスキルとの競合**が発生していないか確認する
- 1つのスキルのdescriptionを最適化した後、関連する他のスキルのPhase 1も再テストすることを推奨する

---

## テスト実施の推奨タイミング

| タイミング | 実施するPhase | 備考 |
|-----------|-------------|------|
| スキル新規作成時 | Phase 1〜4 すべて | 初回は全Phaseを実施 |
| description修正時 | Phase 1（トリガー） | 他のスキルの境界ケースも確認 |
| SKILL.md本体修正時 | Phase 3（出力品質） | 出力フォーマット・内容の変化を確認 |
| reference追加・修正時 | Phase 2（reference） | 正しいreferenceが選択されるか確認 |
| 他のスキルを追加した時 | Phase 1の境界ケース | 新スキルとの競合を確認 |
| Skill Creator最適化後 | Phase 1（トリガー） | 最適化の効果を確認 |

---

## 付録: テスト結果ファイルのサンプル

```markdown
# スキルテスト結果: sdd

テスト日: 2026/04/11
テスト者: Masatsugu
スキルバージョン: 初版（2026/04/11作成）
総合判定: CONDITIONAL PASS

---

## Phase 1: トリガーテスト

| # | 種類 | プロンプト | 期待結果 | 実際結果 | 判定 |
|---|------|----------|---------|---------|------|
| 1 | 正常 | SDDで開発して | sdd起動 | sdd起動 | ✅ |
| 2 | 正常 | スペック駆動開発で進めて | sdd起動 | sdd起動 | ✅ |
| 3 | 類似 | 壁打ちから始めよう | sdd起動 | sdd起動 | ✅ |
| 4 | 類似 | 要件定義書を作りたい | sdd起動 | sdd起動 | ✅ |
| 5 | 非 | バグを修正して | 起動しない | 起動しない | ✅ |
| 6 | 非 | リファクタリングして | 起動しない | 起動しない | ✅ |
| 7 | 境界 | 設計レビューをして | design-review-l1 | sdd起動 | ❌ |
| 8 | 境界 | 用語集を作って | make-ubiquitous-language | sdd起動 | ❌ |

Phase 1 判定: CONDITIONAL PASS（境界ケースで競合あり）

---

## 発見した問題

| # | Phase | 問題 | 重要度 | 対応案 | 対応状況 |
|---|-------|------|--------|--------|---------|
| 1 | Phase 1 | 「設計レビュー」でsddが起動 | 中 | descriptionに「設計レビューの場合はdesign-review-l1を使用」を追記 | 未対応 |
| 2 | Phase 1 | 「用語集を作って」でsddが起動 | 中 | descriptionの範囲を限定 | 未対応 |

---

## 次のアクション

- [ ] sddスキルのdescription修正（境界ケース対応）
- [ ] 修正後Phase 1再テスト
- [ ] Skill Creator最適化の検討
```
