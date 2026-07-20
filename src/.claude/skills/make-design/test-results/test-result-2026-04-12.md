# スキルテスト結果: make-design

テスト日: 2026/04/12 01:34
テスト者: Masatsugu Koga
スキルバージョン: （SKILL.md 現行版）
総合判定: **進行中（INCOMPLETE）**

---

## スキル情報

- name: make-design
- description: 承認済み要件定義書に基づき、機能設計書（design.md）を作成する。ドメインモデル、アーキテクチャ概要、データモデル、API設計、エラーハンドリング方針を含む。Clean Architectureレイヤーは技術スタックに応じたreferenceを参照。
- references: あり（2ファイル: `swift-clean-architecture.md`, `django-clean-architecture.md`）

---

## Phase 1: トリガーテスト

| # | 種類 | プロンプト | 期待結果 | 実際結果 | 判定 |
|---|------|----------|---------|---------|------|
| 1 | 正常トリガー | `docs/specs/foo/requirements.md の設計書を作って` | make-design起動 | 未実施 | - |
| 2 | 正常トリガー | `機能設計書を作成して` | make-design起動 | make-design起動 | ✅ PASS |
| 3 | 正常トリガー | `Phase 3の設計をしたい` | make-design起動 | 未実施 | - |
| 4 | 類似トリガー | `design.mdを作って` | make-design起動 | 未実施 | - |
| 5 | 類似トリガー | `要件定義書をもとに設計をお願い` | make-design起動 | 未実施 | - |
| 6 | 非トリガー | `このバグを修正して` | 起動しない | 未実施 | - |
| 7 | 非トリガー | `CLAUDE.mdを更新して` | generate-claude-md起動 | 未実施 | - |
| 8 | 境界ケース | `棚卸し機能の要件定義書を作って` | make-design起動しない | 未実施 | - |
| 9 | 境界ケース | `設計書のレビューをして` | make-design起動しない | 未実施 | - |

Phase 1 判定: **INCOMPLETE**（1/9 実施、1件 PASS、残り8件は後日実施）

---

## Phase 2: reference読み込みテスト

未実施（後日実施）

Phase 2 判定: **INCOMPLETE**

予定テストケース:
1. CLAUDE.mdの技術スタックがDjango/Pythonの状態で設計書作成 → `references/django-clean-architecture.md` が読み込まれること
2. Swiftプロジェクト想定で設計書作成 → `references/swift-clean-architecture.md` が読み込まれること
3. design-review-l1/l3 が未存在の状態での警告動作確認

---

## Phase 3: 出力品質テスト

未実施（後日実施）

Phase 3 判定: **INCOMPLETE**

予定チェック項目:
- 出力フォーマットがSKILL.md定義（文書ID、9セクション構成）に沿っているか
- ユビキタス言語を一貫して使用しているか
- referenceのメタデータ（version, updated, source-name）が記載されているか
- 設計書全文をユーザーに提示してから保存しているか
- 保存後「テスト設計書の作成に進みますか？」の案内があるか

---

## Phase 4: エッジケーステスト

未実施（後日実施）

Phase 4 判定: **INCOMPLETE**

予定テストケース:
1. 引数なしで実行 → `docs/specs/`をGlob探索しユーザーに確認するか
2. 存在しないファイルパスを指定 → エラー報告するか
3. 未承認の要件定義書を指定 → 承認確認のメッセージを出すか
4. referenceバージョン不一致時 → 警告を出して続行確認するか

---

## 総合判定

| Phase | 判定 |
|-------|------|
| Phase 1: トリガーテスト | INCOMPLETE（1/9 実施） |
| Phase 2: reference読み込みテスト | INCOMPLETE |
| Phase 3: 出力品質テスト | INCOMPLETE |
| Phase 4: エッジケーステスト | INCOMPLETE |
| **総合** | **INCOMPLETE（進行中）** |

---

## 発見した問題

現時点ではなし。

---

## 改善メモ

- プロンプト#2「機能設計書を作成して」は期待通りトリガーされ、descriptionのトリガーフレーズが有効に機能していることを確認。

---

## 次のアクション

- [ ] Phase 1 残り8件のトリガーテストを実施
- [ ] Phase 2 reference読み込みテストを実施
- [ ] Phase 3 出力品質テストを実施（実際に設計書を作らせて評価）
- [ ] Phase 4 エッジケーステストを実施
- [ ] 全Phase完了後、本ファイルを更新して総合判定を確定
