文書ID: TASK-SHIPMENT-HISTORY-CHART-2026-001
作成日: 2026/09/01
更新日: 2026/09/03（入出荷推移の独立グラフ表示を撤去。ステージ8を新設）
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
| 1 | 月次出荷推移VOのテスト作成（TC-SHC-D-001〜009） | domain | [✅2026/09/02 17:40] |
| 2 | `shipment_trend.py` の実装 | domain | [✅2026/09/02 17:40] |

### ステージ2: Oracle取得結果のグループ化と集計行への付与

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 3 | `group_shipments_by_pair()` のテスト作成（TC-SHC-I-001〜003） | infrastructure | [✅2026/09/02 17:40] |
| 4 | `group_shipments_by_pair()` の実装 | infrastructure | [✅2026/09/02 17:40] |
| 5 | `build_summary_rows()` への付与のテスト作成（TC-SHC-I-004〜006） | infrastructure | [✅2026/09/02 17:40] |
| 6 | `build_summary_rows()` への `shipment_trend` 付与 | infrastructure | [✅2026/09/02 17:40] |
| 7 | スナップショット往復・既存互換のテスト作成（TC-SHC-I-007〜008） | infrastructure | [✅2026/09/02 17:40] |
| 8 | codec の互換確認（実装変更不要の確認） | infrastructure | [✅2026/09/02 17:40] |

### ステージ3: ユースケース通過確認

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 9 | `ListPage` 経由での通過テスト作成・確認（TC-SHC-A-001〜002） | use_cases | [✅2026/09/02 17:40] |

### ステージ4: 画面・JS・CSS

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 10 | 詳細ダイアログのテスト改修（TC-SHC-X-001, X-005） | interfaces | [✅2026/09/02 17:40] |
| 11 | `templates/inventory_order_alert/list.html` に「出荷推移」区分を追加 | interfaces | [✅2026/09/02 17:40] |
| 12 | `getShipmentTrend` のテスト作成（TC-SHC-X-002） | interfaces | [✅2026/09/02 17:40] |
| 13 | `inventory-order-alert-list-client.js` に `getShipmentTrend` を追加 | interfaces | [✅2026/09/02 17:40] |
| 14 | `renderShipmentTrendChart` のテスト作成（TC-SHC-X-003〜004） | interfaces | [✅2026/09/02 17:40] |
| 15 | `inventory-order-alert-list.js` に `renderShipmentTrendChart` を追加 | interfaces | [✅2026/09/02 17:40] |
| 16 | `static/css/app.css` に出荷推移区分のスタイルを追加 | interfaces | [✅2026/09/02 17:40] |

### ステージ5: 全体検証と仕上げ

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 17 | エッジケース・性能テストの作成（TC-SHC-E-001〜002） | 横断 | [✅2026/09/02 17:40] |
| 18 | 非回帰テストの確認（TC-SHC-X-006〜007） | 横断 | [✅2026/09/02 17:40] |
| 19 | `collectstatic` とキャッシュバスターの更新 | 横断 | [✅2026/09/02 17:40] |
| 20 | 機能仕様書の改訂 | docs | [✅2026/09/02 17:40] |
| 21 | アプリ全体・リポジトリ全体テストの Green 化 | 横断 | [✅2026/09/02 17:40] |

### ステージ6: 入荷推移（V-217）の追加

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 22 | `fetch_incoming_receipts()` のテスト作成（TC-SHC-I-009, I-011） | infrastructure | [✅2026/09/03 08:35] |
| 23 | `fetch_incoming_receipts()` の実装 | infrastructure | [✅2026/09/03 08:35] |
| 24 | `build_summary_rows()` への `incoming_trend` 付与のテスト作成（TC-SHC-I-010） | infrastructure | [✅2026/09/03 08:35] |
| 25 | `build_summary_rows()` への `incoming_trend` 付与 | infrastructure | [✅2026/09/03 08:35] |
| 26 | `getIncomingTrend` のテスト作成（TC-SHC-X-008） | interfaces | [✅2026/09/03 08:35] |
| 27 | `inventory-order-alert-list-client.js` に `getIncomingTrend` を追加 | interfaces | [✅2026/09/03 08:35] |
| 28 | 2系列描画のテスト作成（TC-SHC-X-009） | interfaces | [✅2026/09/03 08:35] |
| 29 | `renderShipmentTrendChart` を2系列描画に拡張、凡例を追加 | interfaces | [✅2026/09/03 08:35] |
| 30 | 詳細ダイアログの見出しを「入出荷推移」へ変更 | interfaces | [✅2026/09/03 08:35] |
| 31 | ペイロード実測の更新（TC-SHC-E-001 を再測定） | 横断 | [✅2026/09/03 08:35] |
| 32 | 機能仕様書の改訂（§4.1.6 入荷推移の追記） | docs | [✅2026/09/03 08:35] |
| 33 | アプリ全体・リポジトリ全体テストの Green 化（再確認） | 横断 | [✅2026/09/03 08:40] |

### ステージ7: 推定在庫推移（V-218）の追加

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 34 | `parseAnchorQty` / `buildAnchoredStockTrend` のテスト作成（TC-SHC-X-010, X-011, X-013） | interfaces | [✅2026/09/03 09:10] |
| 35 | `inventory-order-alert-list.js` に `parseAnchorQty` / `buildAnchoredStockTrend` を追加 | interfaces | [✅2026/09/03 09:10] |
| 36 | `renderAnchoredStockChart` のテスト作成（TC-SHC-X-012） | interfaces | [✅2026/09/03 09:10] |
| 37 | `inventory-order-alert-list.js` に `renderAnchoredStockChart` を追加、`fillDetailSections` から配線（TC-SHC-X-014） | interfaces | [✅2026/09/03 09:10] |
| 38 | 詳細ダイアログテンプレートのテスト改修（TC-SHC-X-015） | interfaces | [✅2026/09/03 09:10] |
| 39 | `templates/inventory_order_alert/list.html` に「推定在庫推移」区分を追加 | interfaces | [✅2026/09/03 09:10] |
| 40 | `static/css/app.css` に推定在庫推移グラフ・ゼロ基準線のスタイルを追加 | interfaces | [✅2026/09/03 09:10] |
| 41 | 機能仕様書の改訂（§4.1.6 推定在庫推移の追記） | docs | [✅2026/09/03 09:15] |
| 42 | アプリ全体・リポジトリ全体テストの Green 化（再確認） | 横断 | [✅2026/09/03 09:18] |

### ステージ8: 入出荷推移の独立グラフ表示の撤去

ユーザー指示「左に台数と入出荷のグラフはいらない」への対応。出荷推移・入荷推移の**算出**（ステージ2・6）はステージ7（推定在庫推移）の入力として残す。撤去するのは**専用グラフとして描画・表示する処理のみ**。

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 43 | 撤去確認テストの作成・既存テストの削除・置き換え（TC-SHC-X-001, X-003, X-004, X-005, X-009 の撤去。撤去確認テスト新設） | interfaces | [✅2026/09/03 09:30] |
| 44 | `templates/inventory_order_alert/list.html` から「入出荷推移」区分を削除 | interfaces | [✅2026/09/03 09:30] |
| 45 | `inventory-order-alert-list.js` から `renderShipmentTrendChart()` とその呼び出し・`shipmentTrendSection` を削除。`renderAnchoredStockChart()` が流用していた `.ioa-shipment-trend-*` クラス参照を `.ioa-anchored-stock-trend-*` へ付け替え | interfaces | [✅2026/09/03 09:30] |
| 46 | `static/css/app.css` から `.ioa-shipment-trend-*` 系スタイルを削除。付け替え後のクラス用スタイルを追加 | interfaces | [✅2026/09/03 09:30] |
| 47 | requirements.md / design.md / test-design.md の該当要件・節に撤去注記を追加 | docs | [✅2026/09/03 09:35] |
| 48 | 機能仕様書の改訂（§4.1.6 から「入出荷推移」区分の記述を削除、6区分→5区分に戻す） | docs | [✅2026/09/03 09:40] |
| 49 | アプリ全体・リポジトリ全体テストの Green 化（再確認） | 横断 | [✅2026/09/03 09:50] |

### ステージ9: 推定在庫推移グラフの表示改善（見切れ修正・Y軸目盛り追加）

ユーザーからの実画面フィードバック3件への対応。(1) ゼロ基準線（点線）の意味が伝わりにくい→回答で説明のみ・変更なし。(2) 右端の月ラベルがグラフ外に見切れる。(3) 左にY軸の数量目盛りがない。

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 50 | 月ラベル見切れ修正・Y軸目盛り追加のテスト作成（TC-SHC-X-016, X-017） | interfaces | [✅2026/09/03 10:10] |
| 51 | `inventory-order-alert-list.js` の `renderAnchoredStockChart()` を改修（月ラベルの text-anchor 個別設定、Y軸目盛りラベルの追加、`paddingLeft` 拡張） | interfaces | [✅2026/09/03 10:10] |
| 52 | `static/css/app.css` に `.ioa-anchored-stock-trend-y-axis-label` を追加 | interfaces | [✅2026/09/03 10:10] |
| 53 | キャッシュバスター更新・`collectstatic` | 横断 | [✅2026/09/03 10:12] |
| 54 | design.md §6.6 に改修内容を追記 | docs | [✅2026/09/03 10:15] |
| 55 | アプリ全体・リポジトリ全体テストの Green 化（再確認） | 横断 | [✅2026/09/03 10:20] |

### ステージ10: 月ラベル見切れの再修正（CSS優先度バグ）とY軸を等間隔グリッド線化

ステージ9のtext-anchor修正後もユーザーから「まだ見切れてる」との指摘。原因はCSSクラスがJSのsetAttribute("text-anchor",...)より優先されること（SVGのpresentation attributeはCSSカスケードで最下位）。あわせてユーザー提示のExcelグラフを参考に、Y軸目盛りを最大値/最小値のみから等間隔複数目盛り線（グリッド線）方式へ改める（AskUserQuestionで「等間隔の複数目盛り線（推奨）」を選択）。

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 56 | text-anchor修正（style上書き）・グリッド線描画のテスト作成（TC-SHC-X-016改訂, X-018新設） | interfaces | [✅2026/09/03 10:35] |
| 57 | `inventory-order-alert-list.js` の `renderAnchoredStockChart()` を改修（`label.style.textAnchor` へ変更、`GRID_LINE_COUNT`分割の等間隔グリッド線＋ラベル描画に置き換え、ゼロ基準線はマイナス域がある場合のみ描画） | interfaces | [✅2026/09/03 10:35] |
| 58 | `static/css/app.css` に `.ioa-anchored-stock-trend-grid-line` を追加 | interfaces | [✅2026/09/03 10:35] |
| 59 | キャッシュバスター更新・`collectstatic` | 横断 | [✅2026/09/03 10:37] |
| 60 | design.md §6.6 に改訂内容（バグの原因と修正、グリッド線方式）を追記 | docs | [✅2026/09/03 10:40] |
| 61 | アプリ全体・リポジトリ全体テストの Green 化（再確認） | 横断 | [✅2026/09/03 10:50] |

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

--------------------
### 全タスク（1〜21）完了（完了 2026/09/02 17:40）

- **懸念事項**:
  - タスク17のペイロード実測で **+794バイト/行**（見積り約500バイトから乖離）。ISSUE-0005 と同種の見積り誤りが再発した。design.md・DECISIONS.md に記録し、対象期間（24か月固定）の妥当性判断に直接影響する材料とした。
  - 「在庫変動」という元の依頼を「出荷推移」に読み替えて実装した。技術的制約（在庫数の時系列データ不在）による正当な読み替えだが、**ユーザー本人の最終確認前に実装まで完了させている**点はリスクとして DECISIONS.md 冒頭に明記した。
- **改善事項**: `fetch_all_shipments()` の戻り値を `(cust_code, cust_item_cd)` で事前グループ化してから月次集計する設計にしたことで、既存の `aggregate_shipment_stats()`（行ごとに全件線形スキャン）より効率の良い経路を新設できた。既存関数自体は変更していないため、既存の性能特性を悪化させるリスクはない。
- **設計のGoodポイント**: `fetch_all_shipments()` が既に全件・日付付きで取得済みだったため、**新規 Oracle クエリを一切追加せずに実現できた**。REQ-SHC-NF-001（性能）・NF-003（基幹保護）を実装変更なしで満たせる設計だった。
- **チーム共有ポイント**: ペイロード見積りは「キー名+区切り文字を含めて概算する」だけでは依然として過小評価しやすい（今回も約1.6倍の乖離）。**実測をタスクの完了条件に含める運用を今後も徹底する**。

タスク1〜21すべて Green。詳細は各タスク実行時のテスト結果を参照（本レポートは自律実行のため簡潔にまとめた）。
--------------------

--------------------
### ステージ6（タスク22〜33）完了（完了 2026/09/03 08:40）

- **懸念事項**:
  - 入荷推移は出荷推移と異なり、新規 Oracle クエリ（`fetch_incoming_receipts()`）が必要になった。既存の `fetch_last_incoming_by_item_vend()` が範囲指定なしの全件集約だったため、これを安易に模倣せず `WHERE ACPT_DATE >= :window_start` で直近24か月に絞った（REQ-SHC-NF-008）。基幹 Oracle への新規負荷が生じる点は DECISIONS.md 項目3に記録した。
  - `build_monthly_shipment_trend()` / `group_shipments_by_pair()` / `renderShipmentTrendChart` / `ioa-detail-shipment-trend-*` のクラス名・関数名を、入荷にも使う形のまま改名しなかった（design.md R-6）。命名債務として DECISIONS.md に明記した。
- **改善事項**: 出荷・入荷を同一スケール（共通の0〜最大値）で重ね描きすることで、2系列を1グラフで比較できるようにした。空表示の判定を「両系列とも全月0」に限定し、片方のみ実績がある行でもグラフが描かれるようにした。
- **設計のGoodポイント**: 出荷推移で確立した「集計はSLIMS取込時のみ・一覧表示のたびにOracleを呼ばない」設計方針を入荷推移にもそのまま適用できた。`group_shipments_by_pair()` が汎用実装だったため、入荷明細の grouping にコード追加なしで再利用できた。
- **チーム共有ポイント**: 「既存クエリの結果を束ね直すだけで済む」出荷推移と異なり、入荷推移は月次集計に必要な明細粒度のデータが既存クエリになかった。新規クエリを追加する際は、既存の集約専用クエリ（`MAX()`のみ等）を安易に流用せず、必要な粒度・範囲を都度見極める必要がある。

タスク22〜33すべて Green。1行あたり配信ペイロード増分は出荷+入荷合計で実測 +1,587バイト（design.md §6.2）。
--------------------

--------------------
### ステージ7（タスク34〜42）完了（完了 2026/09/03 09:18）

- **懸念事項**:
  - 推定在庫推移の算出ロジック（`buildAnchoredStockTrend`）はクライアント（JS）側の純粋計算であり、この環境には JS 用テストランナーがないため、既存の他JSロジックと同様に**ソース文字列アサーション方式**でしか自動検証できない。数値計算そのものの正しさは、Node で一時スクリプトを実行して手動検証した（3ケース: 通常、起点未取得(null)、マイナスに振れるケース）。結果は期待どおりだったが、自動テストとしては残らない点は今後の課題。
  - 「参考値であり実測ではない」という性質上、利用者が推定値を実測と誤認するリスクは残る。区分見出しの直下に注記文言を置く対応にとどめており、より強い警告（色分け・アイコン等）が必要かはユーザーの実際の利用状況を見て判断する。
- **改善事項**: 算出に必要なデータ（出荷推移・入荷推移・SLIMS/MARI在庫数）がいずれも既に配信済みだったため、サーバー側の変更（Oracle・配信ペイロード）を一切伴わずに実現できた。出荷推移・入荷推移の設計判断（クライアント配信の形）が、想定していなかった今回の追加要求にもそのまま活きた。
- **設計のGoodポイント**: 出荷推移・入荷推移のグラフ描画（`renderShipmentTrendChart`）と同じ座標計算・SVG手組みパターンを踏襲しつつ、ゼロ基準線・可変スケール下限（`Math.min(0, ...)`）という新しい要素を無理なく追加できた。既存パターンの再利用性の高さを確認できた。
- **チーム共有ポイント**: 「累積で見たい」というユーザーの曖昧な要望を、そのまま安易に「入荷−出荷の累積」として実装せず、AskUserQuestion で負値の見せ方を確認した上で「現在庫アンカー型」を選んだ。ユーザーの目的（在庫逼迫の視覚的発見）に立ち返って設計の選択肢を整理したことで、要望どおりの機能に一発で到達できた。

タスク34〜42すべて Green（新規テスト6件追加、リポジトリ全体1673件）。Oracle 問い合わせ回数・配信ペイロードの増加なし（クライアント側純粋計算のため）。
--------------------

--------------------
### ステージ8（タスク43〜49）完了（完了 2026/09/03 09:50）

- **懸念事項**:
  - 「入出荷のグラフはいらない」というユーザー指示は、当初「算出（出荷推移・入荷推移の集計そのもの）」まで含むのか「専用グラフとしての表示だけ」なのか曖昧だった。AskUserQuestionで「詳細ダイアログの『入出荷推移』区分（出荷=青・入荷=橙の2系列グラフ）を区分ごと削除する、という理解であっていますか？」と確認し、算出は推定在庫推移（V-218）の入力として残すことを明確化してから着手した。曖昧なまま実装を始めていれば、V-218が動かなくなる大きな手戻りになっていた。
  - `renderShipmentTrendChart()` が担っていた SVG 描画・凡例生成のロジックは、削除するのではなく `renderAnchoredStockChart()` に既に個別実装されていたため、実質的な重複コードが解消された（削除対象の関数本体と、生き残る関数の実装が別々に存在していた）。クラス名（`.ioa-shipment-trend-*` → `.ioa-anchored-stock-trend-*`）の付け替えを機能撤去と同時に行ったことで、「出荷推移」という名前を持つCSSクラスが実際には推定在庫推移の描画に使われる、という命名との不整合（ステージ6のR-6で残っていた債務）も同時に解消できた。
  - ユビキタス言語集（V-216・V-217）・機能仕様書・requirements.md・design.md・test-design.md の4文書すべてで、「削除」ではなく「表示は撤去したが算出は残る」という区別を一貫して記述する必要があった。CLAUDE.mdの「仕様の原則」に従い、元の要求・記述は削除せず「撤去済み」「（削除）」等の注記を付す方式で全文書を統一した。
- **改善事項**: TDDのRed確認を2つの撤去確認テスト（`test_shipment_trend_dedicated_chart_removed`／`test_shipment_trend_dedicated_section_was_removed`）で行い、実装除去前に両方がFailすることを確認してから着手した。既存の表示系テスト5件（TC-SHC-X-001, 003, 004, 005, 009）は仕様が変わったため削除し、置き換えの新規テストで検証内容を引き継いだ。
- **設計のGoodポイント**: ステージ7で「算出はクライアント側純粋計算」という設計にしていたため、表示撤去がサーバー側（Oracle・配信ペイロード）に一切影響しなかった。`shipmentTrend`・`incomingTrend` の取得コードは1行も削らず、呼び出し先（`renderShipmentTrendChart`呼び出し）だけを削るという最小差分の変更で完結した。
- **チーム共有ポイント**: 「グラフはいらない」という短い依頼文の裏に「算出は要る」という前提が隠れているケースは、機能追加直後の"やっぱり要らない"系の依頼で起こりやすい。実装済み機能の一部だけを撤去する依頼は、"何が入力として使われているか"を洗い出してから着手すると手戻りを防げる。

タスク43〜49すべて Green。アプリ内テスト656件・リポジトリ全体1671件、`manage.py check`／`makemigrations --check --dry-run`とも問題なし。キャッシュバスターを `20260903-shipment-trend-display-removed` に更新し `collectstatic` 実行済み。
--------------------

--------------------
### ステージ9（タスク50〜55）完了（完了 2026/09/03 10:20）

- **懸念事項**:
  - ゼロ基準線（点線）の意味が伝わりにくいという指摘（質問1）はコードの不具合ではなく説明不足だったため、コード変更はせずユーザーへの回答のみで対応した。UIに恒久的な注記を追加すべきか（例: 凡例に「点線=推定在庫0」を明記する等）は、今後同様の質問が繰り返されるようなら再検討する。
  - 月ラベルの見切れは `text-anchor: middle` を全ラベル一律に適用していたことが原因。SVGでラベルをX軸の両端に置く場合、`text-anchor`をmiddleで統一すると原理的に端の文字がはみ出す。今回は先頭/末尾のみ`start`/`end`に個別上書きする最小修正にとどめた。
- **改善事項**: Y軸目盛り追加にあたり、目盛りの本数を「最大値・最小値（・条件付きで0）」の最大3点に絞った。24か月分の全目盛りを出すと詳細ダイアログの限られた高さ（140px）では文字が重なるため、グラフの読み取りに最低限必要な情報（レンジの両端）に絞る判断をした。
- **設計のGoodポイント**: `coordsOf()` が既に共通化されていたため、Y軸ラベルの座標計算に新規ロジックを追加せず既存関数を再利用できた。X軸ラベルの見切れ修正も、描画ループ内の分岐追加のみで完結し、既存のデータ構造・呼び出し方には影響しない変更にとどめられた。
- **チーム共有ポイント**: グラフを新規実装した直後の実画面フィードバック（見切れ・目盛り不足）は、ソース文字列アサーションのテストだけでは検出できない典型例だった。ステージ7完了時のDECISIONS.mdに「JS用テストランナーがなく数値計算の自動テストが手薄」と記録していたが、今回の指摘は数値計算ではなく描画・レイアウトの問題であり、実画面確認の重要性を再確認した。

タスク50〜55すべて Green。新規テスト2件追加（TC-SHC-X-016, X-017）。アプリ内テスト658件・リポジトリ全体1673件、`manage.py check`／`makemigrations --check --dry-run`とも問題なし。キャッシュバスターを `20260903-anchored-chart-axis-fix` に更新し `collectstatic` 実行済み。
--------------------

--------------------
### ステージ10（タスク56〜61）完了（完了 2026/09/03 10:50）

- **懸念事項**:
  - ステージ9でtext-anchorを`setAttribute`で設定したにもかかわらず実画面で反映されなかった原因は、SVGのpresentation attribute（`setAttribute`で設定した属性）がCSSカスケードにおいて外部スタイルシートのクラスセレクタより優先度が低い（ユーザーエージェントのデフォルト相当）ためだった。ソース文字列アサーションのテスト（TC-SHC-X-016旧版）は「該当コードが存在する」ことしか検証できず、この種の**CSS優先度に起因する実描画の不具合を検出できなかった**。JS用テストランナー不在という既知の制約（ステージ7 DECISIONS.md参照）が、今回はより具体的な形で顕在化した。
  - 修正後のテスト（TC-SHC-X-016改訂）は `label.style.textAnchor` の使用と `setAttribute("text-anchor"...)` の不使用を確認する形に変更し、同種の再発（誰かが将来 setAttribute に戻してしまう）を検出できるようにした。ただし依然としてブラウザでの実描画結果そのもの（座標・優先度）は検証できない。
- **改善事項**: ユーザー提示のExcelグラフ（等間隔の複数目盛り線）を参考に、Y軸目盛りを「最大値・最小値のみ」から「`GRID_LINE_COUNT`（4分割=5本）の等間隔グリッド線」に変更した。AskUserQuestionで方式を確認してから実装したため、手戻りなく一度で完了した。
- **設計のGoodポイント**: グリッド線の導入により、既存のゼロ基準線（破線）の役割を「マイナス域が実際にある場合のみ強調表示する危険水準線」に整理できた（全点0以上の行では最下段のグリッド線が0を兼ねるため、重複描画を避けるロジックを追加）。
- **チーム共有ポイント**: SVGを直接操作する実装では、`setAttribute("text-anchor", ...)` のような**presentation attributeでの上書きはCSSクラス指定に負ける**ことがある。優先度を確実にしたい場合は `element.style.xxx`（インラインstyle）を使う、または `!important` 付きCSSを避けて属性側を信頼しないという教訓を得た。今後SVGを手組みする際のチェックポイントとして記憶する。

タスク56〜61すべて Green。新規テスト1件追加（TC-SHC-X-018）、既存テスト1件（TC-SHC-X-016）を実描画に即した内容へ改訂。アプリ内テスト659件・リポジトリ全体1674件、`manage.py check`／`makemigrations --check --dry-run`とも問題なし。キャッシュバスターを `20260903-anchored-chart-grid-lines` に更新し `collectstatic` 実行済み。
--------------------

---

## レビュー履歴

### 自己実施 Implement-L1 相当レビュー (2026/09/02 17:40)

自律実行のため対話レビューではなく自己チェックを実施した。

- **設計書との整合性**: OK。design.md §6.1〜§6.5 のとおりに実装（`group_shipments_by_pair`・`build_monthly_shipment_trend`・`getShipmentTrend`・`renderShipmentTrendChart`）。
- **Clean Architecture のレイヤー違反**: OK。`shipment_trend.py`（domain）に `import django` なし。`config/tests/test_clean_architecture.py` Green。
- **コンテキスト境界（REQ-SHC-NF-005）**: OK。`shipment_trend` アプリ（出荷トレンド）のコードは一切 import していない（`git diff` で確認）。
- **既存コードの保護**: OK。`fetch_all_shipments()` / `aggregate_shipment_stats()` は無変更（TC-SHC-I-006 で非回帰確認）。
- **命名の一貫性**: OK。ユビキタス言語集 V-216「出荷推移」をコード・文書で一貫使用。
- **未解決事項**: DECISIONS.md に記録した5件（在庫変動→出荷推移の読み替え、対象期間24か月、入荷を含めない判断、SVG自前描画、未push）はすべて対話承認を経ていない自己判断であり、**翌営業日のユーザー確認が必須**。
