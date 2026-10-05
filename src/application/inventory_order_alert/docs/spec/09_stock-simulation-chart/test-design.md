# テスト設計書: 在庫推移グラフを「実績」と「在庫シミュレーション」の2つに分ける

文書ID: TST-STOCK-SIMULATION-CHART-2026-001
作成日: 2026/09/29
更新日: 2026/09/29
対応文書: [requirements.md](requirements.md)、[design.md](design.md)

---

## 1. 方針

- 基準日は **2026-09-18** に固定する（07/08 と揃える）
- **最重要は「グラフの線と在庫切れ日が一致すること」**（受け入れ基準 3）。これは domain の純関数テストで固定し、さらに実データ全件でも確認する
- 既存の対応区分の判定（TC-SRR-P-001〜012、TC-SRR-R-*）が**1 件も変わらないこと**を、改修の条件として先に確認する
- JS は「サーバが配信した値を累積するだけ」であることを**ソース文字列の検査**で固定する（判定ロジックを JS に持ち込まない）

## 2. テストケース

### 2.1 日次の動きの組み立て（tests/test_stock_simulation.py 新規）

| ID | 内容 | 期待 |
|---|---|---|
| TC-SSC-D-001 | 過去 30 日の出荷・入荷がある | `ship` / `incoming` が日ごとに入る |
| TC-SSC-D-002 | 基準日より 31 日前の出荷 | 範囲外。含めない |
| TC-SSC-D-003 | 基準日**当日**の出荷・入荷 | 含める（起点は基準日終了時点の在庫） |
| TC-SSC-D-004 | 未来の内示・予定入荷 | `demand` / `planned` が日ごとに入る |
| TC-SSC-D-005 | 納期が基準日以前の発注残 | `planned` に**含めない** |
| TC-SSC-D-006 | 同じ (得意先, 内作品番) の行が 2 つ | 内示を二重に数えない |
| TC-SSC-D-007 | 同じ発注番号が複数行 | 予定入荷を二重に数えない |
| TC-SSC-D-008 | 完成品直下でない工程の発注残 | `planned` に含めない |
| TC-SSC-D-009 | 同じ (得意先, 得意先品番) の行が 2 つ | 日次出荷を二重に数えない |
| TC-SSC-D-010 | 同じ (仕入先品番, 仕入先) の行が 2 つ | 日次入荷を二重に数えない |
| TC-SSC-D-011 | `past_days=0` | 過去側を作らない（`build_stock_projection` の呼び方） |
| TC-SSC-D-012 | 日付が解析できない要素 | 捨てる。例外にしない |
| TC-SSC-D-013 | 並び | 日付の昇順 |

### 2.2 判定との一致（tests/test_stock_projection.py 追補）

| ID | 内容 | 期待 |
|---|---|---|
| TC-SSC-C-001 | `build_stock_projection` の在庫切れ日 | **未来側の動きを累積して初めて 0 未満になる日**と一致する |
| TC-SSC-C-002 | 既存の TC-SRR-P-001〜012 | **1 件も結果が変わらない**（改修の受け入れ条件） |
| TC-SSC-C-003 | 既存の TC-SRR-R-*・N-* | 同上 |
| TC-SSC-C-004 | 在庫切れ日がある行 | 発注期限 ＝ 在庫切れ日 − リードタイム |

### 2.3 取込（tests/test_build_summary_rows.py 追補）

| ID | 内容 | 期待 |
|---|---|---|
| TC-SSC-I-001 | 行に `daily_shipment` / `daily_incoming` が付く | 基準日の 30 日前〜基準日の疎な配列 |
| TC-SSC-I-002 | 行に `planned_incoming` が付く | 納期 > 基準日 のみ・発注番号で重複除去済み |
| TC-SSC-I-003 | Oracle の問い合わせ回数 | **現状から増えない**（`fetch_all_shipments` / `fetch_incoming_receipts` の呼び出しが各 1 回のまま） |
| TC-SSC-I-004 | `shipment_trend` / `incoming_trend`（月次） | 変わらず残る |
| TC-SSC-I-005 | 範囲外（31 日前）の明細 | `daily_shipment` に含まれない |

### 2.4 配信ペイロード（tests/test_list_client_data.py 追補）

| ID | 内容 | 期待 |
|---|---|---|
| TC-SSC-P-001 | `dailyShipment` / `dailyIncoming` / `plannedIncoming` / `unconfirmedOrderDaily` | 行の値がそのまま入る |
| TC-SSC-P-002 | 旧スナップショット（キーなし） | 空配列。例外にしない |

### 2.5 画面（tests/test_inventory_order_alert_views.py 追補）

| ID | 内容 | 期待 |
|---|---|---|
| TC-SSC-X-001 | 詳細ダイアログの区分 | 「在庫推移（実績）」と「在庫シミュレーション」が**この順**で出る |
| TC-SSC-X-002 | 在庫シミュレーションの要素 | `ioa-detail-stock-simulation-chart` / `-empty` / `-note` がある |
| TC-SSC-X-003 | 撤去した要素 | 実績グラフ側に予測・予定入荷・在庫切れ月の要素が**残っていない** |

### 2.6 JS（tests/test_inventory_order_alert_list_js.py 追補）

| ID | 内容 | 期待 |
|---|---|---|
| TC-SSC-J-001 | `buildStockSimulation` がある | 累積和のみ。`order_cd` / 重複除去 / `level` による絞り込みを**含まない** |
| TC-SSC-J-002 | `renderStockSimulationChart` がある | 在庫切れ日・発注期限・安全在庫の縦線／水平線を描く |
| TC-SSC-J-003 | `buildForecastStockTrend` が**無い** | V-218 の予測部分の撤去 |
| TC-SSC-J-004 | `renderAnchoredStockChart` の引数 | `forecastSeries` / `stockoutMonth` を取らない |
| TC-SSC-J-005 | 在庫切れ日の再計算をしない | JS に `stockoutDate` の算出式が無く、`row.stockoutDate` を読むだけ |

### 2.7 実データでの確認（scratchpad）

| ID | 内容 | 期待 |
|---|---|---|
| TC-SSC-R-001 | 全照合単位（約 2,031） | 在庫シミュレーションの線が初めて 0 未満になる日 ＝ 在庫切れ日（V-232）。**不一致 0 件** |
| TC-SSC-R-002 | 対応区分の件数 | 改修前後で**変わらない** |
| TC-SSC-R-003 | 1 行あたりの増分 | `daily_shipment` + `daily_incoming` + `planned_incoming` の件数が内示日次（平均 46）と同程度 |

## 3. テストデータ

基準日 2026-09-18。過去 30 日 ＝ 2026-08-19 〜 2026-09-18。

| ケース | 在庫 | 日次出荷 | 日次入荷 | 内示 | 発注残 |
|---|---|---|---|---|---|
| 標準 | 100 | 09/10 に 20 | 09/12 に 50 | 10/01 に 60、10/10 に 60 | 納期 10/05 に 50 |
| 納期遅れ | 100 | — | — | 10/01 に 60 | 納期 09/10 に 50（基準日以前） |
| 内示なし | 100 | 09/10 に 20 | — | なし | なし |
| 在庫未取得 | （キーなし） | — | — | 10/01 に 60 | — |
| 旧スナップショット | 100 | （キーなし） | （キーなし） | 10/01 に 60 | — |
