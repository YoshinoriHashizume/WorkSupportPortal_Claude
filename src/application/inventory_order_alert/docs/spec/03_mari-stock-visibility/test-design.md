# テスト設計書: MARI 在庫数の併記と一覧・詳細の表示整理

文書ID: TEST-MARI-STOCK-VISIBILITY-2026-001
作成日: 2026/08/31
更新日:
対応文書: ./design.md (DESIGN-MARI-STOCK-VISIBILITY-2026-001), ./requirements.md (REQ-MARI-STOCK-VISIBILITY-2026-001)
テスト戦略reference: test-strategy version 1.1 (updated 2026-04-25)
テストフレームワークreference: django-pytest version 1.0 (updated 2026-04-11)

---

## 1. テスト戦略

### 1.1 テスト対象のスコープ

**テスト対象**:

- 在庫数の 3 状態（値あり／該当なし／未取得）の表現と整形（design.md §4.2）
- MARI 在庫の取得と集計行への付与（§5.3）
- スナップショットの保存・復元における未取得の保持（§5.2）
- 一覧の列構成の変更（§6.1）・CSV の列構成（§6.2）・詳細ダイアログの構成（§6.3）
- クライアント配信ペイロードの増分（§6.4）
- 異常系（§8）

**テスト対象外**:

| 対象 | 理由 |
|---|---|
| Oracle の実接続 | `conftest.py` により既定でモック。実接続の検証はタスク完了後の運用確認で担保する |
| 流動区分の判定ロジック | 本要件で変更しない。既存の `test_flow_quadrant.py` が Green のままであることで担保する（TC-MSV-X-010） |
| 在庫内訳（V-205）・メモの機能 | 本要件で変更しない。既存テストで担保する |
| SLIMS 取込の CSV パース | 変更しない |

### 1.2 テストレイヤーの方針

| レイヤー | テスト種別 | テスト方針 | DB依存 |
|---------|----------|----------|--------|
| Domain | 単体 | 純関数・VO を直接呼ぶ。モックなし | なし |
| Application | 単体 | リポジトリ（Callable ポート）を関数モックに差し替え、**ドメインモデルは実物**を通す | なし |
| Infrastructure | 結合（限定） | `@pytest.mark.django_db`。Oracle はモック、PostgreSQL は実物 | あり |
| Interfaces | 結合（限定） | Django テストクライアント。ユースケースはモック可 | あり |

### 1.3 テスト優先順位

**Domain 層を最優先**とする。在庫数の 3 状態の区別（design.md §9 R-2・R-3）が本機能で最も誤りやすく、
かつ誤ると発注判断を誤らせる箇所であるため。

### 1.4 TDD 方針

CLAUDE.md §2 に従い **TDD（Red → Green → Refactor）** を採用する。

本機能は **追加**が中心であり、02_low-flow-visibility のような「置換」ではない。
したがって**テストスイート全体が長時間 Red になる状況は発生しない**。各タスクで Red → Green を完結させる。

例外は §6.1 の `SORTABLE_COLUMNS` の変更（責任部署の削除）で、この 1 タスクのみ既存テストが一時的に Red になる。

### 1.5 テストケースIDの規約

| 接頭辞 | 層 | 例 |
|---|---|---|
| `TC-MSV-D-nnn` | Domain | 在庫数 VO |
| `TC-MSV-A-nnn` | Application | ListPage / ExportCsv |
| `TC-MSV-I-nnn` | Infrastructure | Oracle 取得・スナップショット |
| `TC-MSV-X-nnn` | Interfaces / 横断 | 画面・CSV・JS・回帰 |
| `TC-MSV-E-nnn` | エッジケース・性能 | 実測系 |

---

## 2. テストケース一覧

### 2.1 Domain層テスト

#### バリューオブジェクト: `stock_quantity`（新規）

テストファイル: `tests/test_stock_quantity.py`（新規）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| TC-MSV-D-001 | `test_format_stock_quantity_returns_number_for_positive_value` | `100` | `"100"` | F-003 | P1 |
| TC-MSV-D-002 | `test_format_stock_quantity_returns_zero_for_zero_value` | `0` | `"0"`（空にしない） | F-003 / F-008 #2 | **P1** |
| TC-MSV-D-003 | `test_format_stock_quantity_returns_empty_for_missing_item` | `""` | `""`（0 にしない） | F-003 / F-008 #1 | **P1** |
| TC-MSV-D-004 | `test_format_stock_quantity_returns_marker_when_not_fetched` | `fetched=False` | `"－"` | F-007 | **P1** |
| TC-MSV-D-005 | `test_format_stock_quantity_returns_negative_value_as_is` | `-5` | `"-5"`（加工しない） | F-008 #3 | P2 |
| TC-MSV-D-006 | `test_format_stock_quantity_adds_thousand_separator` | `12345` | `"12,345"` | F-002 | P2 |
| TC-MSV-D-007 | `test_format_stock_quantity_accepts_decimal` | `10.5` | `"10.5"`（SLIMS はバラ数で小数を許容） | F-003 | P2 |
| TC-MSV-D-008 | `test_is_stock_fetched_returns_false_when_key_absent` | キーなしの行 | `False` | F-007 | **P1** |
| TC-MSV-D-009 | `test_is_stock_fetched_returns_true_when_key_present_and_empty` | `{"mari_stock_qty": ""}` | `True`（該当なしは取得済み） | F-003 / F-007 | **P1** |
| TC-MSV-D-010 | `test_is_stock_fetched_returns_true_when_value_is_zero` | `{"mari_stock_qty": 0}` | `True` | F-007 | P1 |
| TC-MSV-D-011 | `test_three_states_are_mutually_distinguishable` | 値あり / 該当なし / 未取得 | 3 状態の表示がすべて異なる | F-003 / F-007 | **P1** |

> **TC-MSV-D-009 / D-011 が本機能の要**である。「該当なし（キーあり・空）」と「未取得（キーなし）」を
> 取り違えると、再取込すれば直る状態を「在庫が無い」と誤読させる（design.md §9 R-3）。

#### バリューオブジェクト: `table_display`（既存を改修）

テストファイル: `tests/test_table_display.py`（既存を改修）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| TC-MSV-D-012 | `test_sortable_columns_label_slims_stock_quantity` | `SORTABLE_COLUMNS` | `("stock_qty", "在庫数(SLIMS)")` を含む | F-002 | P1 |
| TC-MSV-D-013 | `test_sortable_columns_include_mari_stock_after_slims_stock` | 同上 | `stock_qty` の直後に `("mari_stock_qty", "在庫数(MARI)")` | F-002 | P1 |
| TC-MSV-D-014 | `test_sortable_columns_do_not_include_responsible_department` | 同上 | `responsible_department` を含まない | F-005 | P1 |
| TC-MSV-D-015 | `test_sort_rows_by_mari_stock_quantity_descending` | 3 行 | 降順に並ぶ | F-002 | P2 |
| TC-MSV-D-016 | `test_sort_rows_treats_missing_mari_stock_as_smallest` | 値あり・空・未取得 | 昇順で 空/未取得 が先頭 | F-002 / F-007 | P2 |
| TC-MSV-D-017 | `test_sort_rows_by_mari_stock_keeps_tiebreakers` | 同値 3 行 | 得意先コード・得意先品番で決まる | F-002 | P3 |

#### バリューオブジェクト: `export_csv`（既存を改修）

テストファイル: `tests/test_export_csv.py`（既存を改修）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| TC-MSV-D-018 | `test_export_columns_label_slims_and_mari_stock` | `EXPORT_COLUMNS` | 「在庫数(SLIMS)」「在庫数(MARI)」を含む | F-004 | P1 |
| TC-MSV-D-019 | `test_export_columns_keep_responsible_department` | 同上 | `responsible_department` を**含む**（CSV には残す） | F-004 | **P1** |
| TC-MSV-D-020 | `test_export_csv_writes_empty_for_not_fetched_mari_stock` | 未取得の行 | CSV は **空**（`－` を出さない） | F-004 / F-007 | **P1** |
| TC-MSV-D-021 | `test_export_columns_keep_order_after_confirmation_status` | 同上 | `confirmation_status` 以降が不変 | NF-002 | P2 |

#### バリューオブジェクト: `list_client_data`（既存を改修）

テストファイル: `tests/test_list_client_data.py`（既存を改修）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| TC-MSV-D-022 | `test_payload_row_includes_mari_stock_quantity` | 1 行 | `row["mariStockQty"]` がある | F-002 | P2 |
| TC-MSV-D-023 | `test_payload_display_includes_both_stock_columns` | 1 行 | `display` に `stock_qty` と `mari_stock_qty` | F-002 | P2 |
| TC-MSV-D-024 | `test_payload_display_has_no_responsible_department` | 1 行 | `display` に `responsible_department` を**含まない** | F-005 | P2 |

#### バリューオブジェクト: `row_detail`（既存を改修）

テストファイル: `tests/test_row_detail.py`（既存を改修。無ければ新規）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| TC-MSV-D-025 | `test_row_detail_includes_responsible_department` | 供給リスク品の行 | 責任部署「調達G・営業G・生産管理」 | F-005 / F-006 | P1 |
| TC-MSV-D-026 | `test_row_detail_includes_both_stock_quantities` | 1 行 | SLIMS 在庫数・MARI 在庫数の双方 | F-006 | P1 |
| TC-MSV-D-027 | `test_row_detail_includes_flow_condition_label` | 低流動 3 か月 | 「低流動判定軸・3か月」 | F-006 | P2 |

### 2.2 Application層テスト

リポジトリ（Callable ポート）は関数モックに差し替え、**ドメインモデルは実物**を通す（test-strategy §3.2）。
DB に触れないため `@pytest.mark.django_db` は付けない。

#### ユースケース: `ListPage`

テストファイル: `tests/test_usecase_list_page.py`（既存を改修）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| TC-MSV-A-001 | `test_list_page_passes_through_mari_stock_quantity` | MARI 在庫を持つ行 | 行に `mari_stock_qty` が残る | F-002 | P2 |
| TC-MSV-A-002 | `test_list_page_does_not_query_oracle_for_stock` | 一覧を 2 回開く | Oracle 問い合わせのモックが呼ばれない | F-001 / NF-001 | **P1** |
| TC-MSV-A-003 | `test_list_page_table_headers_have_no_responsible_department` | 既定クエリ | ヘッダに責任部署がない | F-005 | P1 |

#### ユースケース: `ExportCsv`

テストファイル: `tests/test_export_csv.py`（既存を改修）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| TC-MSV-A-004 | `test_export_csv_outputs_both_stock_quantities` | 両在庫を持つ行 | 両方の値が出力される | F-004 | P1 |
| TC-MSV-A-005 | `test_export_csv_keeps_utf8_bom` | 任意 | 先頭が UTF-8 BOM | F-004 / NF-002 | P2 |

### 2.3 Infrastructure層テスト

`@pytest.mark.django_db` を付ける。Oracle は `conftest.py` により既定でモック。

#### Oracle: `summary_queries.fetch_mari_stock_totals`

テストファイル: `tests/test_mari_stock_query.py`（新規）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| TC-MSV-I-001 | `test_fetch_mari_stock_totals_sums_by_internal_item_cd` | 同一品番 2 行 | 合算される | F-001 | P1 |
| TC-MSV-I-002 | `test_fetch_mari_stock_totals_returns_empty_for_unknown_item` | 該当なし | 結果に含まれない（呼び出し側で空になる） | F-008 #1 | P1 |
| TC-MSV-I-003 | `test_fetch_mari_stock_totals_issues_single_query_for_all_items` | 10 品番 | **クエリ発行が 1 回** | NF-001 | **P1** |
| TC-MSV-I-004 | `test_fetch_mari_stock_totals_chunks_over_oracle_in_limit` | 1000 品番 | 既存 `chunked()` で分割。**論理的には 1 回の取得** | NF-001 | P2 |
| TC-MSV-I-005 | `test_fetch_mari_stock_totals_issues_select_only` | 任意 | 発行 SQL が `SELECT` で始まる（INSERT/UPDATE/DELETE を含まない） | NF-003 | **P1** |
| TC-MSV-I-006 | `test_build_summary_rows_attaches_mari_stock_qty` | 集計 | 各行に `mari_stock_qty` が付く | F-001 | P1 |
| TC-MSV-I-007 | `test_build_summary_rows_leaves_mari_stock_empty_when_internal_item_unresolved` | 内作品番なしの行 | 空。他の列は従来どおり | F-008 #4 | P1 |
| TC-MSV-I-008 | `test_build_summary_rows_does_not_change_existing_sql` | 集計 | 既存の集計 SQL が変わっていない | NF-001 | P2 |

#### 永続化: `summary_row_codec` / スナップショット

テストファイル: `tests/test_summary_storage.py`（既存を改修）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| TC-MSV-I-009 | `test_snapshot_roundtrip_keeps_mari_stock_qty` | 保存→読込 | 値が保たれる | F-001 | P1 |
| TC-MSV-I-010 | `test_snapshot_roundtrip_keeps_zero_mari_stock_qty` | `0` を保存→読込 | `0` のまま（空にならない） | F-008 #2 | **P1** |
| TC-MSV-I-011 | `test_legacy_snapshot_row_has_no_mari_stock_key` | MARI 在庫なしの行を読込 | **キーが作られない**（未取得を保つ） | F-007 | **P1** |
| TC-MSV-I-012 | `test_legacy_snapshot_does_not_raise_on_load` | 同上 | 例外を送出しない | F-007 / NF-002 | **P1** |
| TC-MSV-I-013 | `test_snapshot_schema_has_no_new_column` | モデル `_meta` | `InventoryOrderAlertSummarySnapshot` にカラム追加がない | NF-002 | P2 |

#### 取込: `run_summary_aggregation`

テストファイル: `tests/test_build_summary_rows.py`（既存を改修）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| TC-MSV-I-014 | `test_import_fails_entirely_when_mari_stock_query_raises` | 在庫クエリが例外 | **取込全体が失敗**し `aggregation_error` が記録される | F-009 | **P1** |
| TC-MSV-I-015 | `test_previous_snapshot_is_kept_when_mari_stock_query_fails` | 同上 | 直前のスナップショットが残る | F-009 | **P1** |
| TC-MSV-I-016 | `test_no_partial_snapshot_is_created_on_mari_stock_failure` | 同上 | MARI 在庫だけ欠けたスナップショットが作られない | F-009 | **P1** |

### 2.4 Interfaces層テスト

テストファイル: `tests/test_inventory_order_alert_views.py` / `test_inventory_order_alert_row_template.py`（既存を改修）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|------------|------|---------|-----------|--------|
| TC-MSV-X-001 | `test_list_page_shows_both_stock_column_headers` | 一覧 | 「在庫数(SLIMS)」「在庫数(MARI)」が描画される | F-002 | P1 |
| TC-MSV-X-002 | `test_list_page_has_no_responsible_department_column` | 一覧 | 責任部署の列見出しがない | F-005 | P1 |
| TC-MSV-X-003 | `test_list_page_shows_marker_for_not_fetched_mari_stock` | 既存スナップショット | `－` が描画される | F-007 | **P1** |
| TC-MSV-X-004 | `test_list_page_shows_zero_for_zero_mari_stock` | `0` の行 | `0` が描画され空にならない | F-008 #2 | **P1** |
| TC-MSV-X-005 | `test_detail_dialog_has_four_sections` | 一覧 | 品目 / 流動区分 / 在庫 / メモ の見出しがある | F-006 | P1 |
| TC-MSV-X-006 | `test_detail_dialog_shows_responsible_department` | 一覧 | 詳細に責任部署がある | F-005 / F-006 | P1 |
| TC-MSV-X-007 | `test_detail_dialog_shows_both_stock_quantities` | 一覧 | 詳細に両在庫数がある | F-006 | P1 |
| TC-MSV-X-008 | `test_export_csv_has_both_stock_headers` | CSV | 両列の見出しがある | F-004 | P1 |
| TC-MSV-X-009 | `test_list_js_sorts_mari_stock_and_drops_responsible_department` | JS ソース | `mari_stock_qty` の分岐があり、責任部署の列描画がない | F-002 / F-005 | P2 |
| TC-MSV-X-010 | `test_flow_quadrant_judgement_is_unchanged` | 既存の判定テスト | `test_flow_quadrant.py` が全件 Green | NF-004 | **P1** |
| TC-MSV-X-011 | `test_clean_architecture_is_maintained` | 依存方向 | `config/tests/test_clean_architecture.py` が Green | NF-006 | P1 |
| TC-MSV-X-012 | `test_no_bare_stock_quantity_label_remains` | 画面・CSV | 出所を示さない「在庫数」単独の見出しが残っていない | NF-005 | P2 |

---

## 3. テストデータ

### 3.1 代表行（モジュール定数として各テストファイル先頭に定義）

基準日は **2026/8/27 固定リテラル**。`date.today()` は使わない。

| 定数 | SLIMS 在庫 | MARI 在庫 | 用途 |
|---|---|---|---|
| `ROW_BOTH_STOCK` | `100` | `95` | 併記の正常系。差異がある |
| `ROW_SLIMS_ONLY` | `100` | `""` | MARI に該当なし |
| `ROW_MARI_ONLY` | `""` | `50` | SLIMS に該当なし |
| `ROW_ZERO_MARI` | `100` | `0` | **0 と空の区別** |
| `ROW_NEGATIVE_MARI` | `100` | `-5` | 負値をそのまま出す |
| `ROW_LEGACY` | `100` | （キーなし） | **未取得**。既存スナップショット相当 |
| `ROW_NO_INTERNAL_ITEM` | `100` | `""` | 内作品番が解決できない |

### 3.2 異常系テストデータ

| 種別 | 値 | 対応 |
|---|---|---|
| Oracle 例外 | `fetch_mari_stock_totals` が `OracleQueryError` を送出 | TC-MSV-I-014〜016 |
| 大量品番 | 1000 件の内作品番 | TC-MSV-I-004 |
| 小数在庫 | `10.5` | TC-MSV-D-007 |

---

## 4. 境界値・異常系のカバレッジ

### 4.1 境界値テスト

| 対象 | 境界値 | テストケース |
|------|--------|------------|
| MARI 在庫数 | `0`（在庫なし） vs `""`（該当なし） | TC-MSV-D-002 / D-003 / D-010 |
| MARI 在庫数 | `""`（該当なし・キーあり） vs キーなし（未取得） | TC-MSV-D-009 / D-011 / I-011 |
| MARI 在庫数 | 負値 | TC-MSV-D-005 |
| MARI 在庫数 | 小数 | TC-MSV-D-007 |
| 品番数 | Oracle IN 句の上限（900 件）前後 | TC-MSV-I-004 |
| ソート | 値あり / 空 / 未取得 の混在 | TC-MSV-D-016 |

### 4.2 異常系テスト

| 対象 | 異常ケース | 期待される振る舞い |
|------|----------|------------------|
| MARI 在庫クエリ | 例外を送出 | 取込全体が失敗し `aggregation_error` を記録。直前のスナップショットを保持 |
| 内作品番 | 解決できない | MARI 在庫は空。他の列は従来どおり |
| 既存スナップショット | MARI 在庫のキーがない | 画面 `－`、CSV 空。例外にしない |
| 取込の同時実行 | 取込中に一覧を開く | 既存 `import_lock` に従う。新たな排他制御を設けない |

### 4.3 エッジケース

| # | ケース | 検証内容 | 対応REQ-ID | 優先度 |
|---|--------|---------|-----------|--------|
| TC-MSV-E-001 | **配信ペイロードの増分** | 1 行あたりの `mariStockQty` + `display` エントリの増分が **50 バイト以内**。責任部署の削除による減分も併せて計測し、**差し引きの純増**を記録する | NF-001 | **P1** |
| TC-MSV-E-002 | 大量行でのペイロード生成 | 5,000 行で `build_list_client_payload` が完了する | NF-001 | P2 |
| TC-MSV-E-003 | **取込時間の増分** | MARI 在庫クエリの追加による取込時間の増加を計測し記録する | NF-001 / R-1 | P2 |
| TC-MSV-E-004 | 共通品の重複計上 | 同一内作品番に紐づく 2 行が、**同じ MARI 在庫数**を持つ（按分されない） | F-011 | P2 |
| TC-MSV-E-005 | 3 状態の網羅 | 値あり / 該当なし / 未取得 × 画面 / CSV の 6 通りをパラメトライズドで検証 | F-003 / F-007 | **P1** |

> **TC-MSV-E-001 は必ず実測する。** design.md §6.4 の見積り（約 45 バイト）は
> [ISSUE-0005](../../issues/ISSUE-0005-no-payload-size-requirement.md) の反省を踏まえキー名と引用符を含めて数えているが、
> 前回は 2.5 倍ずれた。**見積りと実測が乖離した場合は design.md と本書を改訂する**。

---

## 5. テスト環境

### 5.1 テスト実行コマンド

> **reference との差異**: `django-pytest.md` は `make test-fast` 等を前提とするが、
> 本リポジトリに `Makefile` は無く、`pytest.ini` が `DJANGO_SETTINGS_MODULE = config.settings.development` を指定している。
> したがって **`pytest` を直接実行する**（02_low-flow-visibility と同じ）。

| 目的 | コマンド |
|------|---------|
| Domain 層のみ（TDD の内側ループ、DB 不要） | `pytest application/inventory_order_alert/tests/test_stock_quantity.py -x` |
| アプリ全体 | `pytest application/inventory_order_alert/` |
| アーキテクチャ検証 | `pytest config/tests/test_clean_architecture.py` |
| 全体（回帰確認） | `pytest` |
| 流動区分の非回帰（NF-004） | `pytest application/inventory_order_alert/tests/test_flow_quadrant.py` |

実行はすべて `/django_app/src` を作業ディレクトリとする。

### 5.2 テストデータの準備方法

| 方式 | 用途 | 備考 |
|------|------|------|
| **コード内直接記述** | Domain 層のすべて、Application 層の行データ | 既存慣習。日付は固定リテラル |
| **モジュール定数** | §3.1 の代表 7 行 | 各テストファイル先頭に定義し、他ファイルから import しない（テスト間の暗黙結合を作らない） |
| **`@pytest.mark.parametrize`** | 3 状態 × 出力先（E-005）、境界値 | 期待値表を §4.1 からそのまま書き下す |
| **`unittest.mock`** | Oracle カーソル | 既存の `test_desknet_client.py` の方式に倣う |
| **Django ORM で直接生成** | スナップショット | `@pytest.mark.django_db`。既存 `test_summary_storage.py` に倣う |

---

## 6. テストケース数のまとめ

| 層 | 件数 | うち P1 |
|---|---|---|
| Domain | 27 | 11 |
| Application | 5 | 1 |
| Infrastructure | 16 | 9 |
| Interfaces / 横断 | 12 | 7 |
| エッジケース・性能 | 5 | 2 |
| **合計** | **65** | **30** |

## 7. 要件トレーサビリティ

| 要件ID | テストケース |
|--------|------------|
| REQ-MSV-F-001 | I-001〜I-008、A-002 |
| REQ-MSV-F-002 | D-006、D-012〜D-017、D-022〜D-023、A-001、X-001 |
| REQ-MSV-F-003 | D-001〜D-003、D-007、D-009、E-005 |
| REQ-MSV-F-004 | D-018〜D-021、A-004〜A-005、X-008 |
| REQ-MSV-F-005 | D-014、D-024、D-025、A-003、X-002、X-006、X-009 |
| REQ-MSV-F-006 | D-025〜D-027、X-005〜X-007 |
| REQ-MSV-F-007 | D-004、D-008〜D-009、D-011、D-016、D-020、I-011〜I-012、X-003 |
| REQ-MSV-F-008 | D-002〜D-003、D-005、I-002、I-007、X-004 |
| REQ-MSV-F-009 | I-014〜I-016 |
| REQ-MSV-F-010 | §4.2（既存 `import_lock` に委ねるため新規テストを設けない） |
| REQ-MSV-F-011 | E-004 |
| REQ-MSV-NF-001 | I-003〜I-004、I-008、A-002、E-001〜E-003 |
| REQ-MSV-NF-002 | D-021、I-012〜I-013、A-005 |
| REQ-MSV-NF-003 | I-005 |
| REQ-MSV-NF-004 | X-010 |
| REQ-MSV-NF-005 | X-012 |
| REQ-MSV-NF-006 | X-011 |
| REQ-MSV-NF-007 | §1.4（TDD 方針そのもの） |

---

## レビュー履歴
