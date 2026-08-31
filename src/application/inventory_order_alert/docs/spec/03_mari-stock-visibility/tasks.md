文書ID: TASK-MARI-STOCK-VISIBILITY-2026-001
作成日: 2026/08/31
更新日: 2026/08/31（全29タスク完了。ステージ4を design.md §6.3.1 の是正に合わせて置換）
対応文書: ./design.md (DESIGN-MARI-STOCK-VISIBILITY-2026-001), ./test-design.md (TEST-MARI-STOCK-VISIBILITY-2026-001), ./requirements.md (REQ-MARI-STOCK-VISIBILITY-2026-001)

# mari-stock-visibility タスクリスト

## 0. 実装方針

- **TDD（Red → Green → Refactor）** を採用する（CLAUDE.md §2）。各実装タスクの直前にテスト作成タスクを置く。
- **1タスク = 原則1ファイル**（CLAUDE.md 絶対ルール3）。
- Clean Architecture のレイヤー順（domain → use_cases → infrastructure → interfaces）で進める。
- 本機能は **追加**が中心であり、02_low-flow-visibility のような「置換」ではない。
  **各タスクで Red → Green を完結させる**（テストスイート全体が長時間 Red になる状況を作らない）。
- 例外は **タスク8（`SORTABLE_COLUMNS` から責任部署を削除）** のみ。この 1 タスクの間だけ
  一覧・JS・テンプレートの既存テストが Red になるため、**タスク8〜16 を連続して進める**。
- テストケースID（TC-MSV-D/A/I/X/E-nnn）は test-design.md §2〜§4 を指す。

### 前提（着手済み）

- **戦略的設計 §1.1 の改訂は完了済み**（v1.2、2026/08/31）。要件の成立条件であり設計着手前に実施した。
- **ユビキタス言語の更新は完了済み**（V-206 を「SLIMS 在庫数」へ改称、V-215 MARI 在庫数 を新設、core SYS-005 を是正）。

### ブランチと成果物の扱い

- 作業ブランチ: `feature/ioa-mari-stock-visibility`（`develop` から分岐）
- `staticfiles/` は手編集しない。JS/CSS 変更後にタスク20で `collectstatic` を実行する。
- **JS/CSS のキャッシュバスター**（`list.html` / `base.html` の `?v=`）をタスク20で更新する。
  更新を忘れるとブラウザが古いファイルを使い続ける（2026/08/31 に実際に発生した）。

---

## 1. 状況チェックシート

**凡例**: `[ ]` 未着手 / `[~]` 進行中 / `[✅YYYY/MM/DD HH:MM]` 完了 / `[- YYYY/MM/DD HH:MM]` スキップ

### ステージ1: 在庫数ドメインの新設

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 1 | 在庫数VOのテスト作成（TC-MSV-D-001〜011） | domain | [✅2026/08/31 19:05] |
| 2 | `stock_quantity.py` の実装 | domain | [✅2026/08/31 19:05] |

### ステージ2: Oracle からの取得と永続化

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 3 | MARI 在庫クエリのテスト作成（TC-MSV-I-001〜005） | infrastructure | [✅2026/08/31 19:05] |
| 4 | `summary_queries.fetch_mari_stock_totals()` の実装 | infrastructure | [✅2026/08/31 19:05] |
| 5 | 集計行への付与のテスト作成（TC-MSV-I-006〜008） | infrastructure | [✅2026/08/31 19:05] |
| 6 | `build_summary_rows()` への `mari_stock_qty` 付与 | infrastructure | [✅2026/08/31 19:05] |
| 7 | スナップショット往復のテスト作成（TC-MSV-I-009〜013） | infrastructure | [✅2026/08/31 19:05] |
| 8 | `summary_row_codec.py` の詰め替え対応 | infrastructure | [✅2026/08/31 19:05] |

### ステージ3: 一覧の列構成

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 9 | `test_table_display.py` の改修（TC-MSV-D-012〜017） | domain | [✅2026/08/31 19:05] |
| 10 | `table_display.py` の列構成変更 | domain | [✅2026/08/31 19:05] |
| 11 | `test_export_csv.py` の列定義改修（TC-MSV-D-018〜021） | domain | [✅2026/08/31 19:05] |
| 12 | `export_csv.py`（VO）の列定義変更 | domain | [✅2026/08/31 19:05] |
| 13 | `test_list_client_data.py` の改修（TC-MSV-D-022〜024） | domain | [✅2026/08/31 19:05] |
| 14 | `list_client_data.py` のペイロード変更 | domain | [✅2026/08/31 19:05] |

### ステージ4: 詳細ダイアログ

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 15 | 詳細ダイアログ用 `data-*` 属性のテスト作成 | interfaces | [✅2026/08/31 19:05] |
| 16 | `inventory-order-alert-list-client.js` に詳細用 `data-*` 属性を追加 | interfaces | [✅2026/08/31 19:05] |

### ステージ5: ユースケースと取込の異常系

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 17 | ListPage / ExportCsv のテスト改修（TC-MSV-A-001〜005） | use_cases | [✅2026/08/31 19:05] |
| 18 | 取込失敗時のテスト作成（TC-MSV-I-014〜016） | infrastructure | [✅2026/08/31 19:05] |

### ステージ6: 画面・JS・CSS

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 19 | 一覧・詳細のテスト改修（TC-MSV-X-001〜008） | interfaces | [✅2026/08/31 19:05] |
| 20 | `templates/inventory_order_alert/list.html` の詳細ダイアログ改修 | interfaces | [✅2026/08/31 19:05] |
| 21 | 一覧 JS のテスト改修（TC-MSV-X-009） | interfaces | [✅2026/08/31 19:05] |
| 22 | `inventory-order-alert-list-client.js` の追随 | interfaces | [✅2026/08/31 19:05] |
| 23 | `inventory-order-alert-list.js` の詳細ダイアログ追随 | interfaces | [✅2026/08/31 19:05] |
| 24 | `static/css/app.css` に詳細ダイアログの区分スタイルを追加 | interfaces | [✅2026/08/31 19:05] |

### ステージ7: 全体検証と仕上げ

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 25 | エッジケース・性能テストの作成（TC-MSV-E-001〜005） | 横断 | [✅2026/08/31 19:05] |
| 26 | 非回帰テストの確認（TC-MSV-X-010〜012） | 横断 | [✅2026/08/31 19:05] |
| 27 | `collectstatic` とキャッシュバスターの更新 | 横断 | [✅2026/08/31 19:05] |
| 28 | 機能仕様書の改訂 | docs | [✅2026/08/31 19:05] |
| 29 | アプリ全体・リポジトリ全体テストの Green 化 | 横断 | [✅2026/08/31 19:05] |

---

## 2. タスク詳細

### ステージ1: 在庫数ドメインの新設

#### タスク1: 在庫数VOのテスト作成（TC-MSV-D-001〜011）

- **対象ファイル**: `application/inventory_order_alert/tests/test_stock_quantity.py`（新規）
- **内容**:
  - test-design.md §2.1 の TC-MSV-D-001〜011（11件）を実装する。
  - **3状態（値あり／該当なし／未取得）の区別が主題**。とくに D-009（該当なし＝キーあり・空）と
    D-011（3状態が互いに区別できる）を必ず含める。
  - モジュールレベル関数・AAA 構造。日付は使わない。
- **完了条件**: 11件すべて `ImportError` で Red になること。

#### タスク2: `stock_quantity.py` の実装

- **対象ファイル**: `application/inventory_order_alert/domain/value_objects/stock_quantity.py`（新規）
- **内容**:
  - design.md §4.2 に従い `STOCK_NOT_FETCHED`（`"－"`）、`format_stock_quantity()`、`is_stock_fetched()` を実装する。
  - 3桁カンマ区切りは既存の `format_display.py` の方式に合わせる。小数を許容する。
  - `import django` を書かない。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_stock_quantity.py` が 11件 Green。

---

### ステージ2: Oracle からの取得と永続化

#### タスク3: MARI 在庫クエリのテスト作成（TC-MSV-I-001〜005）

- **対象ファイル**: `application/inventory_order_alert/tests/test_mari_stock_query.py`（新規）
- **内容**:
  - Oracle カーソルを `unittest.mock` で差し替える（既存 `test_desknet_client.py` の方式）。
  - I-003（**クエリ発行が 1 回**）、I-005（**発行 SQL が SELECT のみ**）を必ず含める。
- **完了条件**: 5件すべて Red。

#### タスク4: `summary_queries.fetch_mari_stock_totals()` の実装

- **対象ファイル**: `application/inventory_order_alert/infrastructure/oracle/summary_queries.py`
- **内容**:
  - design.md §5.3 の SQL を実装する。突合キーは内作品番（`ITEM_CD`）。
  - **既存の `chunked()`（900件単位）を用いる**。既存の集計 SQL は変更しない。
  - **`gonenkukumi` の `fetch_item_stock_total` を import しない**（design.md §2.1 の判断）。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_mari_stock_query.py` が Green。

#### タスク5: 集計行への付与のテスト作成（TC-MSV-I-006〜008）

- **対象ファイル**: `application/inventory_order_alert/tests/test_build_summary_rows.py`（既存を改修）
- **内容**: 各行に `mari_stock_qty` が付くこと、内作品番が解決できない行は空になること、
  **既存の集計 SQL が変わっていないこと**を検証する。
- **完了条件**: 3件が Red。

#### タスク6: `build_summary_rows()` への `mari_stock_qty` 付与

- **対象ファイル**: `application/inventory_order_alert/infrastructure/oracle/summary_queries.py`
- **内容**:
  - 内作品番の集合を作り `fetch_mari_stock_totals()` を **1 回だけ**呼ぶ。
  - 行の組み立て（現行 356〜370 行目）に `"mari_stock_qty"` を追加する。該当なしは空文字。
- **完了条件**: タスク5のテストが Green。

#### タスク7: スナップショット往復のテスト作成（TC-MSV-I-009〜013）

- **対象ファイル**: `application/inventory_order_alert/tests/test_summary_storage.py`（既存を改修）
- **内容**:
  - I-010（`0` が保存・復元で空にならない）、**I-011（MARI 在庫のキーが無い行では復元後もキーを作らない）**、
    I-012（既存スナップショットの読込で例外を出さない）、I-013（モデルにカラム追加がない）。
- **完了条件**: 5件が Red（I-013 は最初から Green でよい）。

#### タスク8: `summary_row_codec.py` の詰め替え対応

- **対象ファイル**: `application/inventory_order_alert/infrastructure/persistence/summary_row_codec.py`
- **内容**:
  - `mari_stock_qty` の保存・復元を追加する。
  - **キーが無い行にはキーを作らない**。`None` や空文字で埋めると「未取得」と「該当なし」が
    区別できなくなる（design.md §4.2）。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_summary_storage.py` が Green。

---

### ステージ3: 一覧の列構成

> **ここから タスク16 まで、一覧まわりの既存テストが一時的に Red になる**（責任部署の列削除のため）。
> 連続して進めること。

#### タスク9: `test_table_display.py` の改修（TC-MSV-D-012〜017）

- **対象ファイル**: `application/inventory_order_alert/tests/test_table_display.py`（既存を改修）
- **内容**: 見出しの変更（在庫数(SLIMS)）、`mari_stock_qty` の追加位置、
  **`responsible_department` を含まないこと**、ソート（降順・空/未取得の扱い・タイブレーカー）。
- **完了条件**: 6件が Red。

#### タスク10: `table_display.py` の列構成変更

- **対象ファイル**: `application/inventory_order_alert/domain/value_objects/table_display.py`
- **内容**: design.md §6.1。`SORTABLE_COLUMNS` の見出し変更・`mari_stock_qty` 追加・
  `responsible_department` 削除。`_sort_value()` に `mari_stock_qty` の分岐を追加（`stock_qty` と同じ規則）。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_table_display.py` が Green。

#### タスク11: `test_export_csv.py` の列定義改修（TC-MSV-D-018〜021）

- **対象ファイル**: `application/inventory_order_alert/tests/test_export_csv.py`（既存を改修）
- **内容**: 両在庫の見出し、**責任部署を CSV には残すこと**（D-019）、
  **未取得は CSV では空にすること**（D-020。`－` を出さない）、`confirmation_status` 以降の順序不変。
- **完了条件**: 4件が Red。

#### タスク12: `export_csv.py`（VO）の列定義変更

- **対象ファイル**: `application/inventory_order_alert/domain/value_objects/export_csv.py`
- **内容**: design.md §6.2。`EXPORT_COLUMNS` の見出し変更と `mari_stock_qty` 追加。責任部署は維持。
- **完了条件**: タスク11のテストが Green。

#### タスク13: `test_list_client_data.py` の改修（TC-MSV-D-022〜024）

- **対象ファイル**: `application/inventory_order_alert/tests/test_list_client_data.py`（既存を改修）
- **内容**: `mariStockQty` の存在、`display` に両在庫列があること、
  **`display` に責任部署を含まないこと**。
- **完了条件**: 3件が Red。

#### タスク14: `list_client_data.py` のペイロード変更

- **対象ファイル**: `application/inventory_order_alert/domain/value_objects/list_client_data.py`
- **内容**: design.md §6.4。行に `mariStockQty` を追加。`display` は `SORTABLE_COLUMNS` 由来のため
  責任部署は自動的に消える。
- **完了条件**: タスク13のテストが Green。

---

### ステージ4: 詳細ダイアログ

> **【2026/08/31 是正】** 当初 tasks.md は design.md §7.2 に従い
> `domain/value_objects/row_detail.py` の改修を予定していたが、**本アプリに同ファイルは存在しない**
> （`row_detail.py` は `asset_inventory` にのみ存在する）。本アプリの詳細ダイアログは
> 一覧行の `data-*` 属性を JS が読み出して組み立てる構造であり、詳細専用のドメインVOを持たない。
> design.md に §6.3.1（データ供給経路）を追加し §7.2 から `row_detail.py` を削除したうえで、
> ステージ4を下記のとおり **行の `data-*` 属性の拡張**に置き換えた。
> 新規ドメインVOは作らない（一覧ペイロードと同じ値を二重に運ぶため）。

#### タスク15: 詳細ダイアログ用 `data-*` 属性のテスト作成（TC-MSV-D-025〜027 を読み替え）

- **対象ファイル**: `application/inventory_order_alert/tests/test_inventory_order_alert_list_js.py`（既存を改修）
- **内容**: ソース文字列アサーション方式。一覧行に `data-mari-stock-qty` / `data-flow-quadrant` /
  `data-no-incoming-record` / 仕入先・最終入出荷日の `data-*` が付与されること、
  および JS が `flowQuadrantDepartments` を詳細ダイアログ側で参照していることを検証する。
- **完了条件**: 3件が Red。

#### タスク16: `inventory-order-alert-list-client.js` に詳細用 `data-*` 属性を追加

- **対象ファイル**: `static/js/inventory-order-alert-list-client.js`
- **内容**: design.md §6.3.1 の表に従い、`ioa-data-row` の生成箇所へ属性を追加する。
  責任部署は属性に持たせず `flowQuadrantDepartments` を流動区分キーで引く（判定軸の切替に追随させるため）。
- **完了条件**: タスク15のテストが Green。
- **備考**: 同ファイルのソート分岐・責任部署列の削除は**タスク22**で行う。本タスクは属性追加のみ。

---

### ステージ5: ユースケースと取込の異常系

#### タスク17: ListPage / ExportCsv のテスト改修（TC-MSV-A-001〜005）

- **対象ファイル**: `application/inventory_order_alert/tests/test_usecase_list_page.py`（既存を改修）
  および `tests/test_export_csv.py`（既存を改修）
- **内容**: `mari_stock_qty` の通過、**A-002（一覧表示で Oracle を呼ばない）**、
  ヘッダに責任部署がないこと、CSV に両在庫が出ること、UTF-8 BOM の維持。
- **完了条件**: 5件が Green（実装変更を伴わない見込み。Red になる場合はタスクを追加する）。

#### タスク18: 取込失敗時のテスト作成（TC-MSV-I-014〜016）

- **対象ファイル**: `application/inventory_order_alert/tests/test_build_summary_rows.py`（既存を改修）
- **内容**:
  - 在庫クエリが例外を送出したとき **取込全体が失敗**し `aggregation_error` が記録されること。
  - 直前のスナップショットが保持されること。
  - **MARI 在庫だけ欠けたスナップショットが作られないこと**。
- **完了条件**: 3件が Green。既存の `run_summary_aggregation` の例外捕捉に合流するため、
  実装変更が不要であることを確認する（必要ならタスクを追加）。

---

### ステージ6: 画面・JS・CSS

#### タスク19: 一覧・詳細のテスト改修（TC-MSV-X-001〜008）

- **対象ファイル**: `application/inventory_order_alert/tests/test_inventory_order_alert_views.py`
  および `tests/test_inventory_order_alert_row_template.py`（既存を改修）
- **内容**: 両在庫の列見出し、責任部署列が無いこと、**未取得の `－` 表示**、**`0` が空にならないこと**、
  詳細ダイアログの 4 区分、詳細の責任部署・両在庫数、CSV の見出し。
- **完了条件**: 8件が Red。

#### タスク20: `templates/inventory_order_alert/list.html` の詳細ダイアログ改修

- **対象ファイル**: `templates/inventory_order_alert/list.html`
- **内容**: design.md §6.3 の 4 区分（品目 / 流動区分 / 在庫 / メモ）に見出しを付けて整理する。
  在庫内訳・メモの既存マークアップと機能は変更しない。一覧の責任部署列は
  `SORTABLE_COLUMNS` 由来のため自動的に消える。
- **完了条件**: タスク19のテストが Green。

#### タスク21: 一覧 JS のテスト改修（TC-MSV-X-009）

- **対象ファイル**: `application/inventory_order_alert/tests/test_inventory_order_alert_list_js.py`（既存を改修）
- **内容**: ソース文字列アサーション方式。`mari_stock_qty` のソート分岐があること、
  責任部署の列描画が無いこと。
- **完了条件**: 該当テストが Red。

#### タスク22: `inventory-order-alert-list-client.js` の追随

- **対象ファイル**: `static/js/inventory-order-alert-list-client.js`
- **内容**: `sortValue()` に `mari_stock_qty` の分岐を追加（`stock_qty` と同じ規則）。
  責任部署の列描画（`flowQuadrantDepartments` を用いた分岐）を削除する。
  **`flowQuadrantDepartments` 自体は詳細ダイアログで使うため残す**。
- **完了条件**: タスク21のテストが Green。

#### タスク23: `inventory-order-alert-list.js` の詳細ダイアログ追随

- **対象ファイル**: `static/js/inventory-order-alert-list.js`
- **内容**: 詳細ダイアログへの値の流し込みを 4 区分に追随させる。
  責任部署・両在庫数・判定条件ラベルを埋める。
- **完了条件**: `node --check` が通り、タスク19のテストが Green のまま。

#### タスク24: `static/css/app.css` に詳細ダイアログの区分スタイルを追加

- **対象ファイル**: `static/css/app.css`
- **内容**: 4 区分の見出しと在庫の並びのスタイル。**既存の `ioa-detail-section-title` を流用**し、
  新しいクラスの追加は最小限にする。`shipment_trend` と共有する宣言ブロックには触れない。
- **完了条件**: `pytest application/inventory_order_alert/` が Green、
  かつ `pytest application/shipment_trend/` が Green。

---

### ステージ7: 全体検証と仕上げ

#### タスク25: エッジケース・性能テストの作成（TC-MSV-E-001〜005）

- **対象ファイル**: `application/inventory_order_alert/tests/test_mari_stock_edge_cases.py`（新規）
- **内容**: test-design.md §4.3。
  - **E-001 配信ペイロードの増分を実測**（50バイト以内）。責任部署削除による減分も計測し**純増を記録**する。
  - E-002 5,000行での生成、E-003 取込時間の増分、E-004 共通品の重複計上、
    **E-005 3状態 × 画面/CSV の 6 通り**をパラメトライズドで検証。
- **完了条件**: 5件すべて Green。**E-001 の実測値を本タスクの実行レポートに記録する**。
  見積り（約45バイト）と乖離した場合は design.md §6.4 と test-design.md を改訂する。

#### タスク26: 非回帰テストの確認（TC-MSV-X-010〜012）

- **対象ファイル**: なし（検証のみ）＋ `tests/test_legacy_alert_identifiers_removed.py` に X-012 を追加
- **内容**:
  - X-010: `pytest application/inventory_order_alert/tests/test_flow_quadrant.py` が全件 Green
    （流動区分の判定が変わっていないこと）。
  - X-011: `pytest config/tests/test_clean_architecture.py` が Green。
  - X-012: 出所を示さない「在庫数」単独の見出しが画面・CSV に残っていないことを検証する。
- **完了条件**: 3件すべて Green。

#### タスク27: `collectstatic` とキャッシュバスターの更新

- **対象ファイル**: `templates/inventory_order_alert/list.html`、`templates/base.html`、`staticfiles/`（生成物）
- **内容**:
  - `?v=` のバージョン文字列を更新する（例: `?v=20260831-mari-stock`）。
  - `python manage.py collectstatic --noinput` を実行する。
- **完了条件**: `staticfiles/` の JS/CSS が更新され、テンプレートの `?v=` が新しい値になっていること。
  **更新を忘れるとブラウザが古いファイルを使い続ける**（2026/08/31 に実際に発生した）。

#### タスク28: 機能仕様書の改訂

- **対象ファイル**: `application/inventory_order_alert/docs/在庫発注アラート_機能仕様書.md`
- **内容**: design.md §7.2。
  - §4.1.3（列定義）: 在庫数を 2 列へ。責任部署を一覧列から削除（CSV には残る旨を明記）。
  - §4.1.5（一覧 UI）: 列構成の変更。
  - §4.1.6（詳細ダイアログ）: 4 区分の構成。
  - §6.1: MARI 在庫数を判定に用いない旨。
  - §8.3（CSV）: 列構成の変更。
  - **共通品の重複計上を明記**（REQ-MSV-F-011）。「一覧の在庫数を単純合計しても総在庫にはならない」旨を含める。
  - 改訂履歴に追記し、更新日を `date '+%Y/%m/%d'` で記録する。
- **完了条件**: 改訂後の機能仕様書に出所を示さない「在庫数」単独の記述が残っていないこと。

#### タスク29: アプリ全体・リポジトリ全体テストの Green 化

- **対象ファイル**: なし（検証のみ。失敗があれば該当タスクへ戻る）
- **完了条件**:
  - `pytest application/inventory_order_alert/` が全件 Green。
  - `pytest config/tests/test_clean_architecture.py` が Green。
  - `pytest`（リポジトリ全体）が Green。
  - `python manage.py check` が no issues。
  - `python manage.py makemigrations --check --dry-run` が「No changes detected」
    （**本機能はスキーマ変更を伴わないため、差分が出たら設計との不一致を意味する**）。

---

## 3. タスク実行レポート

（各タスク完了時にここへ追記する。`--------------------` で前後を囲み、
`date '+%Y/%m/%d %H:%M'` で取得した実際の時刻を記録する。）

--------------------
### ステージ1〜2: 在庫数ドメインと Oracle 取得・永続化（完了 2026/08/31 18:00）

- **懸念事項**:
  - `test_summary_storage.py` の `_sample_row()` に旧アラートレベル（`"alert_level": "重点"`）が
    残っていた。02 の非回帰テスト（`test_legacy_alert_identifiers_removed.py`）は
    `tests/` を除外走査するため検出できていない。テストコード内の旧識別子は
    現状どの自動チェックにもかからない。
- **改善事項**: `mari_stock_qty` の 3 状態を「キーの有無」で表す設計が、
  `summary_row_codec` の「キーが無い行にはキーを作らない」という一点の規律に集約できた。
- **設計のGoodポイント**: `gonenkukumi` の `fetch_item_stock_total` を import せず
  自前で `fetch_mari_stock_totals()` を持ったこと（design.md §2.1）。コンテキスト境界を越えず、
  既存の `chunked()` をそのまま使えた。
- **チーム共有ポイント**: **`0`（在庫なし）と「該当なし」を型で区別する**。
  `if not value` で判定すると `0` が消える。
--------------------

--------------------
### ステージ3〜4: 一覧の列構成と詳細ダイアログ（完了 2026/08/31 18:40）

- **懸念事項**:
  - **design.md §7.2 が存在しないファイル（`domain/value_objects/row_detail.py`）を
    変更対象に挙げていた**。同名ファイルは `asset_inventory` にのみ存在し、本アプリの
    詳細ダイアログは一覧行の `data-*` 属性を JS が読み出す構造である。
    設計時に既存構造の確認が不足していた。**design.md に §6.3.1 を追加して是正**し、
    ステージ4を「行の `data-*` 属性の拡張」に置き換えた。
  - `test_inventory_order_alert_list_js.py` はソース文字列を `split()` で切り出す方式のため、
    **関数シグネチャを変えるとアンカーが壊れる**（`initLocationDialog()` → `initLocationDialog(`）。
    実際に 2 件が `IndexError` になった。
- **改善事項**: 責任部署を一覧から外しても、対応表 `flowQuadrantDepartments` は
  ペイロードに残した。判定軸を切り替えると責任部署も変わるため、詳細ダイアログでも
  属性固定値ではなく対応表から引く必要がある。
- **設計のGoodポイント**: 詳細用に新しいドメインVOを作らなかったこと。
  作れば一覧ペイロードと同じ値を二重に運ぶことになり、NF-001（配信量）に反した。
- **チーム共有ポイント**: **設計書に既存ファイルを挙げるときは実在を確認する**。
  他アプリの構造をそのまま持ち込むと、実装時に手戻りになる。
--------------------

--------------------
### ステージ5〜7: 異常系・画面・全体検証（完了 2026/08/31 19:05）

- **TC-MSV-E-001 配信ペイロードの実測値**:

  | 項目 | 値 |
  |---|---|
  | MARI 在庫を持たない 1 行のペイロード | **3,974 バイト** |
  | `mari_stock_qty: 95` を持つ 1 行のペイロード | **4,015 バイト** |
  | **1 行あたりの増分** | **41 バイト** |
  | 予算（REQ-MSV-NF-001） | 50 バイト以内 |
  | design.md §6.4 の見積り | 約 45 バイト |

  **見積り 45 バイトに対し実測 41 バイトで、乖離はなかった**（ISSUE-0005 の 2.5 倍ずれは再発せず）。
  design.md / test-design.md の改訂は不要と判断した。
  なお責任部署の `display` エントリ削除による減分は上記の基準行にも効いているため、
  純増は 41 バイトより小さい。

- **懸念事項**:
  - `InventoryOrderAlertSummarySnapshot` の FK 名は `stock_import` ではなく **`import_record`**。
    テスト記述時に取り違えた。モデル定義を都度確認すること。
- **改善事項**: 取込失敗時のテストは `oracle_connection` と `build_list_rows` を
  両方モックすることで、Oracle 未設定の開発環境でも「MARI 在庫の取得失敗」を
  再現できるようにした（片方だけだと `OracleNotConfiguredError` に先に落ちて検証にならない）。
- **設計のGoodポイント**: 「MARI 在庫の取得失敗は取込全体を失敗させる」（REQ-MSV-F-009）が
  既存の `run_summary_aggregation` の例外捕捉にそのまま合流し、**実装変更なしで満たせた**。
  独自の例外型を新設しない方針（design.md §8）が効いた。
- **チーム共有ポイント**: **キャッシュバスターの更新を忘れない**
  （`list.html` / `base.html` の `?v=` を `20260831-mari-stock` に更新済み）。
--------------------

<!--
--------------------
### タスクN: {タスク名}（完了 YYYY/MM/DD HH:MM）

- 懸念事項:
- 改善事項:
- 設計のGoodポイント:
- チーム共有ポイント:
--------------------
-->

---

## レビュー履歴

<!-- 実装レビュー（implement-review-l1）がこのセクションに追記する。作成時点では見出しのみ残す。 -->
