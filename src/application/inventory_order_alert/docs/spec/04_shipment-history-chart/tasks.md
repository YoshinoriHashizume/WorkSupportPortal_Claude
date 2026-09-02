文書ID: TASK-SHIPMENT-HISTORY-CHART-2026-001
作成日: 2026/09/01
更新日:
対応文書: ./design.md (DESIGN-SHIPMENT-HISTORY-CHART-2026-001), ./test-design.md (TEST-SHIPMENT-HISTORY-CHART-2026-001), ./requirements.md (REQ-SHIPMENT-HISTORY-CHART-2026-001)

# shipment-history-chart タスクリスト

## 0. 実装方針

- **TDD（Red → Green → Refactor）** を採用する（CLAUDE.md §2）。
- **1タスク = 原則1ファイル**。
- Clean Architecture のレイヤー順（domain → infrastructure → interfaces）で進める。
- 既存の `fetch_all_shipments()` / `aggregate_shipment_stats()` は**変更しない**（design.md §5.1）。
- 作業ブランチ: `feature/ioa-shipment-history-chart`（`develop` から分岐）
- JS/CSS 変更後はキャッシュバスター（`?v=`）を更新し `collectstatic` を実行する（過去に更新忘れが発生した実績あり）。

---

## 1. 状況チェックシート

**凡例**: `[ ]` 未着手 / `[~]` 進行中 / `[✅YYYY/MM/DD HH:MM]` 完了 / `[- YYYY/MM/DD HH:MM]` スキップ

### ステージ1: ドメイン層（月次集計ロジック）

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 1 | 月次出荷推移VOのテスト作成（TC-SHC-D-001〜009） | domain | [ ] |
| 2 | `shipment_trend.py` の実装 | domain | [ ] |

### ステージ2: Oracle取得結果のグループ化と集計行への付与

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 3 | `group_shipments_by_pair()` のテスト作成（TC-SHC-I-001〜003） | infrastructure | [ ] |
| 4 | `group_shipments_by_pair()` の実装 | infrastructure | [ ] |
| 5 | `build_summary_rows()` への付与のテスト作成（TC-SHC-I-004〜006） | infrastructure | [ ] |
| 6 | `build_summary_rows()` への `shipment_trend` 付与 | infrastructure | [ ] |
| 7 | スナップショット往復・既存互換のテスト作成（TC-SHC-I-007〜008） | infrastructure | [ ] |
| 8 | codec の互換確認（実装変更不要の確認） | infrastructure | [ ] |

### ステージ3: ユースケース通過確認

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 9 | `ListPage` 経由での通過テスト作成・確認（TC-SHC-A-001〜002） | use_cases | [ ] |

### ステージ4: 画面・JS・CSS

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 10 | 詳細ダイアログのテスト改修（TC-SHC-X-001, X-005） | interfaces | [ ] |
| 11 | `templates/inventory_order_alert/list.html` に「出荷推移」区分を追加 | interfaces | [ ] |
| 12 | `getShipmentTrend` のテスト作成（TC-SHC-X-002） | interfaces | [ ] |
| 13 | `inventory-order-alert-list-client.js` に `getShipmentTrend` を追加 | interfaces | [ ] |
| 14 | `renderShipmentTrendChart` のテスト作成（TC-SHC-X-003〜004） | interfaces | [ ] |
| 15 | `inventory-order-alert-list.js` に `renderShipmentTrendChart` を追加 | interfaces | [ ] |
| 16 | `static/css/app.css` に出荷推移区分のスタイルを追加 | interfaces | [ ] |

### ステージ5: 全体検証と仕上げ

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 17 | エッジケース・性能テストの作成（TC-SHC-E-001〜002） | 横断 | [ ] |
| 18 | 非回帰テストの確認（TC-SHC-X-006〜007） | 横断 | [ ] |
| 19 | `collectstatic` とキャッシュバスターの更新 | 横断 | [ ] |
| 20 | 機能仕様書の改訂 | docs | [ ] |
| 21 | アプリ全体・リポジトリ全体テストの Green 化 | 横断 | [ ] |

---

## 2. タスク詳細

### ステージ1: ドメイン層

#### タスク1: 月次出荷推移VOのテスト作成（TC-SHC-D-001〜009）

- **対象ファイル**: `application/inventory_order_alert/tests/test_shipment_trend_vo.py`（新規）
- **内容**: test-design.md §2.1 の TC-SHC-D-001〜009 を実装する。日付は固定リテラル。
- **完了条件**: 全件 `ImportError` で Red。

#### タスク2: `shipment_trend.py` の実装

- **対象ファイル**: `application/inventory_order_alert/domain/value_objects/shipment_trend.py`（新規）
- **内容**: design.md §4.2 のとおり `build_monthly_shipment_trend()` を実装する。`dates.py` の `add_calendar_months()` を再利用する。`import django` を書かない。
- **完了条件**: `pytest application/inventory_order_alert/tests/test_shipment_trend_vo.py` が Green。

### ステージ2: Oracle取得結果のグループ化と集計行への付与

#### タスク3: `group_shipments_by_pair()` のテスト作成（TC-SHC-I-001〜003）

- **対象ファイル**: `application/inventory_order_alert/tests/test_shipment_trend_query.py`（新規）
- **内容**: test-design.md §2.2 のとおり。
- **完了条件**: 全件 Red。

#### タスク4: `group_shipments_by_pair()` の実装

- **対象ファイル**: `application/inventory_order_alert/infrastructure/oracle/summary_queries.py`
- **内容**: design.md §6.1 のとおり `all_shipments` を `(cust_code, cust_item_cd)` でグループ化する関数を追加する。**既存関数は変更しない**。
- **完了条件**: タスク3のテストが Green。

#### タスク5: `build_summary_rows()` への付与のテスト作成（TC-SHC-I-004〜006）

- **対象ファイル**: `application/inventory_order_alert/tests/test_build_summary_rows.py`（既存を改修）
- **内容**: 既存の `_shipped_pair_patches` パッチ方式を再利用し、`shipment_trend` が付与されること、Oracle 問い合わせ回数が増えないこと（`fetch_all_shipments` の呼び出し回数）、既存の `post_shipment_count` 等が変わらないことを検証する。
- **完了条件**: 3件が Red。

#### タスク6: `build_summary_rows()` への `shipment_trend` 付与

- **対象ファイル**: `application/inventory_order_alert/infrastructure/oracle/summary_queries.py`
- **内容**: `group_shipments_by_pair()` を1回だけ呼び、行ごとに `build_monthly_shipment_trend()` を呼んで `"shipment_trend"` を付与する。
- **完了条件**: タスク5のテストが Green。

#### タスク7: スナップショット往復・既存互換のテスト作成（TC-SHC-I-007〜008）

- **対象ファイル**: `application/inventory_order_alert/tests/test_summary_storage.py`（既存を改修）
- **内容**: `shipment_trend` を含む行の保存・復元、および `shipment_trend` キーを持たない既存スナップショット読込で例外が出ないことを検証する。
- **完了条件**: 2件が Red（既存互換の方は実装によっては最初から Green の可能性がある。その場合は Red 化にこだわらず結果を記録する）。

#### タスク8: codec の互換確認

- **対象ファイル**: なし（検証のみ）
- **内容**: `summary_row_codec.py` の `row_to_storable()` / `row_from_stored()` が汎用実装のため変更不要であることを確認する。もし失敗する場合のみ最小限の対応を行う。
- **完了条件**: タスク7のテストが Green。

### ステージ3: ユースケース通過確認

#### タスク9: `ListPage` 経由での通過テスト作成・確認（TC-SHC-A-001〜002）

- **対象ファイル**: `application/inventory_order_alert/tests/test_usecase_list_page.py`（既存を改修）
- **内容**: `shipment_trend` が `ListPageContext.all_rows` まで届くこと、一覧表示で Oracle を呼ばないことを確認する。
- **完了条件**: 実装変更不要のはず（`ListPage` は行を素通しする）。テストのみ追加し Green を確認する。

### ステージ4: 画面・JS・CSS

#### タスク10: 詳細ダイアログのテスト改修（TC-SHC-X-001, X-005）

- **対象ファイル**: `application/inventory_order_alert/tests/test_inventory_order_alert_views.py`（既存を改修）
- **内容**: 「出荷推移」区分のクラスが存在すること、既存4区分との順序（在庫→出荷推移→メモ）を検証する。
- **完了条件**: Red。

#### タスク11: `templates/inventory_order_alert/list.html` に「出荷推移」区分を追加

- **対象ファイル**: `templates/inventory_order_alert/list.html`
- **内容**: design.md §6.5 のとおり、既存の「在庫」区分と「メモ」区分の間に `ioa-detail-shipment-trend-section` を追加する。SVG の描画先コンテナと「実績なし」表示用の要素を用意する。
- **完了条件**: タスク10のテストが Green。

#### タスク12: `getShipmentTrend` のテスト作成（TC-SHC-X-002）

- **対象ファイル**: `application/inventory_order_alert/tests/test_inventory_order_alert_list_js.py`（既存を改修）
- **内容**: ソース文字列アサーション方式で `getShipmentTrend` の存在と `findRow` の再利用を検証する。
- **完了条件**: Red。

#### タスク13: `inventory-order-alert-list-client.js` に `getShipmentTrend` を追加

- **対象ファイル**: `static/js/inventory-order-alert-list-client.js`
- **内容**: design.md §6.3 のとおり実装する。
- **完了条件**: タスク12のテストが Green。

#### タスク14: `renderShipmentTrendChart` のテスト作成（TC-SHC-X-003〜004）

- **対象ファイル**: `application/inventory_order_alert/tests/test_inventory_order_alert_list_js.py`（既存を改修）
- **内容**: SVG 生成コードの存在、実績なし（全月0またはデータなし）時の表示切り替えロジックの存在を検証する。
- **完了条件**: Red。

#### タスク15: `inventory-order-alert-list.js` に `renderShipmentTrendChart` を追加

- **対象ファイル**: `static/js/inventory-order-alert-list.js`
- **内容**: design.md §6.4 のとおり実装する。`fillDetailSections()` から呼ぶ。
- **完了条件**: タスク14のテストが Green。`node --check` が通る。

#### タスク16: `static/css/app.css` に出荷推移区分のスタイルを追加

- **対象ファイル**: `static/css/app.css`
- **内容**: 区分見出し・グラフ領域・「実績なし」表示のスタイル。既存の `.ioa-detail-section-title` 等を流用し、新規クラスの追加は最小限にする。
- **完了条件**: `pytest application/inventory_order_alert/` が Green。

### ステージ5: 全体検証と仕上げ

#### タスク17: エッジケース・性能テストの作成（TC-SHC-E-001〜002）

- **対象ファイル**: `application/inventory_order_alert/tests/test_shipment_trend_edge_cases.py`（新規）
- **内容**: 1行あたりの配信ペイロード増分を実測する。design.md §6.2 の見積り（約500バイト）と比較し、乖離があれば design.md を改訂する。
- **完了条件**: 全件 Green。実測値を本タスクの実行レポートに記録する。

#### タスク18: 非回帰テストの確認（TC-SHC-X-006〜007）

- **対象ファイル**: なし（検証のみ）
- **内容**: `pytest application/inventory_order_alert/tests/test_flow_quadrant.py` と `pytest config/tests/test_clean_architecture.py` が Green であることを確認する。
- **完了条件**: 両方 Green。

#### タスク19: `collectstatic` とキャッシュバスターの更新

- **対象ファイル**: `templates/inventory_order_alert/list.html`、`templates/base.html`、`staticfiles/`（生成物）
- **内容**: `?v=` を更新し `python manage.py collectstatic --noinput` を実行する。
- **完了条件**: `staticfiles/` が更新され、テンプレートの `?v=` が新しい値になっている。

#### タスク20: 機能仕様書の改訂

- **対象ファイル**: `application/inventory_order_alert/docs/在庫発注アラート_機能仕様書.md`
- **内容**: §4.1.6（詳細ダイアログ）に出荷推移区分を追記する。改訂履歴に追記し、更新日を記録する。
- **完了条件**: 改訂完了。

#### タスク21: アプリ全体・リポジトリ全体テストの Green 化

- **対象ファイル**: なし（検証のみ。失敗があれば該当タスクへ戻る）
- **完了条件**:
  - `pytest application/inventory_order_alert/` が全件 Green。
  - `pytest config/tests/test_clean_architecture.py` が Green。
  - `pytest`（リポジトリ全体）が Green。
  - `python manage.py check` が no issues。
  - `python manage.py makemigrations --check --dry-run` が「No changes detected」（本機能はスキーマ変更を伴わないため）。

---

## 3. タスク実行レポート

（各タスク完了時にここへ追記する。`--------------------` で前後を囲み、実際の時刻を記録する。）

---

## レビュー履歴

（実装レビューがこのセクションに追記する。作成時点では見出しのみ残す。）
