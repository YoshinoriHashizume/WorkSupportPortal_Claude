---
文書ID: ISSUE-GNK-IMP-2026-001
種別: 改善
ステータス: Triaged
優先度: 中
起票者: Hashizume
起票日: 2026/08/25 13:55
更新日: 2026/08/25 13:55
クローズ日:
対象コンテキスト: gonenkukumi
対象機能: 基幹 Oracle（MARI）接続の共有腐敗防止層
対応文書: なし
外部リンク:
---

# Oracle 接続プリミティブが共有カーネル（sales）ではなく gonenkukumi に置かれている

## 現状の課題

`docs/strategic_design.md` §3.1 は、基幹 Oracle 接続の共有腐敗防止層を
**コンテキスト H（`application/sales/`）** と定めている。
しかし実体は逆向きになっている。

- `application/sales/infrastructure/oracle/client.py` は、接続プリミティブ
  （`oracle_config` / `oracle_connect_timeout_seconds` / `oracle_connection` /
  `rows_as_dicts` / `use_mock`）を **`application/gonenkukumi/infrastructure/oracle/client.py`
  から re-export しているだけ** である。
- そのため **共有カーネル（H）が業務コンテキスト（C: 5年9組）に依存する** という、
  依存方向が逆転した参照が残っている。
- 参照元の `gonenkukumi/infrastructure/oracle/client.py` は約 978 行あり、
  共有すべき接続プリミティブと、5年9組固有のクエリ（BOM 展開等）が同一ファイルに同居している。

2026/08/25 の DDD レビュー是正では、承認スコープが「例外クラスの移設」に限られていたため、
`OracleNotConfiguredError` / `OracleQueryError` のみを
`application/sales/domain/value_objects/errors.py` へ移設した。
接続プリミティブの移設は未実施であり、
`config/tests/test_clean_architecture.py` の `KNOWN_CONTEXT_LEAKS` に
既知の逸脱として登録してある（テストは通るが、逸脱として明示されている状態）。

## 改善提案

`gonenkukumi/infrastructure/oracle/client.py` を 2 つに分ける。

1. **接続プリミティブ** → `application/sales/infrastructure/oracle/client.py` へ移す（実体として）
2. **5年9組固有のクエリ** → `gonenkukumi/infrastructure/oracle/` に残し、1 を import する

移設完了後、`config/tests/test_clean_architecture.py` の `KNOWN_CONTEXT_LEAKS` から
`("sales", "application.gonenkukumi.infrastructure.oracle.client")` と
`("sales", "application.gonenkukumi.infrastructure.oracle.customers")` を削除する。
同テストの `test_known_context_leaks_are_not_stale` が、削除漏れを検出する。

## 期待効果

- 共有カーネルが業務コンテキストに依存する逆転を解消し、戦略的設計書の記述と実装を一致させる。
- 5年9組の変更が、Oracle を参照する他の 3 コンテキスト（A・B・D）へ波及しなくなる。

## 代替案

- **戦略的設計書の側を実装に合わせる**（H の実体は gonenkukumi とする）。
  仕様が Single Source of Truth という原則（CLAUDE.md §3）に反するため採らない。
- **現状維持**: 既知の逸脱として登録済みであり、動作上の問題は無い。
  ただし 5年9組の改修時に他コンテキストを壊すリスクが残る。

---

## 対策案 (Plan)

- 対策区分: **本格**
- 978 行のファイル分割と、参照元 4 コンテキストの import 変更を伴うため、
  Issue 内では完結させない。着手時に `spec/{feature}/` を新設する。
- 分割は振る舞いを変えない純粋な移設であるため、既存テスト（Oracle 接続はモック既定）で
  回帰を検出できる見込み。移設前後で全件テストの件数が変わらないことを確認する。
- **基幹 Oracle（MARI）は参照専用**。移設にあたって INSERT / UPDATE / DELETE を導入しない。

## 実施内容 (Do)

- 変更概要: 未着手
- 対象ファイル:
- コミット:

## 検証結果 (Check)

- 期待効果の達成: 未
- テスト結果:
- レビュー結果:

## 振り返り・標準化 (Act)

- 標準化した内容:
- 反映先:
- 派生Issue: なし
