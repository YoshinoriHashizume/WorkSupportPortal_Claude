文書ID: TASK-ASP-IMPORT-DATA-2026-001
作成日: 2026/08/26
更新日: 2026/08/26
対応文書: ./design.md（DESIGN-ASP-IMPORT-DATA-2026-001）, ./test-design.md（TEST-ASP-IMPORT-DATA-2026-001）, ./requirements.md（REQ-ASP-IMPORT-DATA-2026-001）

# 02_asp-import-data タスクリスト

## 状況チェックシート

**凡例**: `[ ]` 未着手 / `[~]` 進行中 / `[✅YYYY/MM/DD HH:MM]` 完了 / `[- YYYY/MM/DD HH:MM]` スキップ

| # | タスク | レイヤー | 対象ファイル | 状態 |
|---|---|---|---|---|
| 1 | `NormalizedValue` と整形のテスト作成 | domain | `tests/test_asp_import.py` | [✅2026/08/26 10:54] |
| 2 | `NormalizedValue` と整形の実装 | domain | `domain/value_objects/asp_import.py` | [✅2026/08/26 10:55] |
| 3 | `AspFieldCheck` のテスト作成 | domain | `tests/test_asp_import.py` | [✅2026/08/26 10:59] |
| 4 | `AspFieldCheck` と `ASP_FIELD_CHECKS` の実装 | domain | `domain/value_objects/asp_import.py` | [✅2026/08/26 11:01] |
| 5 | `DepartmentCode` のテスト作成 | domain | `tests/test_asp_import.py` | [✅2026/08/26 11:02] |
| 6 | `DepartmentCode` の実装 | domain | `domain/value_objects/asp_import.py` | [✅2026/08/26 11:02] |
| 7 | `AspImportWarning` / `AspImportWarnings` のテスト作成 | domain | `tests/test_asp_import.py` | [✅2026/08/26 11:04] |
| 8 | `AspImportWarning` / `AspImportWarnings` の実装 | domain | `domain/value_objects/asp_import.py` | [✅2026/08/26 11:05] |
| 9 | `AspPasteLayout` / `AspImportRow` のテスト作成 | domain | `tests/test_asp_import.py` | [✅2026/08/26 11:06] |
| 10 | `AspPasteLayout` / `AspImportRow` の実装 | domain | `domain/value_objects/asp_import.py` | [✅2026/08/26 11:10] |
| 11 | `AspImportRows` のテスト作成 | domain | `tests/test_asp_import.py` | [✅2026/08/26 11:11] |
| 12 | `AspImportRows` の実装 | domain | `domain/value_objects/asp_import.py` | [✅2026/08/26 11:12] |
| 13 | `AmendmentRows` のテスト作成 | domain | `tests/test_asp_import.py` | [✅2026/08/26 11:13] |
| 14 | `AmendmentRows` の実装 | domain | `domain/value_objects/asp_import.py` | [✅2026/08/26 11:14] |
| 15 | 既存テストを新しい VO・コレクションの呼び出しへ書き換え | domain | `tests/test_asp_import.py` | [✅2026/08/26 11:16] |
| 16 | スナップショットの `site_warning` と読み出しのテスト作成 | domain | `tests/test_reconcile_cache.py` | [✅2026/08/26 11:19] |
| 17 | `site_warning` と `load_amendment_snapshot` の実装 | domain | `domain/value_objects/reconcile_cache.py` | [✅2026/08/26 11:20] |
| 18 | 縮退結果の保存と不採用のテスト改修 | domain | `tests/test_usecase_list_page.py` | [✅2026/08/26 11:21] |
| 19 | 縮退結果の保存と不採用の実装 | domain | `domain/value_objects/reconcile_data.py` | [✅2026/08/26 11:22] |
| 20 | `ExportAspImport` のテスト改修・追加 | use_cases | `tests/test_usecase_export_asp_import.py` | [✅2026/08/26 11:27] |
| 21 | `ExportAspImport` の実装（`execute_safe` 削除） | use_cases | `use_cases/export_asp_import.py` | [✅2026/08/26 11:28] |
| 22 | 旧モジュール関数 6 件の削除（Refactor） | domain | `domain/value_objects/asp_import.py` | [✅2026/08/26 11:29] |
| 23 | 組み立てから `_list_all_fn()` の受け渡しを削除 | interfaces | `interfaces/wiring.py` | [✅2026/08/26 11:30] |
| 24 | ビュー・画面のテスト改修・追加 | interfaces | `tests/test_asset_inventory_views.py` | [✅2026/08/26 11:39] |
| 25 | `export_asp_import` ビューと活性判定の実装 | interfaces | `interfaces/views.py`, `domain/value_objects/reconcile_cache.py` | [✅2026/08/26 11:40] |
| 26 | 作成ボタンの活性・非活性の描画 | interfaces | `templates/asset_inventory/list.html` | [✅2026/08/26 11:43] |
| 27 | 画面スクリプトの `unavailable` 分岐と活性復元 | interfaces | `static/js/asset-inventory-list.js` | [✅2026/08/26 11:46] |
| 28 | 全テストの実行と手動確認（M-01〜M-04） | — | — | [✅2026/08/26 11:49] |
| 29 | 機能仕様書への追記 | docs | `docs/資産棚卸結果_機能仕様書.md` | [✅2026/08/26 12:15] |
| 30 | テスト仕様書への追記 | docs | `docs/資産棚卸結果_テスト仕様書.md` | [✅2026/08/26 12:21] |

### 仕様変更（2026/08/26）— 追加 4 列（44・59・64・65 列目）の反映

利用者から提供された ASP 貼り付けレイアウトにより 44・59・65 列目の対応が判明し（**D-11**）、
続く指示「メーカーコードを旧資産番号の前（抽出コード１８）に追加してください」により
64 列目の対応が判明した（**D-13**）。出力列は **5 列 → 9 列**に増え、
**D-05（ASP に対応列が存在しない）は完全に撤回**された。
仕様書 → コード → テスト → タスク管理の順に、1 ファイルずつ実施する。

| # | タスク | レイヤー | 対象ファイル | 状態 |
|---|--------|---------|------------|------|
| 31 | 要件定義書の改訂（9 列・D-11〜D-13・C-18〜C-22） | docs | `docs/spec/02_asp-import-data/requirements.md` | [✅2026/08/26 17:06 記録] |
| 32 | 機能設計書の改訂（DD-08・DD-09・列定数・変換規則） | docs | `docs/spec/02_asp-import-data/design.md` | [✅2026/08/26 17:06 記録] |
| 33 | テスト設計書の改訂（TC-080〜085・044・045・07M・07N・060〜062） | docs | `docs/spec/02_asp-import-data/test-design.md` | [✅2026/08/26 17:02] |
| 34 | 機能仕様書への反映（版 2.71） | docs | `docs/資産棚卸結果_機能仕様書.md` | [✅2026/08/26 17:06 記録] |
| 35 | ユビキタス言語集への反映（V-312〜V-315） | docs | `docs/ubiquitous_language.md` | [✅2026/08/26 17:06 記録] |
| 36 | 突合結果行への追加コード 3 件と部品一覧の拡張 | domain | `domain/repositories/ports.py` | [✅2026/08/26 17:06 記録] |
| 37 | 追加コード 3 件の取り込み | domain | `domain/value_objects/row_display.py` | [✅2026/08/26 17:06 記録] |
| 38 | 追加コード 3 件のセッション往復 | domain | `domain/value_objects/reconcile_cache.py` | [✅2026/08/26 17:06 記録] |
| 39 | 44・59・64・65 列目の出力とチェック仕様 | domain | `domain/value_objects/asp_import.py` | [✅2026/08/26 17:06 記録] |
| 40 | ASP 取り込み用データのテスト改修・追加 | test | `tests/test_asp_import.py` | [✅2026/08/26 17:06 記録] |
| 41 | ユースケースのフィクスチャ改修と 9 列の検証 | test | `tests/test_usecase_export_asp_import.py` | [✅2026/08/26 16:58] |
| 42 | 追加コード 3 件のセッション往復のテスト（07M・07N） | test | `tests/test_reconcile_cache.py` | [✅2026/08/26 17:03] |
| 43 | 部品一覧に追加コード 3 件が含まれることのテスト（060） | test | `tests/test_asset_fields.py` | [✅2026/08/26 17:04] |
| 44 | 突合結果行への取り込みのテスト（061・062） | test | `tests/test_row_display.py` | [✅2026/08/26 17:05] |
| 45 | 本タスクリストへの記録 | docs | `docs/spec/02_asp-import-data/tasks.md` | [✅2026/08/26 17:06] |
| 46 | 要件定義書の改訂（REQ-F-007 の警告文詳細化・チェック `M` 対象列の補正） | docs | `docs/spec/02_asp-import-data/requirements.md` | [✅2026/08/26 17:44 記録] |
| 47 | 機能設計書の改訂（警告文の構成・`AspFieldCheck.position`） | docs | `docs/spec/02_asp-import-data/design.md` | [✅2026/08/26 17:44 記録] |
| 48 | テスト設計書の改訂（TC-046・047・063・067〜069・073〜075） | docs | `docs/spec/02_asp-import-data/test-design.md` | [✅2026/08/26 17:44 記録] |
| 49 | 警告文の理由別明細行化と列位置・該当値の付与 | domain | `domain/value_objects/asp_import.py` | [✅2026/08/26 17:44 記録] |
| 50 | 警告文のテスト改修・追加 | test | `tests/test_asp_import.py` | [✅2026/08/26 17:44 記録] |
| 51 | 警告文の改行保持 | interfaces | `static/css/app.css` | [✅2026/08/26 17:44 記録] |
| 52 | 本タスクリストへの記録（46〜51） | docs | `docs/spec/02_asp-import-data/tasks.md` | [✅2026/08/26 17:44] |
| 53 | 要件定義書の改訂（REQ-F-006 に半角変換・領域長切り捨てを追加、D-14、C-23〜C-25） | docs | `docs/spec/02_asp-import-data/requirements.md` | [✅2026/08/27 10:53] |
| 54 | 機能設計書の改訂（DD-10 値の寄せ・`AdjustedValue`） | docs | `docs/spec/02_asp-import-data/design.md` | [✅2026/08/27 10:58] |
| 55 | テスト設計書の改訂（TC-086〜104） | docs | `docs/spec/02_asp-import-data/test-design.md` | [✅2026/08/27 10:59] |
| 56 | 半角強制変換と領域長切り捨ての実装 | domain | `domain/value_objects/asp_import.py` | [✅2026/08/27 11:07] |
| 57 | 半角変換・切り捨てのテスト追加（TC-086〜104・19 件） | test | `tests/test_asp_import.py` | [✅2026/08/27 11:07] |
| 58 | 機能仕様書の改訂（版 2.72） | docs | `docs/資産棚卸結果_機能仕様書.md` | [✅2026/08/27 11:11] |
| 59 | 本タスクリストへの記録（53〜58） | docs | `docs/spec/02_asp-import-data/tasks.md` | [✅2026/08/27 11:13] |
| 60 | 要件定義書の改訂（D-15・半角変換は警告に出さない） | docs | `docs/spec/02_asp-import-data/requirements.md` | [✅2026/08/27 14:34] |
| 61 | 設計書の改訂（DD-11・警告種別から `HALF_WIDTH_CONVERTED` を削除） | docs | `docs/spec/02_asp-import-data/design.md` | [✅2026/08/27 14:38] |
| 62 | テスト設計書の改訂（TC-032・101・103・104） | docs | `docs/spec/02_asp-import-data/test-design.md` | [✅2026/08/27 14:40] |
| 63 | 半角変換の警告を削除 | domain | `domain/value_objects/asp_import.py` | [✅2026/08/27 14:39] |
| 64 | テストの改修（TC-032・101・103・104） | tests | `tests/test_asp_import.py` | [✅2026/08/27 14:40] |
| 65 | メッセージ表示エリアの高さを行数分にする | interfaces | `static/css/app.css` | [✅2026/08/27 14:40] |
| 66 | 機能仕様書への反映（版 2.73） | docs | `docs/資産棚卸結果_機能仕様書.md` | [✅2026/08/27 14:41] |
| 67 | 本タスクリストへの記録（60〜66） | docs | `docs/spec/02_asp-import-data/tasks.md` | [✅2026/08/27 14:42] |

> **完了時刻の記録について**: タスク31〜40 は本追記より前に完了しており、
> 各時点の時刻を記録していなかった。推測で書かず「17:06 記録」と
> **記録した時刻**であることを明示する。タスク41 以降は完了時点の時刻。

### 順序についての補足

- **タスク22 が domain なのに use_cases の後ろにあるのは意図的**。旧モジュール関数は
  `use_cases/export_asp_import.py` が最後の利用者であり、タスク21 で参照が消えるまで削除できない。
  TDD の Red → Green → **Refactor** の Refactor に当たる位置づけとして、あえて後段に置く。
- **一時的にテストが失敗する区間はタスク21〜25**。ユースケースの引数変更が
  `wiring.py` → `views.py` に波及するため、この 5 タスクは連続して実施する。
- **タスク1〜20・22 は各タスク完了時点で `make test-fast` が緑**であること（domain と use_cases は DB 不要）。
- **テスト実行コマンドの読み替え（重要）**: 本リポジトリに **Makefile は存在しない**。
  以下の各タスクの完了条件に書いた `make` コマンドは、次のとおり読み替えて実行する。

  | tasks.md の表記 | 実際に実行するコマンド |
  |------|------|
  | `make test-fast` | `python -m pytest application/asset_inventory/tests/test_asp_import.py -q`（対象ファイル単位） |
  | `make test-all` | `python -m pytest application/asset_inventory config/tests/test_clean_architecture.py -q` |
  | `make test-cov` | `python -m pytest application/asset_inventory -q --cov=application.asset_inventory --cov-report=term-missing` |
- 新しい VO を追加していく間、旧モジュール関数は**残したまま**にする（タスク22 でまとめて削除する）。
  そのため、タスク2〜14 の途中でも既存テストは常に緑を保てる。

---

## タスク詳細

### タスク1: `NormalizedValue` と整形のテスト作成

- 対象ファイル: `application/asset_inventory/tests/test_asp_import.py`
- 内容:
  - TC-AIV-ASP-050〜059 を追加する（摘要の CRLF / LF / CR を半角空白 1 つへ置換すること、
    `newline_replaced` の真偽、連続 CRLF が空白 2 つになり二重置換されないこと、
    資産枝番の 4 桁ゼロ埋め、空欄の据え置き、数字以外の据え置き、前後空白の除去）
  - テストデータ `VALUE_SUMMARY_CRLF` / `_LF` / `_CR` / `_CRLF2`、`VALUE_BRANCH_1` / `_EMPTY` / `_ALNUM`
    を用意する（test-design.md §3.1・§3.2）
- 完了条件: 追加した 10 件がすべて **Red**（`NormalizedValue` 未実装のため失敗する）ことを確認できる

### タスク2: `NormalizedValue` と整形の実装

- 対象ファイル: `application/asset_inventory/domain/value_objects/asp_import.py`
- 内容:
  - `NormalizedValue(value: str, newline_replaced: bool)` を凍結データクラスとして追加する
  - 摘要の整形: 前後空白を除去し、**CRLF → LF → CR の順**で半角空白 1 つに置換する
    （順序を誤ると CRLF が空白 2 つになるため、順序を守る。D-08）
  - 資産枝番の整形: 前後空白を除去し、**数字のみの場合に限り** 4 桁ゼロ埋めする。
    空欄はそのまま、数字以外・5 桁以上もそのまま返す
  - 既存の `format_branch_number()` は**この時点では残す**（タスク22 で削除する）
- 完了条件: `make test-fast` が緑（タスク1の 10 件が **Green**、既存テストも緑のまま）

### タスク3: `AspFieldCheck` のテスト作成

- 対象ファイル: `application/asset_inventory/tests/test_asp_import.py`
- 内容:
  - TC-AIV-ASP-037〜043 を追加する（資産枝番が空欄なら `O` 違反、摘要 64 byte 可 / 65 byte 違反、
    管理部門コード 12 byte 可 / 13 byte 違反、型番 24 byte 可 / 25 byte 違反、資産番号 13 byte 違反、
    cp932 で表現できない文字を含んでも例外を出さないこと、複数違反ですべての理由を返すこと）
  - 既存の TC-AIV-ASP-030〜034 は現時点ではモジュール関数呼び出しのまま残す（書き換えはタスク15）
- 完了条件: 追加した 7 件がすべて **Red** であることを確認できる

### タスク4: `AspFieldCheck` と `ASP_FIELD_CHECKS` の実装

- 対象ファイル: `application/asset_inventory/domain/value_objects/asp_import.py`
- 内容:
  - `AspFieldCheck(label: str, checks: frozenset[str], max_bytes: int)` と
    `violations(value) -> tuple[str, ...]` を追加する
  - チェック仕様 `O`（必須入力）/ `M`（半角英数記号）/ `I`（整数）/ `N`（数値）/ `D`（日付）/ `P`（全角可）を判定する
  - 領域長は **cp932 換算のバイト数**で判定する。cp932 で表現できない文字を含む場合は例外にせず、
    UTF-8 換算で安全側に評価する
  - 列番号をキーとする `ASP_FIELD_CHECKS: dict[int, AspFieldCheck]` を定義する
    （1 資産番号 `O,M` 12 / 2 資産枝番 `O,I` 4 / 3 管理部門コード `M` 12 / 16 型番 `M` 24 / 38 摘要 `P` 64）
  - 既存の `check_violations()` は**この時点では残す**（タスク22 で削除する）
- 完了条件: `make test-fast` が緑（タスク3の 7 件が **Green**）

### タスク5: `DepartmentCode` のテスト作成

- 対象ファイル: `application/asset_inventory/tests/test_asp_import.py`
- 内容: TC-AIV-ASP-070〜072 を追加する（棚卸データの拠点コードから前後空白を除いて生成すること、
  12 byte 超過を違反として報告すること、空欄でも例外にならないこと）
- 完了条件: 追加した 3 件がすべて **Red** であることを確認できる

### タスク6: `DepartmentCode` の実装

- 対象ファイル: `application/asset_inventory/domain/value_objects/asp_import.py`
- 内容: `DepartmentCode`（V-311）を凍結データクラスとして追加し、
  領域長・チェック仕様の判定は `ASP_FIELD_CHECKS[3]` に委譲する（判定ロジックを二重に持たない）
- 完了条件: `make test-fast` が緑（タスク5の 3 件が **Green**）

### タスク7: `AspImportWarning` / `AspImportWarnings` のテスト作成

- 対象ファイル: `application/asset_inventory/tests/test_asp_import.py`
- 内容:
  - TC-AIV-ASP-060〜066 を追加する（`of_kind()` の絞り込み、`asset_labels()` の重複除去、
    資産番号の列挙が 10 件上限で超過分が「ほか N 件」になること、チェック仕様違反と改行置換の 2 文が
    改行で連結されること、警告が無ければ空文字になること、拠点マスタ縮退の警告が出力全体で 1 件であること、
    `UNAVAILABLE_MESSAGE` が定数として定義されていること）
  - 既存の TC-AIV-ASP-035・036 も警告の担当範囲だが、書き換えはタスク15 で行う
- 完了条件: 追加した 7 件がすべて **Red** であることを確認できる

### タスク8: `AspImportWarning` / `AspImportWarnings` の実装

- 対象ファイル: `application/asset_inventory/domain/value_objects/asp_import.py`
- 内容:
  - `AspWarningKind`（`CHECK_VIOLATION` / `NEWLINE_REPLACED` / `SITE_UNAVAILABLE`）を定義する
  - `AspImportWarning(kind, asset_label, detail)` と、ファーストクラスコレクション `AspImportWarnings`
    （`of_kind()` / `asset_labels()` / `message()`）を追加する
  - 資産番号の列挙は 10 件を上限とし、超過分は「ほか N 件」に丸める（既存の `_MAX_LISTED_ASSETS` を再利用する）
  - `UNAVAILABLE_MESSAGE`（棚卸を選び直す旨のメッセージ）を `EMPTY_MESSAGE` の隣に定数として追加する
  - 既存の `build_check_warning_message()` は**この時点では残す**（タスク22 で削除する）
- 完了条件: `make test-fast` が緑（タスク7の 7 件が **Green**）

### タスク9: `AspPasteLayout` / `AspImportRow` のテスト作成

- 対象ファイル: `application/asset_inventory/tests/test_asp_import.py`
- 内容: TC-AIV-ASP-010b・019・019b を追加する（`blank_columns()` が 75 個の空文字を返すこと、
  `asset_label` が `資産番号-資産枝番` になること、資産枝番が空欄なら資産番号のみになること）
- 完了条件: 追加した 3 件がすべて **Red** であることを確認できる

### タスク10: `AspPasteLayout` / `AspImportRow` の実装

- 対象ファイル: `application/asset_inventory/domain/value_objects/asp_import.py`
- 内容:
  - `AspPasteLayout`（V-309）に既存の列定数（`ASP_COLUMN_COUNT` / `COLUMN_*`）を集約し、`blank_columns()` を追加する
  - `AspImportRow(columns: tuple[str, ...], asset_label: str, warnings: AspImportWarnings)` を追加する
  - 列の詰め方は既存の `build_asp_import_columns()` の仕様を維持する
    （1 資産番号・2 資産枝番は常に、3 管理部門コードは拠点名に差異がある行のみ、
    16 型番はシリアルNo. に差異がある行のみ、38 摘要は摘要に差異がある行のみ、残り 70 列は空欄）
  - 整形で得た `NormalizedValue.newline_replaced` と `AspFieldCheck.violations()` から `warnings` を組み立てる
  - 既存の `build_asp_import_columns()` は**この時点では残す**（タスク22 で削除する）
- 完了条件: `make test-fast` が緑（タスク9の 3 件が **Green**）

### タスク11: `AspImportRows` のテスト作成

- 対象ファイル: `application/asset_inventory/tests/test_asp_import.py`
- 内容: TC-AIV-ASP-024〜027 を追加する（ダブルクォートを `""` にエスケープして囲むこと、
  `warnings()` が全行の警告を連結すること、同じスナップショットから 2 回描画しても同一 bytes になること（C-17）、
  拠点マスタ縮退のスナップショットでは管理部門コードが空欄になり `SITE_UNAVAILABLE` が 1 件だけ付くこと）
- 完了条件: 追加した 4 件がすべて **Red** であることを確認できる

### タスク12: `AspImportRows` の実装

- 対象ファイル: `application/asset_inventory/domain/value_objects/asp_import.py`
- 内容:
  - `AspImportRows`（V-306）をファーストクラスコレクションとして追加し、
    `render_csv() -> bytes` と `warnings() -> AspImportWarnings` を持たせる
  - CSV はヘッダーなし・BOM 付き UTF-8・CRLF 区切り。0 件のときは `b""` を返す
  - 生成時に `site_warning` を受け取り、真なら `SITE_UNAVAILABLE` の警告を**出力全体に 1 件だけ**付与する
  - 既存の `render_asp_import_csv()` は**この時点では残す**（タスク22 で削除する）
- 完了条件: `make test-fast` が緑（タスク11の 4 件が **Green**）

### タスク13: `AmendmentRows` のテスト作成

- 対象ファイル: `application/asset_inventory/tests/test_asp_import.py`
- 内容:
  - TC-AIV-ASP-004〜009 を追加する（未棚卸・台帳外を除外すること、差異のない棚卸済み行を除外すること、
    0 件で `is_empty()` が真かつ `count()` が 0 になること、1 件の境界、
    1,000 件でも全件を入力順で保持すること（D-10 上限なし）、`to_import_rows()` の件数が一致すること）
  - テストデータ `ROWS_1000` を用意する（test-design.md §3.1）
- 完了条件: 追加した 6 件がすべて **Red** であることを確認できる

### タスク14: `AmendmentRows` の実装

- 対象ファイル: `application/asset_inventory/domain/value_objects/asp_import.py`
- 内容:
  - `AmendmentRows`（V-307）をファーストクラスコレクションとして追加し、
    `select_from(rows)` / `is_empty()` / `count()` / `to_import_rows(site_warning)` を持たせる
  - 抽出条件は既存の `select_amendment_rows()` を維持する（棚卸済みかつ差異あり。行数の上限は設けない）
  - 既存の `select_amendment_rows()` は**この時点では残す**（タスク22 で削除する）
- 完了条件: `make test-fast` が緑（タスク13の 6 件が **Green**）

### タスク15: 既存テストを新しい VO・コレクションの呼び出しへ書き換え

- 対象ファイル: `application/asset_inventory/tests/test_asp_import.py`
- 内容:
  - 既存の TC-AIV-ASP-001〜003・010〜018・020〜023・030〜036 を、モジュール関数呼び出しから
    `AmendmentRows` / `AspImportRow` / `AspImportRows` / `AspFieldCheck` / `AspImportWarnings` の
    メソッド呼び出しへ書き換える
  - ファイル冒頭の import から `select_amendment_rows` / `build_asp_import_columns` /
    `render_asp_import_csv` / `check_violations` / `build_check_warning_message` / `format_branch_number` を外す
  - **テストの期待値は変えない**（Refactor であり仕様変更ではない）
- 完了条件: `make test-fast` が緑。`tests/test_asp_import.py` 内に旧モジュール関数の参照が `grep` で 0 件

### タスク16: スナップショットの `site_warning` と読み出しのテスト作成

- 対象ファイル: `application/asset_inventory/tests/test_reconcile_cache.py`
- 内容:
  - TC-AIV-DOM-07G〜07K を追加する（`site_warning` を含むセッション往復、
    `site_warning` キーの無い旧形式が偽として読めること（後方互換）、
    `load_amendment_snapshot` が棚卸一致でスナップショットを返すこと・不一致で `None` を返すこと・
    セッションが壊れていても例外を出さず `None` を返すこと）
  - テストデータ `SESSION_NO_SITE_WARNING_KEY` / `SESSION_BROKEN` / `SESSION_OTHER_MANAGEMENT` を用意する
- 完了条件: 追加した 5 件がすべて **Red** であることを確認できる

### タスク17: `site_warning` と `load_amendment_snapshot` の実装

- 対象ファイル: `application/asset_inventory/domain/value_objects/reconcile_cache.py`
- 内容:
  - `ReconcileCache` に `site_warning: bool = False` を追加し、
    `reconcile_cache_to_session_payload()` と `reconcile_cache_from_session_payload()` の両方に含める
  - 読み出しは `payload.get("site_warning") or False` とし、キーの無い旧形式のセッションでも壊れないようにする
  - `load_amendment_snapshot(session, management_id) -> ReconcileCache | None` を追加する
    （`management_id` が一致するときだけ返す。セッションが壊れていても例外を送出せず `None` を返す）
- 完了条件: `make test-fast` が緑（タスク16の 5 件が **Green**、既存の TC-AIV-DOM-07C〜07F も緑）

### タスク18: 縮退結果の保存と不採用のテスト改修

- 対象ファイル: `application/asset_inventory/tests/test_usecase_list_page.py`
- 内容:
  - **改修対象**: `test_TC_AIV_UC_032_site_master_failure_is_not_cached` を
    「縮退結果も `site_warning=True` で保存されるが、`use_snapshot=True` の経路では採用されず再取得される」
    という期待へ書き換える（DD-02）。テスト関数名も内容に合わせて改める
  - TC-AIV-DOM-07L（縮退結果が `site_warning=True` で保存されること）を追加する
  - 既存の TC-AIV-UC-030・031・033 の期待は変えない
- 完了条件: 書き換えた 1 件と追加した 1 件が **Red**、他の既存テストは緑のままであることを確認できる

### タスク19: 縮退結果の保存と不採用の実装

- 対象ファイル: `application/asset_inventory/domain/value_objects/reconcile_data.py`
- 内容:
  - `load_reconciled_data()` の `if session is not None and not site_warning:` を `if session is not None:` に変え、
    `ReconcileCache(..., site_warning=bool(site_warning))` として**常に保存**する
  - `use_snapshot=True` の分岐で、読み出したスナップショットの `site_warning` が真なら**採用せず**再取得する
    （一覧表示・CSV 出力の既存挙動を変えない。design.md §7.2）
  - 「縮退結果はキャッシュしない」旨の既存コメントを DD-02 に沿った説明へ差し替える
- 完了条件: `make test-fast` が緑（タスク18の 2 件が **Green**、TC-AIV-UC-030・031・033 も緑）

### タスク20: `ExportAspImport` のテスト改修・追加

- 対象ファイル: `application/asset_inventory/tests/test_usecase_export_asp_import.py`
- 内容:
  - **削除対象**: `test_TC_AIV_UC_045_safe_on_api_error`（DD-07。`execute_safe` の廃止により発生しえない）
  - **改修**: TC-AIV-UC-040〜044・046・047 を、`ExportAspImport()`（引数なし）・`execute(query, session)`・
    `AspImportResult.status` に合わせて書き換える
  - **追加**: TC-AIV-UC-048〜054（スナップショットが無いとき desknet's を呼ばないこと、棚卸不一致、
    ゲートウェイを渡さずに生成・実行できること（DD-01）、繰り返し実行の冪等性（C-17）、
    `row_count` が出力行数と一致すること、セッションが壊れていても例外にしないこと、摘要の改行置換と警告）
  - desknet's を呼ばないことの検証には `tests/test_usecase_list_page.py` の呼び出し回数カウント用モックを流用する
- 完了条件: 改修・追加した **14 件**が **Red**。ファイル内に `execute_safe` の参照が `grep` で 0 件
  - ※ 当初「15 件」と書いていたが、TC-AIV-UC-045（desknet's API 障害）は DD-01 により経路自体が
    無くなったため設計上削除した。実数は UC-040〜044・046〜054 の **14 件**（タスク30 で訂正）

### タスク21: `ExportAspImport` の実装（`execute_safe` 削除）

- 対象ファイル: `application/asset_inventory/use_cases/export_asp_import.py`
- 内容:
  - **削除対象**（design.md §7.1）: `__init__(list_all)` の引数 / `execute()` の `access_key` 引数 /
    `execute_safe()` 全体 / `ListAllRecordsFn`・`list_management_rows`・`load_reconciled_data`・
    `_select_management_row`・`DesknetAccessKeyMissingError`・`DesknetApiError` の import
  - `AspImportStatus`（`OK` / `EMPTY` / `UNAVAILABLE`）を追加し、`AspImportResult` に `status` を持たせる
  - `execute(query, session) -> AspImportResult`: `load_amendment_snapshot(session, query.management_id)` で
    スナップショットを読み、`None`（棚卸未選択・スナップショット無し・棚卸不一致・セッション破損）なら
    `UNAVAILABLE` と `UNAVAILABLE_MESSAGE` を返す
  - `AmendmentRows.select_from(cache.rows)` が空なら `EMPTY` と `EMPTY_MESSAGE`、
    それ以外は `to_import_rows(cache.site_warning)` から `render_csv()` と `warnings().message()` を返す
  - **業務的な分岐に例外を使わない**（`ValueError` を送出しない。design.md §8.2）
- 完了条件: `make test-fast` が緑（タスク20の **14 件**が **Green**）。
  `grep -n 'execute_safe\|access_key\|list_all' use_cases/export_asp_import.py` が 0 件

### タスク22: 旧モジュール関数 6 件の削除（Refactor）

- 対象ファイル: `application/asset_inventory/domain/value_objects/asp_import.py`
- 内容:
  - **削除対象**（design.md §7.1）: `select_amendment_rows()` / `build_asp_import_columns()` /
    `render_asp_import_csv()` / `check_violations()` / `build_check_warning_message()` / `format_branch_number()`
  - 併せて、使われなくなった内部ヘルパー（`_clean` / `_byte_length` / `_is_half_width` / `_diff_labels`）の
    参照元を確認し、VO 側へ移設済みのものを削除する
  - このタスクの直前（タスク21）で最後の利用者が消えているため、ここで安全に削除できる
- 完了条件: `grep -rn 'select_amendment_rows\|build_asp_import_columns\|render_asp_import_csv\|check_violations\|build_check_warning_message\|format_branch_number' application/asset_inventory`
  が 0 件、かつ `make test-fast` が緑

### タスク23: 組み立てから `_list_all_fn()` の受け渡しを削除

- 対象ファイル: `application/asset_inventory/interfaces/wiring.py`
- 内容: `export_asp_import_usecase()` を `return ExportAspImport()` に変える（DD-01）。
  他のユースケース（`ExportCsv` 等）の組み立ては変更しない
- 完了条件: `interfaces/wiring.py` が import エラーなく読み込め、
  `config/tests/test_clean_architecture.py` が緑

### タスク24: ビュー・画面のテスト改修・追加

- 対象ファイル: `application/asset_inventory/tests/test_asset_inventory_views.py`
- 内容:
  - **削除対象**: `test_TC_AIV_API_015_asp_import_error_returns_502`（DD-01 により 502 の経路が無くなる）
  - **改修**: TC-AIV-API-012（`X-Asp-Import-Status: ok` の検証を追加）、
    TC-AIV-API-013（`empty` 時に本文へ `EMPTY_MESSAGE` が返ることを、スナップショット前提の準備に書き換え）、
    TC-AIV-API-014（警告ヘッダーの URL エンコード。準備をスナップショット前提に書き換え）、
    TC-AIV-API-016（棚卸選択時にボタンが**活性**で描画されること）
  - **維持**: TC-AIV-API-011（未ログインのリダイレクト）は準備の変更のみで期待は変えない
  - **追加**: TC-AIV-API-015b（スナップショットが無いとき `unavailable` を返しダウンロードさせないこと）、
    017（棚卸未選択でもボタンを描画し `disabled` と `title` を付けること）、
    018（一覧がエラー表示のとき非活性であること）、019（`unavailable` 時に desknet's を呼ばないこと）、
    020（総務メニューグループ以外は 403）、021（`X-Asp-Import-Rows` が行数と一致すること）、
    022（ファイル名が `asp_import_{YYYYMMDDhhmmss}.csv` であること）
  - **維持**: TC-AIV-API-023（既存 CSV 出力の回帰）は変更しない
- 完了条件: 改修・追加した 11 件のうち **9 件が Red**
  - ※ TC-AIV-API-016（ボタンを活性で描画）と 020（総務メニューグループ以外は 403）は
    着手時点の実装で既に Green。タスク26 のテンプレート改修後も Green を維持することが検証目的
    （タスク30 で訂正）

### タスク25: `export_asp_import` ビューと活性判定の実装

- 対象ファイル: `application/asset_inventory/interfaces/views.py`
- 内容:
  - **削除対象**: `export_asp_import` ビュー内の `_resolve_access_key(request)` 呼び出しと 503 応答、
    `execute_safe()` の呼び出しと 502 応答（`_resolve_access_key` 自体は他のビューで使うため**残す**）
  - `export_asp_import_usecase().execute(query, session=request.session)` に置き換え、
    `result.status` で `ok` / `empty` / `unavailable` に分岐する（4xx・5xx は認証・認可のみ）
  - `unavailable` は 200 と `X-Asp-Import-Status: unavailable`、本文にメッセージを返す
    （文言は domain の定数を使い、ビューで組み立てない。design.md §8.2）
  - `list_page` のコンテキストに `can_export_asp_import`（突合結果スナップショットが表示されているか）を追加する
- 完了条件: `make test-all` が緑（タスク24の 11 件のうち **9 件が Green**、
  既存の TC-AIV-API-001〜004・007・010 も緑）
  - ※ TC-AIV-API-017・018 はテンプレートの描画に依存するため、**タスク26 完了時に Green** になる
    （タスク30 で訂正）

### タスク26: 作成ボタンの活性・非活性の描画

- 対象ファイル: `templates/asset_inventory/list.html`（`.aiv-results-head-actions` 内、48〜53 行目付近）
- 内容:
  - `取り込み用データの作成` ボタン（`.aiv-asp-import-button`）を `{% if has_list_data %}` ブロックの**外**、
    `{% endif %}` の直後へ移す。**CSV出力リンク（`.aiv-export-csv-link`）はブロック内のまま変更しない**
    （一覧データが無いときに CSV 出力を見せない既存挙動を保つため）
  - 移したボタンに `{% if not can_export_asp_import %}disabled title="棚卸を選ぶと作成できます。"{% endif %}`
    を付与する（D-09。棚卸未選択・一覧エラー時も**ボタン自体は表示**し、非活性にする）
  - `data-asp-import-url` と `.aiv-asp-import-message` の位置は変更しない
- 完了条件: `make test-all` が緑（TC-AIV-API-016・017・018 が **Green**）

### タスク27: 画面スクリプトの `unavailable` 分岐と活性復元

- 対象ファイル: `static/js/asset-inventory-list.js`
- 内容:
  - `initAspImportButton()` に `X-Asp-Import-Status === "unavailable"` の分岐を追加し、
    ダウンロードせず本文を `is-error` で表示する
  - 押下前の `button.disabled` を記憶し、`finally` では**無条件に活性化せず**記憶した状態へ戻す
    （現在の `button.disabled = false;` は非活性のボタンを活性化してしまう。DD-05）
- 完了条件: `make test-all` が緑であること。
  **このファイルには自動テストが無い**ため、振る舞いの確認はタスク28 の手動確認（M-02・M-03・M-04）で行う

### タスク28: 全テストの実行と手動確認

- 対象ファイル: —
- 内容:
  - `make test-all` と `make test-cov` を実行し、結果を記録する
  - 手動確認 M-01（ボタンの表示位置）・M-02（押下中の表示）・M-03（完了後に押下前の活性状態へ戻る）・
    M-04（`unavailable` の表示）を DevContainer 上の画面で確認する
  - 受け入れ確認 M-05・M-06（ASP『資産／異動情報修正入力』への実機貼り付け）は**利用者に依頼**し、結果を待つ
- 完了条件: 自動テストが全件緑であること。M-01〜M-04 の確認結果を「タスク実行レポート」に記録済みであること

### タスク29: 機能仕様書への追記

- 対象ファイル: `application/asset_inventory/docs/資産棚卸結果_機能仕様書.md`
- 内容: ASP 取り込み用データの作成（ボタンの位置・出力仕様・警告・非活性条件）を追記する。
  用語は `application/asset_inventory/docs/ubiquitous_language.md` に準拠する
- 完了条件: 追記内容が design.md §6・§8 と矛盾しないこと（差分をユーザーに提示して確認する）

### タスク30: テスト仕様書への追記

- 対象ファイル: `application/asset_inventory/docs/資産棚卸結果_テスト仕様書.md`
- 内容: 本タスクリストで実装したテストケース（TC-AIV-ASP / UC / API / DOM）を追記し、
  削除した TC-AIV-UC-045・TC-AIV-API-015 を取り除く
- 完了条件: test-design.md §2 のテストケース一覧と件数が一致すること

### タスク31〜35: 仕様書の改訂（D-11・D-13 の反映）

- 対象ファイル: `requirements.md` / `design.md` / `test-design.md` /
  `docs/資産棚卸結果_機能仕様書.md` / `docs/ubiquitous_language.md`
- 内容: 出力列を 5 列 → **9 列**（1・2・3・16・38・44・59・64・65）に改め、
  **D-05 を撤回**して D-11（44・59・65 列目）・D-12（6 列目は常に空欄）・D-13（64 列目）と
  受け入れ基準 C-18〜C-22、設計判断 DD-08（判定は名称・出力はコード）・DD-09（専用 VO を設けない）を追加する
- 完了条件: 5 文書間で列マッピング・確定事項 ID・受け入れ基準が矛盾しないこと

### タスク36〜39: コードへの反映

- 対象ファイル: `domain/repositories/ports.py` / `domain/value_objects/row_display.py` /
  `domain/value_objects/reconcile_cache.py` / `domain/value_objects/asp_import.py`
- 内容: `ReconcileRow` に `manager_code` / `usage_category_code` / `manufacturer_code` を追加し、
  desknet's への要求部品（`ASSET_FIELDS` / `INVENTORY_FIELDS`）・突合結果行への取り込み・
  セッション往復・ASP 4 列の出力とチェック仕様（`M`・12 byte）まで一連で通す
- 完了条件: `make test-all` が緑であること（1 ファイルずつ変更し、その都度実行する）

### タスク40〜44: テストの改修・追加

- 対象ファイル: `tests/test_asp_import.py` / `tests/test_usecase_export_asp_import.py` /
  `tests/test_reconcile_cache.py` / `tests/test_asset_fields.py` / `tests/test_row_display.py`
- 内容: test-design.md の TC-AIV-ASP-015・017（改修）、080〜085・044・045（新規）、
  TC-AIV-UC-040（改修）、TC-AIV-DOM-07M・07N・060〜062（新規）を実装する。
  D-05 を前提にしていた `test_TC_AIV_ASP_015_model_column_ignores_model_name_diff` は**削除**する
- 完了条件: `make test-all` が緑で、9 列すべてが検証対象に含まれること

### タスク45: 本タスクリストへの記録

- 対象ファイル: `docs/spec/02_asp-import-data/tasks.md`
- 内容: 仕様変更分のタスク31〜45 と、タスク実行レポートを追記する
- 完了条件: 実施した 15 ファイルがすべて表に現れること

### タスク53〜55: 仕様書の改訂（値を ASP の書式へ寄せる）

- 対象ファイル: `docs/spec/02_asp-import-data/requirements.md` / `design.md` / `test-design.md`
- 内容: REQ-F-006 に (a) 半角への強制変換（チェック `M` の 7 列）・(b) 領域長超過分の切り捨てを追加し、
  REQ-F-007 に警告種別表と表示順を定める。確定事項 **D-14**・受け入れ基準 **C-23〜C-25** を追加する。
  design.md には **DD-10**（3 段の変換規則・適用列の限定・カナ語保護条件・切り捨て規則）と
  `AdjustedValue` を定義する。test-design.md には TC-AIV-ASP-086〜104 を追加する
- 完了条件: 仕様書が実装より先に確定していること（CLAUDE.md「仕様書が SSOT」）

### タスク56: 半角強制変換と領域長切り捨ての実装

- 対象ファイル: `domain/value_objects/asp_import.py`
- 内容: `AdjustedValue` / `AspFieldCheck.adjusted()` / `AspFieldCheck.truncatable` /
  `_to_half_width()` / `_truncated()` / 警告種別 `VALUE_TRUNCATED`・`HALF_WIDTH_CONVERTED` を追加し、
  `from_reconcile_row()` で**寄せてから検査する**順序に変える。**削除するコードはない（追加のみ）**
- 完了条件: `make test-all` が緑で、実データ 6 件がすべて解消すること

### タスク57: 半角変換・切り捨てのテスト追加

- 対象ファイル: `tests/test_asp_import.py`
- 内容: TC-AIV-ASP-086〜100（`AdjustedValue`）と TC-101〜104（警告種別・変換前後表示・表示順）を実装する
- 完了条件: `make test-all` が緑で、既存テストの改修が 0 件であること

### タスク58: 機能仕様書の改訂（版 2.72）

- 対象ファイル: `docs/資産棚卸結果_機能仕様書.md`
- 内容: §4.1.8 に「値の寄せ（半角変換）」「値の寄せ（切り捨て）」「警告の並び」を追加し、
  チェック警告を明細行方式に書き換える。§7.5 の `X-Asp-Import-Warning` の説明を拡張し、改訂履歴に版 2.72 を追加する
- 完了条件: 仕様書の記述が実装・requirements.md と一致すること

### タスク59: 本タスクリストへの記録

- 対象ファイル: `docs/spec/02_asp-import-data/tasks.md`
- 内容: タスク53〜58 の完了時刻・詳細・実行レポートを追記する
- 完了条件: 実施した 6 ファイルがすべて表に現れること

---

## タスク実行レポート

（各タスク完了時にここへ追記する。`date '+%Y/%m/%d %H:%M'` で取得した実際の時刻を記録すること）

<!-- 記入例
--------------------
### タスクN: {タスク名}（YYYY/MM/DD HH:MM 完了）

- **懸念事項**:
- **改善事項**:
- **設計のGoodポイント**:
- **チーム共有ポイント**:
--------------------
-->

--------------------
### タスク1: `NormalizedValue` と整形のテスト作成（2026/08/26 10:54 完了）

- **懸念事項**:
  - tasks.md の完了条件に書いた `make test-fast` は、本リポジトリに **Makefile が存在せず実行できない**。
    実際の実行コマンドは `python -m pytest application/asset_inventory/tests/test_asp_import.py -q`（`pytest.ini` の
    `testpaths = application config` を利用）。以降のタスクもこのコマンドで検証する。
  - Red の現れ方が「10 件の失敗」ではなく **モジュール収集時の ImportError（1 error）** になった。
    `NormalizedValue` を import 節に加えたため、ファイル全体が収集できない。テストが書かれ実装が無いことは
    示せているが、既存 23 件の緑が Red 区間だけ見えなくなる。タスク2 の Green で解消する。
- **改善事項**:
  - テストデータ名は tasks.md の略記（`VALUE_BRANCH_1` / `_EMPTY` / `_ALNUM`）ではなく、
    **test-design.md §3.2 の正式名**（`VALUE_BRANCH_EMPTY` / `VALUE_BRANCH_ALPHA` / `VALUE_BRANCH_5DIGIT`）に揃えた。
    仕様書が Single Source of Truth であるため、tasks.md 側の略記は追随させる。
  - `NormalizedValue` の生成方法は design.md §4.2(d) に明記が無かったため、整形規則の 3 区分に対応する
    クラスメソッド **`trimmed()` / `branch_number()` / `summary()`** を設計した。TDD なのでテスト側で API を先に確定させている。
- **設計のGoodポイント**:
  - 整形規則を「対象ごとの 3 メソッド」に分けたことで、`資産番号にゼロ埋めが漏れ出す` 種の事故が型で防げる。
    TC-AIV-ASP-059 が「ゼロ埋め・桁合わせをしない」ことを明示的に守っている。
  - `newline_replaced` を戻り値に同梱する DD-03 の設計により、TC-AIV-ASP-050〜053 が
    「整形結果」と「警告の要否」を 1 回の呼び出しで検証できている。
- **チーム共有ポイント**:
  - TC-AIV-ASP-054（連続 CRLF → 空白 2 つ）は、CRLF → LF → CR の**置換順序**を守らないと落ちる回帰テスト。
    順序を入れ替えるリファクタは禁止と考えてよい。
  - 本プロジェクトのテスト実行は `python -m pytest`（Makefile なし）。tasks.md 内の `make test-*` は読み替えること。
--------------------

--------------------
### タスク2: `NormalizedValue` と整形の実装（2026/08/26 10:55 完了）

- **懸念事項**:
  - `NormalizedValue.trimmed()` は 3 種類（資産番号・管理部門コード・シリアルNo.）で共用しているため、
    将来どれか 1 つだけ整形規則が変わると分岐が必要になる。今は規則が同一なので共用のままとする。
  - 既存の `format_branch_number()` を**残したまま**にした（タスク22 でまとめて削除する）。
    それまでゼロ埋めの実装が 2 か所に存在するため、片方だけ直す事故に注意。
- **改善事項**:
  - `branch_number()` の初版に `len(cleaned) < LENGTH_BRANCH_NUMBER` という冗長な条件を書いていたが、
    `zfill()` は桁数が足りている値をそのまま返すため不要。条件を外し、意図をコメントに残した
    （TC-AIV-ASP-058「5 桁は切り詰めない」がこの挙動を守る）。
  - `raw` に `None` が来ても落ちないよう `(raw or "")` で受けている。`ReconcileRow` の各項目は
    desknet's 由来で欠損しうるため、ドメイン側で防いでおく。
- **設計のGoodポイント**:
  - 置換順序（CRLF → LF → CR）を実装コメントで理由つきで固定したので、
    「まとめて `\r?\n` の正規表現にする」ようなリファクタが入りにくい。
  - `newline_replaced` を `replaced != cleaned` の比較で導出しており、置換ロジックと警告フラグが
    ずれることが構造的に起きない。
- **チーム共有ポイント**:
  - Green を確認したコマンドは `python -m pytest application/asset_inventory config/tests/test_clean_architecture.py -q` →
    **261 passed**。既存 23 件 + 新規 10 件を含む資産棚卸結果アプリ全体と、Clean Architecture 検証が緑。
  - `domain/value_objects/asp_import.py` に `dataclasses` を追加したのみで、`import django` は増えていない。
--------------------

--------------------

### タスク3 実行レポート（2026/08/26 10:59）

**懸念事項**

- Red の現れ方がタスク1と同じく「7 件の失敗」ではなく **収集時の ImportError（1 error）** になった。`ASP_FIELD_CHECKS` を import 節に追加したためで、`AspFieldCheck` / `ASP_FIELD_CHECKS` が未実装であることは確認できているが、個々のアサーションが赤であることはタスク4 の Green で初めて検証される。
- TC-AIV-ASP-043 は「2 件以上」というゆるい期待値のままにした（test-design.md §2.1 の期待結果に合わせた）。`M` 違反と `I` 違反の内訳までは固定していないため、実装側の違反理由の粒度が変わってもテストが赤にならない。

**改善事項**

- 「出力する 5 列すべてに `ASP_FIELD_CHECKS` が定義されていること」を確かめるテストを一度書いたが、test-design.md に対応する TC-ID が無いため**削除した**。仕様書が SSOT である以上、テスト側だけで TC-ID を増やさない。列の定義漏れは タスク5 以降の `AspImportRow` 側テストで間接的に検出できる。
- テストデータ名は test-design.md §3.2 の正式名（`VALUE_DEPT_13` / `VALUE_SUMMARY_64` / `VALUE_SUMMARY_65` / `VALUE_SUMMARY_CP932_NG`）に揃え、境界値の「可」側（`VALUE_DEPT_12` / `VALUE_MODEL_24`）も定数として明示した。

**設計のGoodポイント**

- 領域長の境界を「可」と「違反」の 2 点セットで書けているので（039・040）、`<=` と `<` の取り違えが必ず落ちる。
- cp932 非対応文字（TC-AIV-ASP-042）を**例外にせず評価する**という方針がテストとして固定された。ASP は cp932 前提のシステムだが、desknet's 側は UTF-8 で任意の文字が入りうるため、ここで落ちない保証は運用上の価値が大きい。

**チーム共有ポイント**

- テスト実行コマンドは `python -m pytest application/asset_inventory/tests/test_asp_import.py -q`（Makefile は本リポジトリに存在しないため、tasks.md の `make test-fast` は読み替えて運用する）。
- `COLUMN_ASSET_NUMBER` は既に `asp_import.py` に定義済みだったため、import 追加のみで済んだ。新規に必要なのは `AspFieldCheck` と `ASP_FIELD_CHECKS` の 2 つ。

--------------------

--------------------

### タスク4 実行レポート（2026/08/26 11:01）

**懸念事項**

- チェック `N`（数値）・`D`（日付）は、現時点で使う列が 1 つも無いまま実装した（`ASP_FIELD_CHECKS` の 5 列は `O`/`M`/`I`/`P` のみ）。テストで守られていない経路であり、将来 ASP 側の列を増やすときに必ず実挙動を確認する必要がある。`N` は `float()` 判定、`D` は `YYYYMMDD` / `YYYY/MM/DD` / `YYYY-MM-DD` の書式一致のみで、暦日として妥当か（2 月 30 日等）までは見ていない。
- 既存の `check_violations()` を残したままなので、**同じ判定ロジックが 2 か所に存在する状態**になっている。文言はほぼ同じだが完全一致ではない（例: 既存は空欄でも半角判定や領域長判定を通す）。タスク22 で `check_violations()` を削除するまでは、修正時に片側だけ直さないよう注意する。

**改善事項**

- 空欄の扱いを `violations()` の入口で 1 か所に集約した。既存の `check_violations()` は列ごとに `if department_code:` / `if model_number:` と個別に空欄ガードを書いていて、資産番号だけガードが無い（空欄でも半角判定が走る）という不揃いがあった。列ごとの `if` が消えることでこの取りこぼしが構造的に起きなくなる。
- 領域長の判定を `CHECK_FULL_WIDTH`（P）の有無に関わらず**必ず走る**形にした。P は「文字種を問わない」だけであって「領域長を見ない」ではないため。
- チェック記号を `CHECK_REQUIRED` 等の定数にし、`frozenset({"O", "M"})` のような生文字列が `ASP_FIELD_CHECKS` に散らばらないようにした。

**設計のGoodポイント**

- 「どの列に何のチェックが掛かるか」が `ASP_FIELD_CHECKS` の 1 つの表に集約された。従来は `check_violations()` の手続きの中に列ごとの判定が埋まっていて、要件定義書 §9 付録の表と突き合わせるのが難しかった。表と表の対応になったことでレビューが目視でできる。
- `AspFieldCheck` は `ReconcileRow` を知らない純粋な値オブジェクトなので、列の値さえあれば単体で検証できる。タスク3 のテストが `ReconcileRow` を組み立てずに書けたのはこの分離のおかげ。
- cp932 換算のバイト数計算（`_byte_length`）を既存のまま再利用でき、`UnicodeEncodeError` 時に UTF-8 換算へ落とす安全側の評価（TC-AIV-ASP-042）がそのまま引き継がれた。

**チーム共有ポイント**

- `python -m pytest application/asset_inventory/tests/test_asp_import.py -q` → **40 passed**（タスク3 の 7 件が Green）。回帰確認として `python -m pytest application/asset_inventory config/tests/test_clean_architecture.py -q` → **268 passed**。
- `domain/` への追加 import は `re` のみ。Django 非依存は維持されており Clean Architecture 検証も緑。
- **既存の `check_violations()` は未削除**（tasks.md タスク4 の指示どおり）。削除はタスク22 でまとめて行う。

--------------------

--------------------

### タスク5 実行レポート（2026/08/26 11:02）

**懸念事項**

- `DepartmentCode` の生成 API も design.md に明示されていなかったため、テスト側で `DepartmentCode.from_site_code(site_code)` と確定させた（`NormalizedValue` と同じ状況）。design.md §4.2(c) は「値は棚卸データの `site_code` から取り、前後の空白を除く」としか書いていない。**生成元が拠点コードであることを名前に残す**判断だが、タスク6 の実装後に design.md へ追記して同期させるかは タスク29 で機能仕様書を書くときに合わせて判断したい。
- TC-AIV-ASP-071 の期待値を「1 件」と固定した。`ASP_FIELD_CHECKS[3]` は `M` と領域長を見るが、`VALUE_DEPT_13`（半角 13 文字）は領域長違反のみなので 1 件になる。委譲先の違反文言までは固定していない。

**改善事項**

- テストデータは タスク3 で定義済みの `VALUE_DEPT_13` を再利用し、同じ値の定義を増やさないようにした。新規に足したのは `VALUE_SITE_CODE_PADDED = " 001 "` のみ。

**設計のGoodポイント**

- TC-AIV-ASP-072 が「管理部門コードは `O`（必須入力）対象外」を明示的に守る。5 列のうち必須は資産番号と資産枝番だけであり、拠点が取れなかった場合に空欄で貼り付けても ASP 側は「変更なし」として扱う（D-01）という前提がテストとして残る。
- 違反判定を `DepartmentCode` 自身が持たず `ASP_FIELD_CHECKS` へ委譲する設計なので、領域長 12 byte を変えるときに直す場所が 1 か所で済む。

**チーム共有ポイント**

- Red を確認（`ImportError: cannot import name 'DepartmentCode'`）。タスク3 と同様、import 節への追加により収集時エラーの形で赤くなる。
- 次の タスク6 で `DepartmentCode` を実装すれば 43 passed になる見込み。

--------------------

--------------------

### タスク6 実行レポート（2026/08/26 11:02）

**懸念事項**

- `DepartmentCode` は現時点でまだどこからも使われていない（`build_asp_import_columns()` は依然として `_clean(row.site_code)` を直接呼んでいる）。実際に組み込まれるのは タスク11〜12 の `AspImportRow` 実装時であり、それまでは「定義したが使われていない型」が並ぶ状態が続く。
- 5 列のうち独立した型を持つのは管理部門コードだけで、資産番号・資産枝番・型番・摘要は素の `str` のまま扱う。設計どおりだが、型の粒度が不揃いである点はレビューで指摘されうる。

**改善事項**

- `from_site_code()` の実装で `_clean()` ではなく `NormalizedValue.trimmed()` を使った。整形の入口を `NormalizedValue` に一本化しておけば、タスク22 で `_clean()` を整理するときに追随箇所が減る。

**設計のGoodポイント**

- 「値の整形」は `NormalizedValue`、「値の検査」は `AspFieldCheck` へそれぞれ委譲し、`DepartmentCode` 自身は 1 行も判定ロジックを持っていない。VO を足しても知識の重複が増えない形になった。
- `violations()` が引数を取らないため、呼び出し側が誤って別の列の値を渡すことがない。列位置 `COLUMN_DEPARTMENT_CODE` の指定が型の内側に閉じている。

**チーム共有ポイント**

- `python -m pytest application/asset_inventory/tests/test_asp_import.py -q` → **43 passed**（タスク5 の 3 件が Green）。回帰確認 → **271 passed**。
- `domain/` への import 追加なし。Clean Architecture 検証も緑。

--------------------

--------------------

### タスク7 実行レポート（2026/08/26 11:04）

**懸念事項**

- TC-AIV-ASP-065「拠点マスタ縮退の警告は出力全体に 1 件」を、`AspImportWarnings.with_site_unavailable()` という**新しいメソッド**で表現した。design.md §4.2(h) のメソッド一覧には `of_kind()` / `asset_labels()` / `message()` しか無く、「`AspImportRows` の生成時にスナップショットの `site_warning` から付与する」とだけ書かれている。付与の入口を `AspImportWarnings` 側に置いたのは、`AspImportRows`（タスク13）が「1 件だけ足す」判断を持たなくて済むようにするため。design.md との差分になるので タスク29 で仕様書へ反映する候補とする。
- 警告文の文言をテストで**部分一致**（`in`）で検証している。全文一致にすると文言の微修正でテストが割れるためだが、句読点や助詞の崩れは検出できない。全文の最終確認は タスク28 の受け入れ確認（画面表示）で行う。
- `AspImportWarnings` を「タプルを 1 つ受け取る凍結データクラス」として確定させた（`AspImportWarnings(())` が空コレクション）。可変長引数にするか迷ったが、`of_kind()` が同じ型を返す都合上、コレクションを渡す形の方が素直と判断した。

**改善事項**

- テストの前準備に `_check_violation()` / `_newline_replaced()` の 2 つのヘルパーを置き、7 件のテストで `AspImportWarning(...)` の 3 引数を繰り返し書かないようにした。将来 `AspImportWarning` に属性が増えても直すのは 2 か所で済む。
- TC-AIV-ASP-062 は「10 件目が入っていること」だけでなく「**11 件目が入っていないこと**」（`"52610-0001" not in message`）も確認する形にした。上限がずれたときに必ず落ちる。

**設計のGoodポイント**

- 警告を「文字列」ではなく `kind` を持つ値として扱う設計（DD-04）の効果がテストに出ている。`of_kind()` があるおかげで「チェック仕様違反が何件で、改行置換が何件か」を文字列の解析なしに検証できる。従来の `build_check_warning_message()` は文字列しか返さないため、この粒度の検証ができなかった。
- 警告の種別ごとに 1 文を作る構成なので、種別が増えても `message()` の組み立てが線形に伸びるだけで済む。

**チーム共有ポイント**

- Red を確認（import 節に `AspWarningKind` / `AspImportWarning` / `AspImportWarnings` / `UNAVAILABLE_MESSAGE` を追加したため収集時 ImportError）。
- `UNAVAILABLE_MESSAGE` の文言は `"棚卸を選び直してください。"`（test-design.md TC-AIV-ASP-066・design.md §6 の `unavailable` 応答本文と同一）。views 側（タスク24）でもこの定数を使い、文言を二重に書かない。

--------------------

--------------------

### タスク8 実行レポート（2026/08/26 11:05）

**懸念事項**

- design.md §4.2(h) のメソッド一覧に無いものを 3 つ追加した: `AspImportWarning.site_unavailable()`（縮退警告の生成）、`AspImportWarnings.merged()`（連結。タスク13 の `AspImportRows` で行ごとの警告をまとめるために必要）、`AspImportWarnings.with_site_unavailable()`。いずれも設計の意図の範囲内だが、**仕様書に無いメソッドが 3 つ**という事実は タスク29 の仕様書更新時に必ず棚卸しする。
- `message()` の中で `violations._listed_labels()` と、別インスタンスの非公開メソッドを呼んでいる。同一クラス内なので Python 上は問題ないが、読み手には一瞬引っかかる書き方。
- 警告文の文言を `SITE_UNAVAILABLE_MESSAGE` だけ定数に切り出し、他の 2 文は `message()` 内の f-string のままにした。件数と資産番号を埋め込む都合だが、文言の所在が 2 か所に分かれている。

**改善事項**

- 件数を「警告の件数」ではなく **`asset_labels()` の件数（＝資産の件数）** で数えるようにした。1 つの資産に違反が 2 件あっても「1 件あります」と表示される。TC-AIV-ASP-061 の重複除去と表示件数の意味が揃う。
- `with_site_unavailable()` を冪等にした（既に付いていれば増やさない）。呼び出し側が「1 回だけ呼ぶ」ことを守らなくても出力全体で 1 件になる。
- `asset_labels()` は空ラベルを除く。縮退警告は資産に紐づかない（`asset_label=""`）ため、資産番号の列挙に紛れ込まない。

**設計のGoodポイント**

- 警告の生成（誰が何に違反したか）と、警告文の組み立て（どう見せるか）が同じ VO の中で分かれた。従来の `build_check_warning_message()` は `ReconcileRow` のタプルを受け取って違反判定と文言組み立てを一度にやっていたため、文言だけ変えたい場合でも突合の型を持ち出す必要があった。
- `of_kind()` が同じ `AspImportWarnings` を返すため、`len(violations.asset_labels())` のように絞り込んだ結果へそのままメソッドを重ねられる。

**チーム共有ポイント**

- `python -m pytest application/asset_inventory/tests/test_asp_import.py -q` → **50 passed**（タスク7 の 7 件が Green）。回帰確認 → **278 passed**。
- `domain/` への import 追加は `enum` のみ（標準ライブラリ）。Clean Architecture 検証も緑。
- **既存の `build_check_warning_message()` は未削除**。削除は タスク22。

--------------------

--------------------

### タスク9 実行レポート（2026/08/26 11:06）

**懸念事項**

- ここでも生成 API が design.md に無いため、テスト側で `AspImportRow.from_reconcile_row(row)` と確定させた。`NormalizedValue` / `DepartmentCode` に続いて 3 例目であり、**design.md §4 は属性表しか持たず、生成の入口を定めていない**という構造的な欠落が確認できた。タスク29 で仕様書へ反映する際は、VO ごとにばらばらに直すのではなく §4 に「生成方法」列を足す形で一括して埋めたい。
- TC-AIV-ASP-019 の期待値 `5262-0001` は、`asset_label` が**ゼロ埋め後の資産枝番**を使うことを前提にしている（入力は `1`）。design.md §4.2(e) は「`資産番号-資産枝番`」としか書いていないが、既存の `build_check_warning_message()` が `format_branch_number()` を通した値を使っているため、既存の警告表示と揃う方を採った。

**改善事項**

- `AspPasteLayout.blank_columns()` の検証を `set(blanks) == {""}` で書き、75 個すべてが空文字であることを 1 行で確認できるようにした（`all(...)` より失敗時の差分が読みやすい）。
- 既存の `_row()` ヘルパーをそのまま使えたため、テストデータの新規定義はゼロ。

**設計のGoodポイント**

- `asset_label` を `AspImportRow` の属性として持つ設計により、警告（`AspImportWarnings`）が `ReconcileRow` を知らなくてよくなっている。タスク7 のテストが `ReconcileRow` 抜きで書けたのはこのため。
- 「75 列固定」という不変条件が `blank_columns()` という 1 つの入口に集約されるので、列数の取り違えが構造的に起きにくい。

**チーム共有ポイント**

- Red を確認（import 節に `AspPasteLayout` / `AspImportRow` を追加したため収集時 ImportError）。
- タスク10 では `AspPasteLayout` に列定数を集約するが、モジュールレベルの `ASP_COLUMN_COUNT` / `COLUMN_*` も**当面は残す**（既存テスト TC-AIV-ASP-030〜034 やタスク22 までの互換のため）。

--------------------

--------------------

### タスク10 実行レポート（2026/08/26 11:10）

**懸念事項**

- `AspImportRow.from_reconcile_row()` は design.md §4.2(e) に生成 API の記載がなく、テスト（TC-AIV-ASP-019）から確定した。タスク5・9 と同じ構造的な穴で、タスク29 で design.md §4 に「生成方法」列を足して一括で埋めたい。
- 資産番号が空の行のラベルを `(資産番号なし)` とした。仕様に定義が無いため暫定。実運用では突合結果に資産番号なしの行は現れない想定だが、警告文にこの文字列が出る可能性は残る。
- 警告の生成順は `ASP_FIELD_CHECKS` の辞書順（列番号順: 1→2→3→16→38）に依存する。Python 3.7+ の挿入順保証に乗っているだけなので、順序を仕様として要求するテストはまだ無い。

**改善事項**

- 差異判定は既存の `_diff_labels()`（変化点判定 A-301 の結果）を読むだけにし、値の再比較をしていない。二重に判定ロジックを持たない形を維持した。
- `_build_asset_label()` と `_build_row_warnings()` をモジュール private 関数に切り出し、`from_reconcile_row()` を「列を詰める」だけの見通しに保った。
- 摘要は差異がある行だけ `NormalizedValue.summary()` を通し、その戻り値をそのまま改行置換警告の判断に使った。整形と警告判定で二度走査していない（DD-03 の意図どおり）。

**設計のGoodポイント**

- `AspPasteLayout` が列位置と総列数の唯一の置き場になり、`AspImportRow` 側は `AspPasteLayout.ASSET_NUMBER - 1` のような形でしか列に触れない。75 列一覧は要件定義書 §9 付録が正で、コード側には再掲していない。
- チェック仕様違反の検出が `ASP_FIELD_CHECKS` の内包表記 1 つに収まり、列を増やしても `from_reconcile_row()` は変わらない。

**チーム共有ポイント**

- テスト実行は `python -m pytest application/asset_inventory/tests/test_asp_import.py -q`（tasks.md の `make test-fast` は Makefile が無く実行できない）。タスク9 の 3 件が Green になり 53 passed。
- 回帰は `python -m pytest application/asset_inventory config/tests/test_clean_architecture.py -q` で 281 passed。Clean Architecture 検証も緑（domain には標準ライブラリのみ）。
- 旧 `build_asp_import_columns()` / `format_branch_number()` は当面併存する。新規コードは `AspImportRow` 側を使うこと。削除はタスク22。

--------------------

--------------------

### タスク11 実行レポート（2026/08/26 11:11）

**懸念事項**

- TC-AIV-ASP-027 は「拠点マスタ縮退時は 3 列目が空欄」を求めるが、design.md §4.2(g) には `AspImportRows` が管理部門コードを消す旨の記述が無い（§4.2(h) に「`SITE_UNAVAILABLE` は出力全体に 1 件」とあるのみ）。テスト設計書を正として、タスク12 では生成時に 3 列目を空欄化する実装にする。design.md §4.2(g) への追記はタスク29 で扱う。
- 生成 API `AspImportRows.from_rows(rows, site_warning=...)` はテストから確定した。設計書に生成方法が無い問題は タスク5・9・10 と同根。
- 4 件とも Red の見え方はコレクション時の `ImportError`（1 error）で、個別の失敗としては現れない。新しい記号を import ブロックに先に足すためで、これまでの Red と同じ扱い。

**改善事項**

- テスト側に `_import_rows(rows, site_warning=...)` ヘルパーを置き、`AmendmentRows`（タスク13）が入っても呼び出し側の書き換えが 1 か所で済むようにした。
- TC-AIV-ASP-025 は件数だけでなく `asset_labels()` の並び（`("5262", "5263")`）も検証し、行の並び順が保たれることを固定した。

**設計のGoodポイント**

- 冪等性（C-17）の検証が `render_csv() == render_csv()` の 1 行で書ける。時刻や乱数を出力に混ぜない設計になっている裏付けになる。
- 拠点マスタ縮退が「行ごとの警告」ではなく「出力全体の 1 件」として表現されているため、行数に関係なく警告文が 1 文で済む。

**チーム共有ポイント**

- Red 確認コマンド: `python -m pytest application/asset_inventory/tests/test_asp_import.py -q` → `ImportError: cannot import name 'AspImportRows'`。想定どおり。
- 次のタスク12 で `AspImportRows`（`render_csv()` / `warnings()` / `from_rows()`）を実装し、この 4 件を Green にする。

--------------------

--------------------

### タスク12 実行レポート（2026/08/26 11:12）

**懸念事項**

- 拠点マスタ縮退時の 3 列目空欄化を `from_rows()` の中で行うため、`AspImportRows(rows=...)` とコンストラクタを直接呼ぶと空欄化されない。生成は必ず `from_rows()` を通す運用にする（タスク13 の `AmendmentRows.to_import_rows()` からも `from_rows()` を呼ぶ）。
- 縮退時に管理部門コードを消しても、その行の「拠点名に差異がある」という事実は CSV から読み取れなくなる。警告文（`拠点名の変化点は手作業で確認してください。`）だけが手掛かりになる点は仕様どおりだが、利用者への周知が要る。
- BOM を `"﻿"` のリテラルで書いた（既存実装は生の BOM 文字が埋まっていた）。挙動は同じだが、タスク22 で旧関数を消すときに差分が見やすいようこの形にした。

**改善事項**

- `warnings()` は各行の警告を連結したうえで `with_site_unavailable()` を通すだけにし、`SITE_UNAVAILABLE` の重複防止をコレクション側（タスク8 実装済みの冪等メソッド）に任せた。
- `_without_department_code()` は既に空欄の行をそのまま返し、無駄なタプル再構築をしない。

**設計のGoodポイント**

- `render_csv()` が `row.columns` をそのまま書き出すだけになり、列の詰め方（`AspImportRow`）と CSV 表現（`AspImportRows`）の責務が分離した。旧 `render_asp_import_csv()` は内部で `build_asp_import_columns()` を呼んでおり、両者が密結合だった。
- 0 件で `b""` を返す分岐がコレクション側に 1 か所だけある。REQ-F-008（0 件時は出力しない）の判断は `AmendmentRows.is_empty()` 側に持たせるので二重にはならない。

**チーム共有ポイント**

- `python -m pytest application/asset_inventory/tests/test_asp_import.py -q` → 57 passed（タスク11 の 4 件が Green）。
- 回帰 `python -m pytest application/asset_inventory config/tests/test_clean_architecture.py -q` → 285 passed。
- 旧 `render_asp_import_csv()` はタスク22 まで併存。新規コードは `AspImportRows.render_csv()` を使うこと。

--------------------

--------------------

### タスク13 実行レポート（2026/08/26 11:13）

**懸念事項**

- test-design.md の TC-AIV-ASP-004 は「`MatchStatus.ASSET_ONLY` 1 / `INVENTORY_ONLY` 1」とあるが、`RowTone` に対応する値（`ASSET_ONLY` / `INVENTORY_ONLY`）は無く、`NONE` / `MATCH_CLEAN` / `MATCH_DIFF` / `MATCH_FACTORY` の 4 値のみ。未棚卸・台帳外の行は `RowTone.NONE` として組み立てた。抽出条件は `MatchStatus` だけを見るため判定結果に影響はない。
- `ROWS_1000` はモジュール読み込み時に 1,000 件を生成する。現状 0.9 秒程度で収まっているが、今後この規模のデータを増やすならフィクスチャ化を検討する。

**改善事項**

- TC-AIV-ASP-008 は件数だけでなく資産番号の並びを入力順と突き合わせ、「上限なし（D-10）」と「順序保持」を同時に固定した。
- 0 件・1 件の境界（TC-006・007）で `is_empty()` を `is True` / `is False` と同一性で検証し、真偽値以外を返す実装を弾けるようにした。

**設計のGoodポイント**

- `is_empty()` / `count()` をコレクションに持たせたことで、REQ-F-008（0 件時はダウンロードさせない）の判断をユースケース側が `len(tuple)` で書かずに済む。
- `to_import_rows()` が `AspImportRows` を返すため、修正対象行 → 取り込み用データの変換が 1 本の導線になる。

**チーム共有ポイント**

- Red 確認: `python -m pytest application/asset_inventory/tests/test_asp_import.py -q` → `ImportError: cannot import name 'AmendmentRows'`。
- test-design.md TC-AIV-ASP-004 の `RowTone` 表記はタスク30（テスト仕様書への追記）でまとめて実態に合わせる。

--------------------

--------------------

### タスク14 実行レポート（2026/08/26 11:14）

**懸念事項**

- `to_import_rows(site_warning=...)` はキーワード専用引数にした。design.md §4.2(f) の表では `to_import_rows()` に引数の記載が無いため、タスク29 で設計書側に引数を追記する必要がある。
- `AmendmentRows` は `ReconcileRow` をそのまま保持するので、突合結果の巨大なタプルを 2 本持つことになる（元の一覧＋抽出結果）。1,000 件規模では問題にならないが、将来もっと増える場合は生成元を使い捨てにする運用を検討する。

**改善事項**

- 抽出条件（`MatchStatus.MATCHED and has_diff`）を `select_from()` の 1 か所に集約した。旧 `select_amendment_rows()` と同じ条件で、タスク22 の削除後もここだけを見れば済む。
- `is_empty()` は `not self.rows` を返すので必ず `bool`。TC-AIV-ASP-006・007 の `is True` / `is False` 検証を満たす。

**設計のGoodポイント**

- 「抽出（`AmendmentRows`）→ 変換（`AspImportRows`）→ 表現（`render_csv`）」の 3 段が別々の型に分かれ、それぞれ単独でテストできる形になった。
- 拠点マスタ縮退の伝播が `to_import_rows(site_warning=...)` → `AspImportRows.from_rows()` の 1 経路に限定され、ユースケース側が個々の行に手を入れる余地が無い。

**チーム共有ポイント**

- `python -m pytest application/asset_inventory/tests/test_asp_import.py -q` → 63 passed（タスク13 の 6 件が Green）。
- 回帰 `python -m pytest application/asset_inventory config/tests/test_clean_architecture.py -q` → 291 passed。
- これで domain 層の VO・コレクションが揃った。次のタスク15 で既存テストを新 API 呼び出しへ書き換え、タスク22 で旧モジュール関数を削除する。

--------------------

--------------------

### タスク15 実行レポート（2026/08/26 11:16）

**懸念事項**

- 一括置換の途中で `_import_rows((...).render_csv())` と括弧の位置を誤り、TC-AIV-ASP-021 が 1 件 `AttributeError` で落ちた。すぐ直して 63 passed。正規表現での機械置換は、置換後に必ずテストを走らせて確認する。
- 期待値は変更していない（Refactor であり仕様変更ではない）。TC-AIV-ASP-030〜035 が旧 `build_check_warning_message()` と新 `AspImportRows.warnings().message()` で同じ結果になったことは、タスク4・8 で移した検査ロジックが等価である裏付けになる。

**改善事項**

- テスト側に `_columns_of(row)` を置き、`build_asp_import_columns(row)` の呼び出し形をそのまま維持した。差分が「関数名だけ」に収まり、レビューしやすい。
- `_import_rows()` は タスク11 で入れたヘルパーをそのまま流用し、CSV 系・警告系の両方から使えるようにした。

**設計のGoodポイント**

- 旧モジュール関数 6 つへの参照がテストから 0 件になり、タスク22 の削除が「実装側だけを消す」作業になった。テストが先に新 API へ移っているので、削除時に落ちれば本番コードの取りこぼしだと即断できる。

**チーム共有ポイント**

- 完了条件の確認: `grep -n "select_amendment_rows\|build_asp_import_columns\|render_asp_import_csv\|check_violations\|build_check_warning_message\|format_branch_number" application/asset_inventory/tests/test_asp_import.py` → 0 件。
- `python -m pytest application/asset_inventory/tests/test_asp_import.py -q` → 63 passed。回帰 291 passed。

--------------------

--------------------

### タスク16 実行レポート (2026/08/26 11:19)

**懸念事項**

- テスト設計書の TC-AIV-DOM-07K は「`rows` が文字列／キー欠損の dict」を壊れたセッションとして挙げているが、
  実運用では `SESSION_KEY` の値そのものが dict でないケース（文字列・None）も起こりうる。
  テストでは 3 パターン（`rows` が文字列 / `SESSION_KEY` の値が文字列 / `session` が None）を検証している。
  タスク17 の実装はこの 3 パターンすべてで `None` を返す必要がある。
- TC-AIV-DOM-07L（拠点マスタ縮退の突合結果が `site_warning=True` で保存されること）は
  ユースケース側の検証のため、本タスクではなく タスク18（`tests/test_usecase_list_page.py`）で扱う。

**改善事項**

- 既存の TC-AIV-DOM-07C〜07F にはテスト関数の docstring が無い。今回追加した 5 件は
  「〜こと（対応 REQ-ID）。」形式の docstring を付与した。既存分は本 feature の変更対象外のため据え置く。
- スナップショット組み立ての重複を避けるため `_cache()` ヘルパーを追加した。

**設計のGoodポイント**

- `site_warning` を `ReconcileCache` の属性としてセッションに載せることで、
  一覧表示と取り込み用データ作成が同じスナップショットを見る（DD-02）。往復テストで後方互換も担保できる。
- `load_amendment_snapshot(session, management_id)` が棚卸一致の判定まで引き受けるため、
  ユースケース側は「返ってきたか否か」だけを見ればよく、分岐が単純になる。

**チーム共有ポイント**

- Red は 5 件の failure ではなく収集時 ImportError として出る（import 文に新シンボルを先に足すため）。想定どおり。
- 本リポジトリに Makefile は無い。tasks.md の `make test-fast` は
  `python -m pytest application/asset_inventory/tests/test_reconcile_cache.py -q` と読み替える。

--------------------

--------------------

### タスク17 実行レポート (2026/08/26 11:20)

**懸念事項**

- `ReconcileCache.site_warning` を既定値 `False` の末尾フィールドとして追加した。
  既存の `ReconcileCache(...)` 呼び出し（キーワード引数のみ）はすべて無変更で通るが、
  位置引数で組み立てている箇所があると意味がずれる。grep 済みで該当なし。
- `load_amendment_snapshot` の例外握りつぶしは `TypeError` / `ValueError` / `KeyError` /
  `AttributeError` に限定した。想定外の例外まで飲み込むと不具合が隠れるため広げていない。

**改善事項**

- 読み出しは `payload.get("site_warning") or False` を `bool()` で包み、
  文字列など想定外の値が入っていても真偽値に正規化されるようにした。

**設計のGoodポイント**

- `load_amendment_snapshot` が「セッション読み出し」「棚卸の一致判定」「壊れたセッションの吸収」を
  1 つの関数に閉じ込めたため、ユースケース側は `None` かどうかだけを見ればよい（設計 §8.1 #3・#10）。
- `site_warning` キーの無い旧形式セッションが偽として読めるので、
  リリース直後にログイン中の利用者のセッションが壊れない（後方互換）。

**チーム共有ポイント**

- 単体 9 passed（TC-AIV-DOM-07C〜07K）、回帰 296 passed。Clean Architecture 検証も緑。
- domain 層は標準ライブラリのみで完結しており、`import django` は増えていない。

--------------------

--------------------

### タスク18 実行レポート (2026/08/26 11:21)

**懸念事項**

- `ListPage.execute()` は `use_snapshot=False`（一覧表示のたびに再取得）で呼んでいるため、
  「スナップショットを採用しない」挙動を `ListPage` 経由では検証できない。
  そのため TC-AIV-UC-032 では `load_reconciled_data(..., use_snapshot=True)` を直接呼んで検証している。
  実運用でこの経路を通るのは CSV 出力・取り込み用データ作成であり、そちらの検証は タスク20 以降で行う。
- テスト用に `SELECTED_MANAGEMENT`（`ManagementRow`）を新設した。`MANAGEMENT` 辞書と二重定義になるため、
  片方を変更したらもう片方も合わせる必要がある。

**改善事項**

- 旧テスト名 `..._is_not_cached` は DD-02 の決定（縮退結果も保存する）と逆の意味になるため、
  `..._is_saved_but_not_reused_from_snapshot` に改名した。
- TC-AIV-DOM-07L はドメイン VO の ID だが、検証にユースケース実行が必要なため
  `tests/test_usecase_list_page.py` に置いた（テスト設計書の配置と異なる点は タスク30 で追記する）。

**設計のGoodポイント**

- 「保存はする／採用はしない」を分けたことで、取り込み用データ作成が
  一覧に表示されている内容と同じスナップショットを参照できる（DD-02）。
  同時に一覧・CSV 出力の既存挙動（縮退結果を再利用しない）も維持される。

**チーム共有ポイント**

- Red は 2 件の AssertionError として出た（import は既存シンボルのみのため収集は通る）。
- 既存の TC-AIV-UC-030・031・033 は無変更で緑のまま。

--------------------

--------------------

### タスク19 実行レポート (2026/08/26 11:22)

**懸念事項**

- 縮退結果も保存するようになったため、拠点マスタが落ちている間はセッションのスナップショットが
  毎回上書きされる。取り込み用データ作成はそのスナップショットを読むので、
  管理部門コードが空欄の取り込み用データ（＋警告）が出力される。これは DD-02 の意図どおりだが、
  利用者から見ると「拠点マスタ障害中は管理部門コードだけ出ない」挙動になる点を運用へ周知したい。
- `save_reconcile_cache` の呼び出し条件から `not site_warning` を外したため、
  セッションへの書き込み頻度がわずかに増える（拠点マスタ障害時のみ）。

**改善事項**

- 「縮退結果はキャッシュしない」旨の旧コメントを、保存する理由と採用しない理由を分けて書いた
  新コメントへ差し替えた（削除対象を明示: 旧コメント 1 行）。
- 採用判定の条件は `and not cached.site_warning` の追加のみで、既存の棚卸一致判定はそのまま残した。

**設計のGoodポイント**

- 保存側（無条件）と採用側（`site_warning` が偽のときだけ）を分離したことで、
  一覧・CSV 出力の既存挙動を変えずに取り込み用データ作成の要求を満たせた（design.md §7.2）。
- `site_warning` の真偽値化を `bool(site_warning)` で明示し、警告文（空文字 or メッセージ）を
  そのまま真偽値として扱う既存の慣習と齟齬が出ないようにした。

**チーム共有ポイント**

- 単体 16 passed（TC-AIV-UC-030〜033・TC-AIV-DOM-07L を含む）、回帰 297 passed。
- `load_reconciled_data` の戻り値 2 番目（警告文）は従来どおり。呼び出し側の変更は不要。

--------------------

--------------------

### タスク20 実行レポート（2026/08/26 11:27）

**懸念事項**

- tasks.md の完了条件は「改修・追加した **15 件**」だが、test-design.md の TC-AIV-UC-040〜054 は
  045 が削除済みのため実数は **14 件**（改修 7 件 + 新規 7 件）。tasks.md の件数表記の誤りであり、
  テスト側の漏れではない。タスク30 で tasks.md 側を訂正する。
- TC-AIV-UC-048 の「desknet's を呼ばない」検証は、ユースケースがゲートウェイを受け取らない設計（DD-01）に
  なった時点で構造的に保証される。呼び出し回数カウンタでの検証は形式的になるため、コメントで意図を明記した。
  実質的な担保は TC-AIV-UC-050（引数なしで生成・実行できること）が担う。
- テストは `ListPage` を経由してスナップショットを作る。`ListPage` の仕様変更がそのまま
  取り込み用データ作成のテストに波及するため、結合度は高い。ただし「画面が表示した内容と同一である」ことを
  検証する目的にはこの経路が最も忠実であり、意図的に採用した。

**改善事項**

- `_snapshot_session(list_all, **overrides)` / `_with_inventory(inventory)` / `_csv_lines(content)` の
  3 ヘルパーに集約し、各テストが「入力データ → 期待結果」だけを語るようにした。
- 拠点マスタ縮退版のゲートウェイ `_diff_list_all_site_master_down` を、差異ありデータを保ったまま
  395 のみ空で返す形で新設した（既存の `_list_all_site_master_down` は差異なしデータのため TC-046 に使えない）。

**設計のGoodポイント**

- `AspImportStatus`（OK / EMPTY / UNAVAILABLE）で結果を表現する設計により、テストが例外の捕捉ではなく
  戻り値の検証だけで書けるようになった（design.md §8.2「業務的な分岐に例外を使わない」の効果が
  テストコードの単純化として現れている）。
- `execute(query, session)` がセッションのみを入力とするため、TC-AIV-UC-051（冪等性）が
  「同じセッションで 2 回呼ぶ」だけで書ける。外部通信が残っていたら成立しない検証である。

**チーム共有ポイント**

- 本リポジトリに Makefile は無いため、`make test-fast` は `python -m pytest application/asset_inventory/tests/test_usecase_export_asp_import.py -q` と読み替える。
- Red は今回もコレクション時 ImportError（`AspImportStatus` 未定義）として現れた。新 API のシンボルを
  import 行に先に置くと、Red が 1 error に集約されて確認が速い。

--------------------

--------------------

### タスク21 実行レポート（2026/08/26 11:28）

**懸念事項**

- 回帰実行（`python -m pytest application/asset_inventory config/tests/test_clean_architecture.py -q`）は
  **3 failed / 300 passed**。失敗はすべて `tests/test_asset_inventory_views.py` の
  TC-AIV-API-012・013・014 で、`AspImportResult` に `status` が必須になったことによる
  **想定内の Red**（interfaces 層はタスク24・25 で改修する）。ユースケース層・ドメイン層に回帰はない。
- タスク20 のテストで拠点マスタ縮退を「395 が空リストを返す」で再現していたが、実際の縮退判定は
  `DesknetApiError` の送出であり、空リストでは `site_warning` が立たない。TC-AIV-UC-046 が
  Green にならず発覚したため、既存の `_list_all_site_master_down` と同じ「例外を送出する」形へ修正した。
  **テストの前提誤りをテストが検出できた**ケースであり、実装側の修正は不要だった。

**改善事項**

- `execute_safe` と `ValueError` の送出を廃止し、`AspImportStatus`（OK / EMPTY / UNAVAILABLE）へ一本化した。
  呼び出し側（views）は例外捕捉ではなく区分の分岐だけで済むようになる。
- `ListAllRecordsFn` / `list_management_rows` / `load_reconciled_data` / `_select_management_row` /
  `DesknetAccessKeyMissingError` / `DesknetApiError` の import をすべて削除。
  `grep -n 'execute_safe\|access_key\|list_all' use_cases/export_asp_import.py` は **0 件**。

**設計のGoodポイント**

- ユースケースがゲートウェイを持たなくなったことで、「取り込み用データ作成は desknet's を呼ばない」（REQ-NF-003）が
  テストの約束事ではなく**型レベルの保証**になった。将来の改修で誤って API 呼び出しを足すには
  コンストラクタ引数の追加という目立つ変更が要る。
- `AmendmentRows` / `AspImportRows` に振る舞いが載っているため、ユースケース本体は
  「スナップショットを読む → 抽出 → 変換 → 返す」の 4 行で書き切れた。ユースケースが薄いことが
  ドメインモデルの充実度の指標になっている。

**チーム共有ポイント**

- 業務的な分岐（対象なし・棚卸未選択）に例外を使わない方針（design.md §8.2）は、テストの可読性にも効く。
  `pytest.raises` が消え、すべて戻り値のアサーションで書けるようになった。
- 現時点の回帰は interfaces 層の 3 件のみ Red。タスク24・25 完了時点で全件 Green に戻す。

--------------------

--------------------

### タスク22 実行レポート（2026/08/26 11:29）

**削除対象（実行前に確認済み・すべて参照 0 件）**

| 関数 | 置き換え先 |
|------|-----------|
| `select_amendment_rows` | `AmendmentRows.select_from` |
| `format_branch_number` | `NormalizedValue.branch_number` |
| `build_asp_import_columns` | `AspImportRow.from_reconcile_row` |
| `render_asp_import_csv` | `AspImportRows.render_csv` |
| `check_violations` | `AspFieldCheck.violations` / `DepartmentCode.violations` |
| `build_check_warning_message` | `AspImportWarnings.message` |

`_diff_labels` / `_clean` / `_byte_length` / `_is_half_width` は新コード（`AspImportRow` ・`AspFieldCheck`）が
使用中のため残した。`COLUMN_*` / `LENGTH_*` / `DIFF_LABEL_*` 定数も全件が現行コードとテストから参照されている。
モジュールは 616 行 → **497 行**（-119 行）。

**懸念事項**

- 回帰は引き続き **3 failed / 300 passed**。失敗はタスク21 と同じ interfaces 層の 3 件のみで、
  今回の削除による新規の回帰はない。

**改善事項**

- 削除は「モジュール関数 → VO のメソッド」への移設が完了した後にまとめて行った。
  タスク14〜15 で新 API のテストが Green になっていたため、削除の安全性をテストで担保できた。

**設計のGoodポイント**

- 同じ責務がモジュール関数と VO の両方に存在する期間を、TDD のサイクル 3 つ分（新テスト → 新実装 → 旧削除）に
  限定できた。移行期間が短いほど「どちらを使うべきか」の迷いが生まれにくい。

**チーム共有ポイント**

- 削除前に `grep -rn '<関数名>' --include=*.py application/ config/` で参照 0 件を確認する手順を踏んだ。
  CLAUDE.md の「既存コードの削除を伴う変更は、削除対象を明示してから実行する」に対応する実務手順として定着させたい。

--------------------

--------------------

### タスク23 実行レポート（2026/08/26 11:30）

**懸念事項**

- なし。`export_asp_import_usecase()` のみの 1 行変更で、`ExportCsv` など他のユースケースの組み立ては
  従来どおり `_list_all_fn()` を渡している。`config/tests/test_clean_architecture.py` は **69 passed**。

**改善事項**

- 「なぜゲートウェイを渡さないのか」を wiring 側にもコメントで残した（DD-01）。
  組み立てだけを読む人が、引数の抜けを漏れと誤解しないようにするため。

**設計のGoodポイント**

- 依存の有無が `wiring.py` の 1 行に集約されているため、ユースケースの外部依存が減ったことが
  組み立てコードの差分としてそのまま可視化される。DI コンテナを使わない方針の利点が出た箇所。

**チーム共有ポイント**

- `_list_all_fn()` はセッションからアクセスキーを解決する経路を含むため、これを渡さなくなったことは
  「取り込み用データ作成はアクセスキーを必要としない」ことも意味する。タスク25 のビュー実装では
  アクセスキー未設定時のガードを取り込み用データ作成の経路から外してよい。

--------------------

--------------------

### タスク24 実行レポート（2026/08/26 11:39）

**実施内容**: `tests/test_asset_inventory_views.py` を新ユースケース API（`execute(query, session)` / `AspImportResult`）前提へ改修。
`_stub_asp_usecase`（`execute_safe` 版スタブ）を廃止し、`save_reconcile_cache` で**実際の突合結果スナップショット**を
セッションに積む方式へ全面的に切り替えた。`test_TC_AIV_API_015_asp_import_error_returns_502` は DD-01（ユースケースが
desknet's ゲートウェイを持たない＝502 が発生し得ない）により**削除**。TC-AIV-API-015b / 017〜022 を新規追加。

**結果**: `python -m pytest application/asset_inventory/tests/test_asset_inventory_views.py -q` → **9 failed / 9 passed**。
改修・追加した 11 件のうち 9 件が Red（想定どおり）。

**懸念事項**
- test-design.md の 11 件のうち 2 件は**着手時点で既に Green** である。
  - TC-AIV-API-020（総務メニューグループ以外は 403）: `application/portal/interfaces/middleware.py` の
    `AccessApprovalMiddleware` が `/api/asset-inventory/` 配下を既に 403 にしているため、コード変更なしで成立。回帰ガードとして残す。
  - TC-AIV-API-016（突合結果表示中はボタン活性）: 現テンプレートが `{% if has_list_data %}` 内で `disabled` なしに
    描画しているため現状でも通る。タスク26 のテンプレート改修後も Green を維持することが本来の検証目的。
  - よって tasks.md タスク24 の完了条件「11 件が Red」は実態と合わない。**タスク30 で「9 件が Red（016・020 は既存実装で Green）」に訂正する**。
- タスク25 の完了条件「11 件すべて Green」も実態と合わない。017・018 は**タスク26（テンプレート改修）まで Green にならない**。
  こちらもタスク30 で訂正対象とする。
- 非活性時の `title` 文言が文書間で不一致。design.md §6.3 =「棚卸を選択して突合結果を表示してください」／
  tasks.md タスク26 =「棚卸を選ぶと作成できます。」。**仕様書が SSOT** のため design.md 側を採用してテストを書いた。
  tasks.md をタスク30 で design.md に合わせる。

**改善事項**
- スタブを捨てて実スナップショットを使う方式に変えたことで、ビュー層テストが
  「ユースケースの戻り値をそのまま HTTP に写しているか」だけでなく
  「セッション → ドメイン → CSV」の結線まで通す統合テストになった。DD-01 の構造的保証（TC-AIV-API-019 の呼び出し回数 0）も
  スタブでは書けなかった検証である。
- 行の組み立てを `_amendment_row()` / `_matched_row()` / `_save_snapshot()` に切り出し、
  今後の追加テストが 1〜2 行で書けるようにした。

**設計のGoodポイント**
- DD-01（ユースケースが desknet's ゲートウェイを受け取らない）のおかげで、TC-AIV-API-019 が
  「モックの呼び出し回数を数える」テストではなく「そもそも呼びようがない」という**構造による保証**になっている。
- 権限チェックがミドルウェアに集約されているため、新エンドポイントを追加しても認可のテスト（020）が自動的に成立する。

**チーム共有ポイント**
- ビュー層テストで突合結果スナップショットが必要なときは `_save_snapshot(client, rows)` を使う。
  `client.session` は都度新しいオブジェクトを返すため、`save_reconcile_cache` の後に **`session.save()` が必須**。
- 摘要の ASP チェック上限は 64 バイト。全角「あ」×40 = 80 バイトで違反を再現できる（TC-AIV-API-014）。

--------------------

--------------------

### タスク25 実行レポート（2026/08/26 11:40）

**実施内容**（2 ファイル。着手前に一覧を提示済み）
1. `domain/value_objects/reconcile_cache.py`: `has_amendment_snapshot(session, management_id) -> bool` を**追加**（既存関数の変更・削除なし）。
   design.md §6.3 / DD-05 が「活性判定はドメインで行い、画面は真偽値を受け取るだけ」と定めているため、判定をビューに書かずドメインへ置いた。
2. `interfaces/views.py`:
   - `export_asp_import` を新 API へ書き換え。`_resolve_access_key` 呼び出しと **503（アクセスキー未取得）/ 502（desknet's 障害）の分岐を削除**。
     desknet's を一切呼ばない（DD-01）ため、この 2 つの失敗系は構造上発生しない。
   - `AspImportStatus.UNAVAILABLE` を 200 + `X-Asp-Import-Status: unavailable` + 本文 `棚卸を選び直してください。` で返す（C-16）。
   - `list_page` のコンテキストに `can_export_asp_import` を追加（`has_list_data` かつスナップショット一致）。

**結果**: `pytest tests/test_asset_inventory_views.py -q` → **2 failed / 16 passed**。
残る Red は TC-AIV-API-017・018 の 2 件で、いずれも**タスク26（テンプレート改修）で Green になる**。
※ tasks.md タスク25 の完了条件「11 件すべて Green」は誤り。タスク30 で「017・018 はタスク26 完了時に Green」に訂正する。

**懸念事項**
- `_resolve_access_key` は他ビュー（一覧・CSV 出力・添付取得）が使い続けるため残置した。ASP 取り込み用データの作成だけがアクセスキー不要になる。
- ビューは `use_cases.export_asp_import.AspImportStatus` を関数内 import している。`interfaces → use_cases` は許容される依存方向であり
  `test_clean_architecture.py` にも抵触しないが、モジュール先頭 import に寄せるかは実装レビュー（L5）で確認したい。

**改善事項**
- 失敗系の分岐が 2 本消え、ビューが「ステータスを HTTP に写すだけ」になった。分岐は `AspImportStatus` の 3 値に集約されている。

**設計のGoodポイント**
- DD-01 の効果がコード量として現れた。ゲートウェイを渡さない設計にしたことで、ビューから外部 API 障害のハンドリングが丸ごと消えた。
- DD-05 により、活性判定のロジックがドメイン 1 関数（`has_amendment_snapshot`）に閉じ、テンプレート／JS の双方に判定が散らばらない。

**チーム共有ポイント**
- 取り込み用データの作成エンドポイントは **常に 200 を返す**。結果の区別は `X-Asp-Import-Status`（`ok` / `empty` / `unavailable`）で行う。
  ダウンロードが発生するのは `ok` のときだけ。
- 画面側の活性判定はテンプレート変数 `can_export_asp_import` を見る。JS 側で判定してはならない（DD-05）。

--------------------

--------------------

### タスク26 実行レポート（2026/08/26 11:43）

**実施内容**
- `templates/asset_inventory/list.html`: `取り込み用データの作成` ボタンを `{% if has_list_data %}` ブロックの**外**へ移し、常に描画するようにした。
  CSV出力リンクはブロック内のまま変更していない。非活性時は `disabled` と `title="棚卸を選ぶと作成できます。"` を出力する（D-09・DD-05）。
- **仕様書の修正（先に仕様、次にコード）**: design.md §6.3 の `title` 文言
  「棚卸を選択して突合結果を表示してください」を「棚卸を選ぶと作成できます。」へ修正した。
  旧文言は画面表示に用いない用語「突合結果」を含み、**既存仕様 TC-AIV-API-003（画面に「突合結果」を出さない）と衝突**して回帰失敗を起こしたため。
  tasks.md タスク26 の文言が正しく、design.md 側の誤りであった。
- `interfaces/views.py` の追修正: `use_cases` からの直 import（`AspImportStatus`）が
  `config/tests/test_clean_architecture.py::test_views_do_not_import_use_cases_directly` に抵触したため、
  **`result.status.value` をそのままヘッダーへ写す**方式に変更して import を削除した。分岐も `result.content is None` の 1 本に減った。

**結果**
- `pytest tests/test_asset_inventory_views.py -q` → **18 passed**（TC-AIV-API-016・017・018 を含む 11 件すべて Green）
- 回帰: `pytest application/asset_inventory config/tests/test_clean_architecture.py -q` → **309 passed / 0 failed**

**懸念事項**
- 文書間の文言不一致（design.md と tasks.md）が実装時まで発見されなかった。テスト設計レビュー（L4）で
  「画面文言に禁止用語が含まれていないか」を観点に追加したい。
- ボタンが常時描画になったため、棚卸未選択の初期表示でも「取り込み用データの作成」が見える。
  意図どおり（D-09）だが、利用者に紛らわしくないかは手動確認 M-01 で確かめる。

**改善事項**
- ステータスをヘッダーへ写すだけの実装になり、ビューが持つ ASP 固有の知識が「ヘッダー名」だけになった。
  結果区分が増えてもビューを触らずに済む。

**設計のGoodポイント**
- 活性判定をドメイン（`has_amendment_snapshot`）→ ビュー（`can_export_asp_import`）→ テンプレートの一方向に流したことで、
  テンプレートは `{% if not can_export_asp_import %}` の 1 箇所だけで済んでいる。

**チーム共有ポイント**
- 画面文言に **「突合結果」は使わない**（TC-AIV-API-003 が保証）。ユビキタス言語上の概念名であっても画面には出さない。
- `interfaces/views.py` から `use_cases` を直接 import してはならない。ユースケースの結果は
  そのまま画面表現へ写せる形（値・文字列）で返す設計にすること。

--------------------

--------------------

### タスク27 実行レポート（2026/08/26 11:46）

**懸念事項**

- `static/js/asset-inventory-list.js` には自動テストが無く、`unavailable` 分岐と活性復元の振る舞いは
  タスク28 の手動確認（M-02・M-03・M-04）でしか検証できない。回帰時に壊れても気づけない箇所である
- `wasDisabled` はクリック時点の DOM 状態を見ているため、一覧を再描画せずにスナップショットだけが
  失効した場合、ボタンは活性のまま残る。実害は「押すと `unavailable` メッセージが出る」だけで
  設計どおり（C-16）だが、活性表示と実際の可否が一時的にずれる

**改善事項**

- ステータス値の分岐が `"empty"` / `"unavailable"` の文字列リテラル直書きになっている。
  サーバ側は `AspImportStatus` enum を持つため、将来値が増えるなら定数化を検討する
- 応答本文の読み取り（`await response.text()`）が 3 箇所に散っている。分岐ごとの表示 modifier だけを
  変える形に括り出せる

**設計のGoodポイント**

- 状態の判定はサーバ（`X-Asp-Import-Status`）に一本化され、JS は受け取った値で表示を切り替えるだけになった。
  DD-05 の「判定はドメイン側、画面は結果を使うだけ」という方針が HTTP 境界でも一貫している
- `finally` で押下前の状態へ戻すことで、非活性ボタンをスクリプトが勝手に活性化する副作用が消えた。
  テンプレート側の活性判定（`can_export_asp_import`）が唯一の真実であり続ける

**チーム共有ポイント**

- 取り込み用データの作成は **常に HTTP 200** を返し、区別は `X-Asp-Import-Status`（`ok` / `empty` / `unavailable`）で行う。
  `response.ok` の判定はネットワーク・認可レベルの失敗にのみ対応する
- `unavailable` は「棚卸を選び直してください。」（C-16）を `is-error` で表示し、ダウンロードは行わない
- JS の構文確認は `node --check static/js/asset-inventory-list.js` で行える（回帰の pytest では検出できない）

--------------------

--------------------

### タスク28 実行レポート（2026/08/26 11:49）

**自動テストの結果**

| 実行内容 | コマンド（実際に使用したもの） | 結果 |
|---------|------------------------------|------|
| 全テスト | `python -m pytest -q` | **1145 passed**（0 failed） |
| 資産棚卸結果アプリ + アーキテクチャ検証 | `python -m pytest application/asset_inventory config/tests/test_clean_architecture.py -q` | **309 passed** |
| カバレッジ | `python -m pytest application/asset_inventory -q --cov=application.asset_inventory --cov-report=term-missing` | 240 passed / **TOTAL 96%** |

本機能で追加・変更した主なモジュールのカバレッジ:

| モジュール | カバレッジ | 未到達行 |
|-----------|-----------|---------|
| `use_cases/export_asp_import.py` | 100% | — |
| `domain/value_objects/asp_import.py` | 94% | 108, 113, 229, 231, 290-294, 378, 402, 429, 483（防御的分岐） |
| `interfaces/views.py` | 80% | 165-185 ほか（既存の添付取得・アクセスキー解決経路） |

**手動確認 M-01〜M-04 の結果**

ブラウザでの目視確認は行える環境が無いため、同等の検証を自動で行った。実施内容と結果は次のとおり。

| # | 確認項目 | 検証方法 | 結果 |
|---|---------|---------|------|
| M-01 | ボタンの表示位置 | ビュー層テスト `TC-AIV-API-016`（`aiv-results-head-actions` ツールバー内に描画され `disabled` が無い）・`TC-AIV-API-017`（未選択時は `disabled` と `title="棚卸を選ぶと作成できます。"`）・`TC-AIV-API-018`（一覧エラー時も非活性） | ✅ CSV出力ボタンの直後・同一ツールバー内に描画されることを確認 |
| M-02 | 押下中の表示 | `static/js/asset-inventory-list.js` の `initAspImportButton()` を Node.js のスタブ環境（`document`/`fetch`/`URL` を差し替え）で実行 | ✅ 要求中は `button.disabled=true`・メッセージ「取り込み用データを作成しています…」 |
| M-03 | 完了後に押下前の活性状態へ戻る | 同上。活性状態／非活性状態の両方から押下した場合を実行 | ✅ 活性で押下 → 完了後も活性／非活性で押下 → 完了後も非活性（DD-05 の意図どおり、勝手に活性化しない） |
| M-04 | `unavailable` の表示 | 同上。`X-Asp-Import-Status: unavailable` の応答を与えて実行 | ✅ ダウンロードせず、本文「棚卸を選び直してください。」を `is-error` で表示（C-16） |
| 追加 | `empty` / 警告付き `ok` | 同上 | ✅ `empty` はダウンロードせずメッセージのみ、警告付き `ok` はダウンロード後に警告を `is-warning` で表示 |

検証に使ったスタブは一時ファイル（スクラッチパッド）であり、リポジトリには追加していない。
再実行したい場合は `node --check static/js/asset-inventory-list.js` で構文確認、
振る舞いは同様のスタブを書いて `initAspImportButton()` を呼び出せば再現できる。

**利用者への依頼（M-05・M-06）**

- M-05: 作成した CSV を ASP『資産／異動情報修正入力』へ実際に貼り付け、列ズレが無いことを確認する
- M-06: 貼り付け後に ASP 側でエラーとならないこと（摘要 38 列目・シリアルNo. 16 列目・管理部門コード 3 列目）を確認する

**懸念事項**

- M-01 は「ツールバー内に存在すること」までしか自動検証できていない。実際の見た目（折り返し・間隔・
  ボタン幅）は利用者の目視確認が必要
- ブラウザ実機での確認（特に Safari / iPad からの利用）は未実施。`URL.createObjectURL` を使った
  ダウンロードは環境差が出やすい

**設計のGoodポイント**

- 状態を HTTP ヘッダー（`X-Asp-Import-Status`）に集約したことで、JS の振る舞いを DOM スタブだけで
  検証できた。ブラウザ無しでも `empty` / `unavailable` / 警告の 4 経路すべてを確認できている
- ユースケースが desknet's ゲートウェイを持たない（DD-01）ため、全テスト実行でも外部 API のモック漏れによる
  不安定さが一切発生しなかった

**チーム共有ポイント**

- 本リポジトリに **Makefile は存在しない**。tasks.md 中の `make test-all` / `make test-fast` / `make test-cov` は
  読み替えが必要（上表の実コマンドを使用すること）。この点はタスク30 で tasks.md 本文にも反映する
- 全 1145 件が緑。本機能の追加によって既存機能のテストが壊れていないことを確認済み

--------------------

### タスク29: 機能仕様書への追記（2026/08/26 12:15 完了）

差分をユーザーに提示し、承認を得たうえで `docs/資産棚卸結果_機能仕様書.md` を版 2.69 → **2.70** に更新した。

| # | 箇所 | 変更 |
|---|------|------|
| ① | §4.1.2 画面上部 | `取り込み用データの作成` 行を追加（CSV 出力の隣・常に表示・未選択時は非活性） |
| ② | §4.1.8 ボタン | 「棚卸が選択されているときのみ表示する」→ 常に描画し `disabled` + `title="棚卸を選ぶと作成できます。"`（D-09） |
| ③ | §4.1.8 | 摘要の改行置換（C-15・D-08）／拠点マスタ縮退時の 3 列目空欄（DD-02）／作成できないときの案内（C-16）／行数上限なし（D-10・DD-06）／desknet's 非呼出（DD-01）／再現性（C-17）の 6 行を追加 |
| ④ | §7.5 | 「エラー: §7.4 と同一（302 / 403 / 503 / 502）」を訂正。`unavailable` 応答を追記し、302 / 403 以外は常に 200 で `X-Asp-Import-Status` により区別する旨を明記 |
| ⑤ | §1・§10 | 更新日を 2026-08-26 に、改訂履歴に 2.70 を追加 |

**懸念事項**

- §7.5 の「503 / 502」は設計・実装より前に書かれた記述で、**実装と食い違ったまま 1 版分残っていた**。
  仕様が SSOT である以上、設計フェーズで HTTP 契約を変えた時点（DD-07）で機能仕様書も同時に直すべきだった。
- §4.1.8 は requirements.md への参照リンクで詳細を委ねている箇所があり、機能仕様書だけを読む利用者には
  列レイアウト・チェック仕様が見えない。現状は意図的な分担だが、requirements.md が feature フォルダ配下にあるため
  運用フェーズで見失われる懸念がある。

**改善事項**

- 設計フェーズで既存仕様書の該当節を洗い出し、design.md の「§7 既存コードへの変更点」と同様に
  **「既存仕様書への変更点」**を設計時点で列挙しておくと、Phase 5 末尾での差分作りが不要になる。
- HTTP 契約のように複数文書（機能仕様書・design.md・test-design.md）に散る取り決めは、
  1 箇所（design.md）を正としてほかは参照にする方が食い違いにくい。

**設計のGoodポイント**

- 状態を `X-Asp-Import-Status` の 3 値（`ok` / `empty` / `unavailable`）に集約したため、
  仕様書の記述が「常に 200 + ヘッダーで区別」の 2 行で済み、HTTP ステータスの分岐表が不要になった。
- 非活性の判定をドメイン（`has_amendment_snapshot`）に置いたことで、仕様書側も
  「スナップショットのある棚卸を選ぶと活性化する」という業務語で書ける。

**チーム共有ポイント**

- **機能仕様書 §7.5 は 503 / 502 を返さない**。障害・失効はすべて 200 + `X-Asp-Import-Status: unavailable` で表現する。
  画面側は本文をそのまま表示する契約になっているため、メッセージ文言の変更はサーバ側のドメイン定数だけで完結する。
- 取り込み用データの作成ボタンは**常に表示**される。棚卸未選択時に「ボタンが消えない」のは仕様（D-09）である。

--------------------

--------------------

### タスク30: テスト仕様書への追記（2026/08/26 12:21 完了）

**変更内容（`docs/資産棚卸結果_テスト仕様書.md` 版 2.38 → 2.39）**

| # | 節 | 変更 |
|---|----|------|
| ① | §7.7a | 実装済み 63 件に全面差し替え。VO 単位の小見出し（抽出 001〜009／列生成 010〜019b／CSV 020〜027／チェック 030〜043／正規化 050〜059／警告集約 060〜066／管理部門コード 070〜072）で再編 |
| ② | §7.9 | **TC-AIV-UC-045（desknet's API 障害）を削除**し削除理由を注記。UC-048〜054 を追加。UC-044 の期待結果を `棚卸を選び直してください。` に訂正 |
| ③ | §7.6b | TC-AIV-DOM-07I〜07K を追加。07L は `test_usecase_list_page.py` にある旨を注記 |
| ④ | §7.10 | **TC-AIV-API-015（502）を削除**し削除理由を注記。API-015b・017〜022 を追加。API-016 の説明を「突合結果表示中はボタンを**活性**で描画」に訂正 |
| ⑤ | §8 | TC レンジを実装に一致させ、`test_reconcile_cache.py`（DOM-07A〜07K）の行を新設 |
| ⑥ | §9 | 版 2.39（2026-08-26）を追加 |

**あわせて tasks.md 本文を訂正**

| # | 箇所 | 訂正 |
|---|------|------|
| (a) | タスク24 完了条件 | 「11 件が Red」→「11 件のうち **9 件が Red**」（016・020 は着手時点で既に Green） |
| (b) | タスク25 完了条件 | 「11 件すべて Green」→「9 件が Green。017・018 は**タスク26 完了時**に Green」 |
| (c) | タスク26 の title 文言 | design.md 側を修正して統一済み（対応不要） |
| (d) | タスク20 完了条件 | 「15 件」→「**14 件**」（UC-045 は設計上削除） |
| (e) | §7.7a・§7.6b | 各 VO の生成 API・警告 API・縮退時 3 列目空欄・TC-AIV-DOM-07L の配置を反映 |
| (f) | 順序についての補足 | **Makefile 不在**のため `make test-fast` / `test-all` / `test-cov` の pytest 読み替え表を追加 |

**件数の突合（test-design.md §2 の 100 TC）**

| 区分 | 件数 |
|------|------|
| 実装済み | 97（ASP 63 + UC 14 + API 18 + DOM 07I〜07L 相当を含む） |
| 設計上削除 | 2（TC-AIV-UC-045 / TC-AIV-API-015） |
| 既存回帰でカバー | 1（TC-AIV-API-023 は既存 TC-AIV-API-004 が担保） |
| **合計** | **100** |

**最終確認**: `python -m pytest application/asset_inventory config/tests/test_clean_architecture.py -q` → **309 passed**

**懸念事項**

- テスト仕様書の TC 一覧は**手作業で実装と同期している**。テスト関数名から TC-ID を機械抽出する仕組みが無いため、今後テストを追加・削除すると再び乖離する。今回も §7.7a が 26 件のまま実装 63 件と大きく開いていた。
- 「設計上削除した TC」を仕様書から消すだけだと、後から見た人が「なぜ番号が飛んでいるのか」を追えない。今回は削除理由の注記を残したが、この運用ルールは test-design.md 側には書かれていない。
- TC-AIV-DOM-07L だけ `test_reconcile_cache.py` ではなく `test_usecase_list_page.py` にある。スナップショットへの `site_warning` 保存はユースケースの責務なので配置自体は妥当だが、節（§7.6b）と実装ファイルが 1 対 1 でなくなっている。

**改善事項**

- TC-ID をテスト関数名の規約（`test_TC_AIV_{層}_{番号}_...`）から抽出して仕様書と突き合わせる小さなスクリプトを用意すれば、この同期作業は自動化できる。次に同種の機能を作るときの候補。
- tasks.md の完了条件に件数を書くと、設計変更で TC が増減したときに必ず陳腐化する。件数ではなく「test-design.md の該当 TC がすべて Red」のように**参照で書く**ほうが保守しやすい。
- `make test-fast` 等の存在しないコマンドを完了条件に書いてしまった。タスク分解時に**実行コマンドの存在確認**を 1 度行うだけで防げた。

**設計のGoodポイント**

- HTTP 契約を 3 値ステータス（`ok` / `empty` / `unavailable`）に集約したことで、テスト仕様書側も「502 の異常系」を持たずに済み、TC が素直に減った。契約の単純化がテストの単純化に直結した好例。
- 活性判定を domain の `has_amendment_snapshot()` に置いた（DD-05）ため、ボタンの活性・非活性が `test_reconcile_cache.py` のドメインテストと `test_asset_inventory_views.py` の結合テストの両方から検証できている。
- 警告を `AspImportWarnings` に集約した設計により、「10 件上限」「拠点マスタ縮退は全体で 1 件」といった仕様が VO 単体テスト（ASP-062・065）で閉じて検証できた。

**チーム共有ポイント**

- **テスト仕様書 §7.7a・§7.9・§7.10 は版 2.39 で実装と一致させた**。以後テストを追加したら、同じ版で仕様書も更新すること。
- **TC-AIV-UC-045 と TC-AIV-API-015 は「不合格」ではなく「設計変更により削除」**。取り込み用データの作成は desknet's を呼ばないため（DD-01）、API 障害の経路が存在しない。
- **本リポジトリに Makefile は無い**。テストは `python -m pytest application/asset_inventory config/tests/test_clean_architecture.py -q` で実行する。tasks.md の補足に読み替え表を追加した。
- 残作業は **M-05・M-06（ASP「資産／異動情報修正入力」への実機貼り付け確認）** と **L4 Codex クロスレビュー**（Codex CLI 未導入のため保留）。

--------------------

--------------------

### タスク31〜45: ASP 取り込み用 CSV の 9 列化（2026/08/26 17:10 完了）

**実施内容**: 仕様書 5 / コード 4 / テスト 5 / タスク管理 1 の計 15 ファイルを、
仕様書 → コード → テスト → タスク管理の順に 1 ファイルずつ変更した。
最終確認は `python -m pytest application/asset_inventory config/tests/test_clean_architecture.py -q`
→ **322 passed**（変更前 309 passed）。

#### 懸念事項

- **M-05・M-06（ASP 実機への貼り付け確認＝C-11）の再実施が必要**。
  出力列が **5 列 → 9 列**に増えたため、以前の確認結果は無効になっている。
  『資産／異動情報修正入力』に実際に貼り付け、44・59・64・65 列目が
  意図した項目に入ることを利用者に確認いただく必要がある。
- **64 列目（抽出コード１８）の対応は利用者の口頭指示のみが根拠**。
  貼り付けレイアウトの画像には 64 列目の記載がなく、
  「メーカーコードを旧資産番号の前（抽出コード１８）に追加」という指示に基づく。
  M-06 の実機確認で裏取りするまでは仮の確定とみなす。
- **6 列目「取得日付」は空欄据え置き（D-12）**。ASP 側に列はあるが、
  棚卸で取得日付を変更する運用が無いため出力しない。運用が変わった場合は要改訂。
- **追加 4 コードのチェック仕様は `M`（半角英数記号）・12 byte の推定値**。
  ASP の正式なチェック仕様書に 44・59・64・65 列目の記載が無く、
  同種の抽出コード列から類推した。実機確認で桁あふれが出た場合は要調整。

#### 改善事項

- **test-design.md §2.1 にテストケース行が欠けていた穴を発見・補正した**。
  §1.1 のスコープには「追加コード部品の取得・保持・セッション往復」と書いてあるのに、
  §2.1 に対応する TC 行が無く、Phase 5 で何を書けばよいか特定できない状態だった。
  仕様書 SSOT の原則に従い、テストを書く前に
  TC-AIV-DOM-07M・07N・060〜062 を追記（2026/08/26 17:02）してから実装した。
- **自作した TC-AIV-DOM-062 が実装と矛盾していたため自己修正した**。
  当初「棚卸データの無い行では追加コード 3 件が空になる」と書いたが、
  `row_display.py` では 3 コードとも `source.get()` 由来であり、
  ASSET_ONLY 行では `source` が資産データになるため空にならない。
  「追加コードを持たない記録でも例外にならず空欄になる」へ改訂した。
  なお ASSET_ONLY 行は ASP 出力対象外（棚卸済みかつ変化点ありの行のみ出力）のため実装側に問題はない。
- **`test_usecase_list_page.py` / `test_reconcile.py` / `test_row_detail.py` / `test_field_compare.py`
  へのフィクスチャ追加は見送った**。取得（TC-060）・保持（TC-061/062）・
  往復（TC-07M/07N）がすべて検証済みで、追加は利得が小さく、
  既存の CSV 出力・列表示テストへ波及するリスクの方が大きいと判断した。
  承認済み計画でも「必要な範囲のみ」と定義していた。
- **リポジトリ内で改行コードが混在している**（CRLF: `test_asset_fields.py` /
  `test_row_display.py`、LF: `test_reconcile_cache.py` / `asp_import.py` 等）。
  置換スクリプトが CRLF ファイルで一致 0 件になり失敗した。
  以降は `NL = "\r\n" if "\r\n" in s else "\n"` で改行コードを自動判定する方式に統一した。
  `.gitattributes` で LF に正規化済みだが、既存ファイルは未変換のものが残っている。

#### 設計のGoodポイント

- **「判定は名称、出力はコード」（DD-08）** を明文化したことで、
  画面表示（利用者が見て分かる名称）と ASP 取り込み（システムが解釈するコード）の
  役割分担が一箇所に定義された。44・59・64・65 列目の 4 列すべてがこの原則で説明できる。
- **追加 4 コードに専用 VO を設けなかった（DD-09）**。
  `ASP_FIELD_CHECKS`（`M`・12 byte）と整形関数だけで扱えるため、
  VO を 4 つ増やすより保守対象が少ない。値に業務ルールが付いた時点で VO 化すればよい。
- **`ReconcileRow` への追加が後方互換**。`reconcile_row_from_dict()` は
  `str(payload.get(...) or "")` で復元するため、
  変更前に保存されたセッション（3 キーを持たない）でも例外にならず空文字になる（TC-07N）。
  リリース時にセッションを飛ばす必要がない。
- **1 テスト（TC-AIV-UC-040）で 9 列すべてを検証できる形にした**。
  A1↔I1 を変化点 7 項目すべて差異に拡張しつつ、A2↔I2 は「変化なし」を維持したため、
  既存の UC-041〜054（変化なし行の除外判定など）を壊さずに済んだ。

#### チーム共有ポイント

- **D-05 は撤回された**。「メーカー名は ASP に対応列が存在しないため反映不可」という
  以前の説明は誤りで、現在は 64 列目（抽出コード１８）にメーカーコードを出力する。
  過去の説明を引用する場合は注意すること。
- **確定事項の対応表（最終）**:

  | 列 | ASP項目名 | 出力する値 | 差異判定に使う項目 |
  |----|-----------|-----------|------------------|
  | 1 | 資産番号 | 資産番号 | 常に出力 |
  | 2 | 資産枝番 | 資産枝番（4桁ゼロ埋め） | 常に出力 |
  | 3 | 管理部門コード | 管理部門コード | 管理部門名称（画面の「拠点名」） |
  | 6 | 取得日付 | — | 空欄据え置き（D-12） |
  | 16 | 型番 | 型番 | 画面の「シリアルNo.」 |
  | 38 | 摘要 | 摘要 | 摘要 |
  | 44 | 管理者コード | 管理者コード | 管理者名称（画面の「型番」） |
  | 59 | 抽出コード１３ | 使用区分コード | 使用区分 |
  | 64 | 抽出コード１８ | メーカーコード | メーカー |
  | 65 | 抽出コード１９ | 旧資産番号コード | 旧資産番号 |

  **画面の列名と ASP の列名がねじれている箇所が 2 つある**（画面「型番」→ ASP 44 列目「管理者コード」、
  画面「シリアルNo.」→ ASP 16 列目「型番」）。desknet's 側の項目定義に由来する既存のねじれで、
  今回の変更で持ち込んだものではない。読み替えを誤らないこと。
- **desknet's から追加取得する部品は 3 件**（`管理者コード` / `使用区分コード` / `メーカーコード`）。
  棚卸データ app（408）に存在することは利用者に確認済み。
  資産データ側にも同名の項目があり、`ASSET_FIELDS` / `INVENTORY_FIELDS` の双方に追加した。
- **L4 Codex クロスレビューは未実行**（Codex CLI が本環境に未導入）。
- **本変更はまだ commit していない**。M-05・M-06 の確認結果を待って一括でコミットするか、
  先にコミットして確認結果を追加コミットにするかは利用者の判断に委ねる。

--------------------

--------------------

### タスク46〜52 実行レポート（2026/08/26 17:44）

**対象**: 利用者からの「エラーメッセージをもっとわかりやすく出力して。それからエラーを解析して」
への対応。チェック仕様違反の警告文を、資産番号の列挙から**違反理由ごとの明細行**へ改めた。

**懸念事項**

- 警告文に**該当値そのもの**を載せるようにした（`資産番号「値」`）。全角長音と半角ハイフンの
  ように見た目が近い文字を見分けるには値の提示が不可欠だが、摘要のような自由記述が対象になると
  画面に業務データが長く並ぶ。20 文字で丸める（`_MAX_VALUE_CHARS`）ことで抑えているが、
  丸めた結果として違反箇所が見えなくなる値（21 文字目以降に全角が混じる型番等）は依然ありうる。
- 理由ごとの列挙は 10 件が上限（`_MAX_LISTED_ASSETS`）。超過分は「ほか N 件」に丸めるため、
  棚卸全体で同種の違反が多発したときは画面だけでは全件を追えない。CSV は全件出力されるので
  実害はないが、「画面に出た件数＝直すべき件数」ではないことを運用側に伝える必要がある。
- TC 番号の採番で既存の TC-AIV-ASP-070〜072（管理部門コード）と衝突させかけた。
  テスト設計書の番号は連番の末尾を見るだけでは足りず、**全体を grep して空き番号を確認する**
  手順に改めるべきである。

**改善事項**

- `ASP_FIELD_CHECKS` を dict 内包表記（`{check.position: check for check in (...)}`）に変更した。
  以前は辞書キーと `AspFieldCheck` の列位置を人手で一致させる必要があったが、これで構造的に一致する。
- `.aiv-asp-import-message` に `white-space: pre-line` が無く、複数種別の警告が 1 行に潰れていた。
  `showMessage()` が `textContent` を使う以上 CSS 側の指定が必須であり、今回併せて修正した。
  **既存の不具合**であり、今回の改修で作り込んだものではない。
- 要件定義書 REQ-F-007 のチェック `M` 対象列が 5 列時代のままで、44・59・64・65 が抜けていた。
  9 列化のときに拾いきれていなかった箇所であり、併せて補正した。

**設計の Good ポイント**

- 違反理由の文字列（`AspFieldCheck.violations()` の戻り値）は 9 列化の時点で既に組み立てられており、
  `message()` が捨てていただけだった。**表示層の変更だけで済み、判定ロジックには一切触れていない**。
  判定と表示を分けておいた設計がそのまま効いた形である。
- 明細行の並び順を `(列位置, 検査順)` で固定した。出力のたびに順序が変わると、利用者が前回の
  警告と見比べられなくなるためである。`dict` の挿入順に依存せず明示的にソートしている。
- 値が空の違反（必須入力）では `「」` を付けない。空欄に対して「値を確認してください」と
  値を示しても意味がなく、直すべきことは「入力すること」ひとつだからである。

**チーム共有ポイント**

- **この警告はエラーではない**。REQ-F-007 のとおり、該当行も含めて CSV は全件出力される。
  画面のフィルタは出力範囲に影響しない（REQ-F-002）。
- 実データで検出された 6 件の内訳（利用者が再実行して共有）:

  | 資産番号 | 44 列目（管理者コード）の値 | 違反理由 | 原因 |
  |---------|------------------------|---------|------|
  | 3614-0000 / 3615-0000 / 3616-0000 | `DDGー380C` | 半角英数記号以外 | `ー`（U+30FC 全角長音記号） |
  | 4118-0003 | `ZSー302R` | 半角英数記号以外 | 同上 |
  | 4122-0002 | `GMEーR1500` | 半角英数記号以外 | 同上 |
  | 5096-0002 | `RGSHL4-60-50-L-S` | 12 byte 超過 | 16 byte。文字種は適合 |

  **5 件はすべて同一原因**で、半角ハイフン `-` の代わりに全角長音記号 `ー` が入力されている。
  日本語 IME で `-` を打つと `ー` が確定される典型的な入力ゆれであり、画面上ではほぼ見分けが付かない。
  半角ハイフンに直せば 5 件とも byte 長・文字種の両方に適合する（8〜9 byte）。
- 44 列目は**画面の「型番」列が ASP の「管理者コード」に対応する**ねじれ区間である。
  検出された値がすべて型番の体裁なのは設計どおりで、異常ではない。

--------------------

### タスク53〜59 実行レポート (2026/08/27 11:13)

--------------------

**実施内容**

利用者指示「超過した文字は切り捨てて。変更を反映して」に基づき、
**出力する値を ASP の書式へ寄せてから検査する**方式へ変更した（D-14 / DD-10）。

| 段 | 処理 | 対象列 |
|----|------|--------|
| 1 | NFKC 正規化 | チェック `M` の 7 列（1・3・16・44・59・64・65） |
| 2 | ダッシュ類（U+2010〜2015・U+2212）と引用符（U+2018/2019/201C/201D）の個別置換 | 同上 |
| 3 | 長音記号（U+30FC・U+FF70）→ `-`。**値に かな・カナ・漢字 を含む場合は行わない** | 同上 |
| 4 | 領域長（cp932 byte）超過分の末尾切り捨て | 3・16・38・44・59・64・65（**1・2 を除く**） |

テスト結果: `test_asp_import.py` 単体 **98 passed**、全体 **349 passed**（既存 330 は無改修で全通過）。

**懸念事項**

- **利用者確認外の設計判断が 1 件ある**: 切り捨ての対象から **1 資産番号・2 資産枝番を除外**した。
  この 2 列は ASP 上で更新対象の資産を特定するキーであり、12 byte / 4 byte に切り詰めると
  **別の資産を書き換えてしまう**ためである。この 2 列は超過したまま出力し、チェック警告で知らせる。
  9 列一律に戻す場合は `ASP_FIELD_CHECKS` の `truncatable=False` を外すだけでよい（design.md に明記済み）。
- 長音記号の変換を「かな・カナ・漢字を含まない値のみ」に限定したのは**文脈依存のヒューリスティック**である。
  `ﾓｰﾀｰ100` のような半角カナは NFKC で全角カナになるため保護されるが、
  ローマ字表記のカナ語（例: `MOTAー`）は保護されず `MOTA-` になる。実データに該当は無いが、原理的な限界として残る。
- 切り捨ては**黙って行わない**方針だが、警告は行数が増えるほど長くなる。
  実データ 6 件では問題にならない規模だが、大量件数時の表示は継続課題（行数上限なしの課題と同根）。

**改善事項**

- 寄せ（`adjusted()`）と検査（`violations()`）を**別のメソッドに分けた**。
  `violations()` の意味を変えなかったため、既存テスト 330 件は 1 件も改修せずに済んだ。
- テスト設計書 §2.5 の当初の記述（「TC-032・044・045 を改修扱いにする」）は、
  実装後に**改修不要と判明**したため実態に合わせて訂正した（既存テストは `violations()` を直接呼ぶ）。
  仕様書を先に書いた副作用であり、実装後に仕様書を実態へ戻す運用が機能した例である。
- TC 番号は当初 076〜083 を想定していたが、既存の **TC-AIV-ASP-080〜085 と衝突**したため
  086〜104 に採り直した。採番前に既存の最大番号を grep で確認する手順を定着させたい。

**設計の Good ポイント**

- **寄せてから検査する**という順序を `from_reconcile_row()` の 1 箇所に閉じた。
  出力列の追加・チェック記号の変更があっても、寄せの適用範囲は `ASP_FIELD_CHECKS` の定義だけで決まる。
- `AdjustedValue` が `original` / `value` / `half_width_converted` / `truncated` を持つため、
  「何をどう変えたか」を警告側で**再計算せずに**表示できる。判定と表示の分離（タスク46〜52）と同じ方針が続いている。
- `truncatable` をフィールドとして持たせたことで、「切り捨ててはいけない列」が
  コード上に**理由付きで明示**された。暗黙の例外分岐にせずに済んでいる。

**チーム共有ポイント**

- 実データ 6 件は**全件解消**する。実測値:

  | 元の値 | 寄せた結果 | 変換 | 切り捨て | 残る違反 |
  |--------|-----------|------|---------|---------|
  | `DDGー380C` | `DDG-380C` | ✅ | — | なし |
  | `ZSー302R` | `ZS-302R` | ✅ | — | なし |
  | `GMEーR1500` | `GME-R1500` | ✅ | — | なし |
  | `RGSHL4-60-50-L-S` | `RGSHL4-60-50` | — | ✅ | なし |
  | `モーター100` | `モーター100` | — | — | 半角英数記号以外（**カナ語保護のため意図どおり**） |

- **ASP → desknet's → 棚卸 → ASP 反映 のサイクルは年 1 回**であり、desknet's 側の値が
  寄せ前のまま残ることは**利用者判断で不問**とした（次回 ASP から desknet's へ反映した段階できれいになるため）。
- 寄せは**出力時のみ**で、desknet's・突合結果スナップショットの値は一切変更しない
  （REQ-NF-005 のとおり ASP へも自動書き込みしない）。画面表示も従来どおり元の値のままである。
- **M-05・M-06（＝C-11、ASP『資産／異動情報修正入力』への実機貼り付け確認）は未実施のまま**。
  出力列が 5 → 9 に増え、さらに値の寄せが入ったため、利用者による再確認が必要である。

--------------------

### タスク60〜67: 半角変換の警告抑止とメッセージ表示エリアの高さ調整（2026/08/27）

**契機**: 利用者より「全角文字を半角変換はデフォルトのため、メッセージに出さなくてもよいです」
「メッセージ表示エリアがでかいので縦を行数分だけにして」との指示。

**タスク60**（requirements.md・14:34）: **D-15** を追加（半角変換は既定動作のため警告に出さない）。
REQ-F-007 の警告種別表から「半角に変換した」行を削除し、表示順を **チェック違反 → 切り捨て → 改行置換 →
拠点マスタ縮退** の 4 種別に。REQ-F-006(a) に「警告には出さない」理由を追記。C-23 を修正。変更履歴に 1 行追加。

**タスク61**（design.md・14:38）: **DD-11** を追加（`half_width_converted` は保持するが警告は組み立てない。
判定＝事実の保持 と 通知＝警告の組み立て を分ける）。§4.2(h) から警告種別 `HALF_WIDTH_CONVERTED` を削除し、
`adjusted_value` の対象を `VALUE_TRUNCATED` のみに。警告文の構成から半角変換ブロックを削除。§8.1 #6 を更新。
§10 に D-15 の行を追加。半角変換と切り捨てが重なった場合、切り捨て警告の `value` は**半角変換前の値**とする旨を明記。

**タスク62**（test-design.md・14:40）: TC-101 を反転（警告 0 件・`message()` が空文字）、TC-103 の入力を
`DDGー380C`（半角変換）→ `RGSHL4-60-50-L-S`（切り捨て）に差し替え、TC-104 を 4 種別に。
**TC-032 を改修扱いに変更**し、§2.5 の「既存 TC の改修は無い」という注記を訂正した。

**タスク63**（asp_import.py・14:39）: 列挙子 `HALF_WIDTH_CONVERTED`・`message()` の変換ブロック・
`_build_row_warnings()` の生成ブロックを**削除**。`AdjustedValue.half_width_converted` と `adjusted()` の
3 段変換規則は**残した**（DD-11）。`message()` の docstring にブロック順と D-15 の理由を反映。

**タスク64**（test_asp_import.py・14:40）: TC-101・103・104 を改訂し、**TC-032 を改修**
（`_import_rows(...).warnings().message()` が真であることの検証 → 16 列目が `SN100`・`message()` が空文字）。

**タスク65**（app.css・14:40）: `.aiv-results-card` を `grid-template-rows: auto auto minmax(0, 1fr)` にし、
`.aiv-results-head` / `.aiv-asp-import-message` / `.aiv-results-body`・`.favorite-empty` を
`grid-row: 1 / 2 / 3` で**明示配置**した。

**タスク66**（資産棚卸結果_機能仕様書.md・14:41）: §4.1.8 の「値の寄せ（半角変換）」を「警告は表示しない」に、
「警告の並び」を 4 種別に、§7.5 の `X-Asp-Import-Warning` の付与条件から半角変換を除外。**版 2.73** を追加。

**テスト結果**: `python -m pytest application/asset_inventory/tests/test_asp_import.py -q` → **98 passed**。
`python -m pytest application/asset_inventory config/tests/test_clean_architecture.py -q` → **349 passed in 15.46s**。

--------------------

### タスク60〜67 実行レポート (2026/08/27 14:42)

**懸念事項**

- **TC-032 が既存 TC の唯一の改修点だった**。タスク 55 の時点で「既存 TC の改修は無い」と test-design.md §2.5 に
  書いたが、これは誤りだった。TC-032 は `from_reconcile_row()` 経由で全角値を流し込む唯一の既存 TC であり、
  当時は `HALF_WIDTH_CONVERTED` の警告が出ていたため `message()` が真となり**偶然通っていた**
  （本来検証したかった `CHECK_VIOLATION` はすでに出ていなかった）。半角変換の警告を消した本タスクで初めて失敗し、
  意図の乖離が表面化した。**「message() が真であること」のような緩い表明はテストの意図を守れない**という教訓。
  今回の改修で「16 列目が `SN100`・`message()` が空文字」という具体的な表明に置き換えた。
- **半角変換が完全に見えなくなった**。実データ 5 件（`DDGー380C` 等）は今後、画面上は何も告げずに `DDG-380C` として
  出力される。利用者は「ASP からの往復で毎年きれいになる」前提で受け入れているが、意図しない変換が起きた場合に
  気づく手立てが無い。`AdjustedValue.half_width_converted` は残してあるため、将来「件数だけ出す」等に戻せる。
- **警告文が長い場合の高さ**は依然として内容次第。メッセージ表示エリアは行数分の高さになったが、
  違反が数十件に及ぶと表本体を押し下げる。上限＋スクロールは今回の指示の範囲外のため入れていない。

**改善事項**

- **判定と通知の分離**（DD-11）を明文化できた。「事実を残す」と「利用者に伝える」は別の決定であり、
  片方を変えるときにもう片方を巻き込まない構造になった。今回は列挙子と 2 つのブロックを消すだけで済んだ。
- 仕様書 → 実装 → テストの順（CLAUDE.md「仕様書が SSOT」）を守った結果、コード側の削除範囲が
  設計書の「削除した記述」欄と 1 対 1 で対応し、消し漏れの確認が目視でできた。
- CSS は `grid-row` の**明示配置**にしたことで、`hidden` の有無で行の割り当てが変わる暗黙の依存が消えた。
  今後カード内に要素を足しても、行番号を書かない限り 1fr の行を奪わない。

**設計のGoodポイント**

- `AspWarningKind` が列挙子だったため、警告種別の削除が「列挙子 1 行＋生成箇所 1 つ＋表示箇所 1 つ」に
  収まった。`message()` が種別ごとのブロックを素直に並べる構造だったことも効いている。
- `AdjustedValue` が「寄せたあとの値」と「何をしたか」を同時に返す設計（DD-10）のおかげで、
  通知をやめても判定ロジックには一切手を入れずに済んだ。
- 切り捨て警告の `value` が最初から `value.original`（半角変換前の値）だったため、
  D-15 が求める「利用者が画面で探せる値を出す」がコード変更なしで満たされていた。

**チーム共有ポイント**

- **半角変換は既定動作・無通知**（D-15）。切り捨ては値が消えるため引き続き通知する。この線引きは
  「値の情報が失われるか否か」で引いている。今後の寄せ処理を追加する際も同じ基準で判断すること。
- **警告の並びは 4 種別**: チェック違反 → 切り捨て → 改行置換 → 拠点マスタ縮退。
- テストの表明は「何かが出る」ではなく「何がどう出る」で書くこと（TC-032 の教訓）。
- **M-05・M-06（＝C-11、ASP『資産／異動情報修正入力』への実機貼り付け確認）は未実施のまま**。
- L4 Codex クロスレビューは Codex CLI 未導入のため未実行。git commit も未実施。

--------------------
