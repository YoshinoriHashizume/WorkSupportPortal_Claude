# スキルテスト結果: csharp-requirements-gen

テスト日: 2026/04/12 02:26
テスト者: Masatsugu Koga
スキルバージョン: （SKILL.md 初版、Apr 12 02:05 作成）
総合判定: **FAIL**

---

## スキル情報

- name: csharp-requirements-gen
- description: C# Clean Architectureコードを層別に静的解析し、SDD準拠の要件定義書を逆引きで生成
- references: あり（`domain_analysis_guide.md`, `requirements_template.md`）
- allowed-tools: 未定義
- argument-hint: 未定義

---

## 事前確認で発見した問題（テスト前）

| # | 項目 | 内容 | 重要度 |
|---|------|------|--------|
| P1 | ファイル名 | 初回 `Skill.txt` → `Skill.md` → `SKILL.md` と段階的に修正。最終的に正常認識 | 中（解決済み） |
| P2 | フロントマター | `argument-hint`, `allowed-tools` が未定義 | 中 |
| P3 | 出力先パス | `/mnt/user-data/outputs/requirements.md` はClaude.ai Web向けで不適切 | **高** |
| P4 | `present_files` | Claude Codeに存在しないツール | **高** |
| P5 | `find` 多用 | Claude CodeではGlob/Grep推奨 | 低 |

---

## Phase 1: トリガーテスト

| # | 種類 | プロンプト | 期待結果 | 実際結果 | 判定 |
|---|------|----------|---------|---------|------|
| 1 | 正常トリガー | `このC#プロジェクトのコードから要件定義書を作って` | 起動 | 未実施 | - |
| 2 | 正常トリガー | `既存のC#コードを要件定義書に起こして` | 起動 | 起動 | ✅ PASS |
| 3 | 正常トリガー | `Clean ArchitectureのC#コードベースを分析して要件を抽出して` | 起動 | 未実施 | - |
| 4 | 類似トリガー | `この.slnのrequirements.mdを自動生成して` | 起動 | 未実施 | - |
| 5 | 類似トリガー | `C#プロジェクトから機能一覧を作って` | 起動 | 未実施 | - |
| 6 | 非トリガー | `このバグを修正して` | 起動しない | 未実施 | - |
| 7 | 非トリガー | `機能設計書を作成して` | make-design起動 | 未実施 | - |
| 8 | 境界ケース | `Djangoアプリのコードから要件定義書を作って` | 起動しない | 未実施 | - |
| 9 | 境界ケース | `要件定義書を作って` | 言語確認 or 起動 | 未実施 | - |

Phase 1 判定: **INCOMPLETE（1/9 実施、1件 PASS）**

---

## Phase 2: reference読み込みテスト

判定: **SKIP（保留）** — 実際にスキルを動かすテストが必要なため後日実施

予定テストケース:
1. ダミーC#プロジェクトでスキル起動 → `domain_analysis_guide.md` が Phase 2段階で読まれるか
2. 同上 → `requirements_template.md` が Phase 5段階で読まれるか
3. 抽出結果が domain_analysis_guide.md の判定基準に沿っているか
4. 出力 requirements.md が requirements_template.md の7セクション構成に沿っているか

---

## Phase 3: 出力品質テスト（静的レビュー）

SKILL.mdの記述から構造的問題を検出。

| # | 重要度 | カテゴリ | 問題 | 該当箇所 |
|---|-------|---------|------|---------|
| Q1 | **高** | 出力先 | `/mnt/user-data/outputs/requirements.md` はClaude.ai Web向けパス | L165 |
| Q2 | **高** | ツール | `present_files` はClaude Codeに存在しない | L165 |
| Q3 | **高** | 規約不一致 | プロジェクト正式保存先は `docs/specs/{feature-name}/requirements.md`。スキルの出力先と不整合 | L160-165 |
| Q4 | 中 | フロントマター | `argument-hint`, `allowed-tools` 未定義 | L1-12 |
| Q5 | 中 | コマンド指定 | `find` 多用。Claude CodeはGlob/Grep推奨 | L36-37, L52-58, L84-85, L108 |
| Q6 | 中 | 承認フロー欠如 | SDD原則「Phase 5後にユーザー承認」が無い | L144-165 |
| Q7 | 中 | 文書ID規約 | CLAUDE.md必須の「文書ID・作成日・対応文書」記載指示なし | 全体 |
| Q8 | 中 | ユビキタス言語 | `docs/ubiquitous_language.md` 照合・更新指示なし | 全体 |
| Q9 | 低 | Read指示 | referenceファイルのRead指示が曖昧（「参照しながら実施する」のみ） | L79, L146 |
| Q10 | 低 | 出力形式 | 出力構造をSKILL.md内に明記せずreference依存 | L144-156 |
| Q11 | 低 | ステップ重複 | Phase 0とPhase 1の構造把握が重複気味 | L26-58 |

Phase 3 判定: **FAIL**（Q1〜Q3が致命的）

---

## Phase 4: エッジケーステスト（静的レビュー）

| # | ケース | 期待挙動 | SKILL.md指示 | 判定 |
|---|--------|---------|-------------|------|
| 1 | 引数なしで起動 | ユーザーに対象パスを質問 | 明示的質問指示なし | △ |
| 2 | 存在しないパス指定 | エラー報告＆再質問 | 記述なし | ✕ |
| 3 | `.sln`が無い | ユーザー確認 | 記述なし | ✕ |
| 4 | C#以外のプロジェクト | 非該当を報告し中止 | 指示なし | ✕ |
| 5 | Domain層が見つからない | マッピング結果を提示し確認 | スペルミス注記のみ、無い場合の指示なし | △ |
| 6 | 大規模プロジェクト（ファイル数500超） | 主要部分を優先分析 | 「50未満でも大規模でも適用可能」のみで戦略なし | △ |
| 7 | 実装が空/テストしかない | レビュー不可を報告 | 記述なし | ✕ |
| 8 | `bin/`, `obj/`, `.git/` | 除外する | Phase 0-1で除外指示あり | ✅ |

Phase 4 判定: **FAIL**（エラーハンドリング・異常系指示の全面欠落）

---

## 総合判定

| Phase | 判定 |
|-------|------|
| Phase 1: トリガーテスト | INCOMPLETE（1/9、1件 PASS） |
| Phase 2: reference読み込みテスト | SKIP（保留） |
| Phase 3: 出力品質テスト（静的） | **FAIL** |
| Phase 4: エッジケーステスト（静的） | **FAIL** |
| **総合** | **FAIL** |

**致命的要因**: Phase 3のQ1〜Q3（Claude.ai Web向けの出力先指定・プロジェクト規約違反）により、現状のスキルはClaude Code環境で正常に動作しない可能性が高い。

---

## 発見した問題（まとめ）

| # | Phase | 問題 | 重要度 | 対応案 | 対応状況 |
|---|-------|------|--------|--------|---------|
| Q1 | Phase 3 | 出力先が `/mnt/user-data/outputs/` | 高 | `docs/specs/{feature-name}/requirements.md` に変更 | 未対応 |
| Q2 | Phase 3 | `present_files` 使用 | 高 | Write ツールに置換し該当行削除 | 未対応 |
| Q3 | Phase 3 | 規約不一致 | 高 | プロジェクトのSDD規約（CLAUDE.md）に合わせる | 未対応 |
| Q4 | Phase 3 | フロントマター不備 | 中 | `argument-hint`, `allowed-tools` 追加 | 未対応 |
| Q6 | Phase 3 | 承認ゲート欠如 | 中 | Phase 5後にユーザー承認ステップを追加 | 未対応 |
| Q7 | Phase 3 | 文書ID欠如 | 中 | テンプレート冒頭に文書ID等を追加 | 未対応 |
| Q8 | Phase 3 | UL照合欠如 | 中 | `docs/ubiquitous_language.md` 照合・更新指示を追加 | 未対応 |
| E2 | Phase 4 | 存在しないパス | 中 | エラーハンドリング節を追加 | 未対応 |
| E3 | Phase 4 | `.sln`無し | 中 | 同上 | 未対応 |
| E4 | Phase 4 | 非C#プロジェクト | 中 | 非該当時の中止指示 | 未対応 |
| E7 | Phase 4 | 空プロジェクト | 低 | レビュー不可の報告指示 | 未対応 |

---

## 改善メモ

- Phase 1 #2 の起動成功から、description のトリガーフレーズは有効に機能している
- 本スキルは元々 Claude.ai Web UI 向けに書かれたものを Claude Code に移植した可能性が高い
- referenceファイル自体（domain_analysis_guide.md, requirements_template.md）は内容が整っており、そのまま流用可能
- make-design スキルと構造が似ているため、make-design の構成を参考に修正するとよい

---

## 次のアクション

- [ ] Q1〜Q3（致命的）の修正をSKILL.mdに適用
- [ ] Q4, Q6〜Q8（中程度）の修正をSKILL.mdに適用
- [ ] Phase 4のエッジケース対応指示を追加
- [ ] 修正後、Phase 1残り8件とPhase 2を実機で再テスト
- [ ] 修正後、ダミーC#プロジェクトで end-to-end 動作確認
