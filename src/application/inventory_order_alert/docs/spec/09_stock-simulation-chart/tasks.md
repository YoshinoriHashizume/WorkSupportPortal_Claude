# タスク一覧: 在庫推移グラフを「実績」と「在庫シミュレーション」の2つに分ける

文書ID: TSK-STOCK-SIMULATION-CHART-2026-001
作成日: 2026/09/29
更新日: 2026/09/29
対応文書: [requirements.md](requirements.md)、[design.md](design.md)、[test-design.md](test-design.md)

TDD（Red → Green）。既存テストの期待値も同じタスクで更新する。

| # | タスク | 対象 | 状態 |
|---|---|---|---|
| 1 | 用語集: V-234 日次出荷・V-235 日次入荷・V-236 予定入荷・V-237 在庫シミュレーション を新設、V-218 から予測部分を撤去、V-226/228/229/230 に撤去の印 | ubiquitous_language.md | ✅ 2026/09/29 |
| 2 | 09 要件・設計・テスト設計・タスク | docs/spec/09 | ✅ 2026/09/29 |
| 3 | stock_simulation: 日次の動きの組み立て（TC-SSC-D-001〜013） | stock_simulation.py（新規）+ test_stock_simulation.py | ✅ 2026/09/29 |
| 4 | stock_projection: 上を使うよう改修。**既存の判定結果を変えない**（TC-SSC-C-001〜004） | stock_projection.py + test_stock_projection.py | ✅ 2026/09/29 |
| 5 | summary_queries: `daily_shipment` / `daily_incoming` / `planned_incoming` を行へ（TC-SSC-I-001〜005） | summary_queries.py + test_build_summary_rows.py | ✅ 2026/09/29 |
| 6 | list_client_data: 配信キーの追加（TC-SSC-P-001/002） | list_client_data.py + test_list_client_data.py | ✅ 2026/09/29 |
| 7 | list.html: 区分を 2 つに分割（TC-SSC-X-001〜003） | templates + test_inventory_order_alert_views.py | ✅ 2026/09/29 |
| 8 | JS: V-218 の予測部分を撤去（TC-SSC-J-003/004） | inventory-order-alert-list.js + test_inventory_order_alert_list_js.py | ✅ 2026/09/29 |
| 9 | JS: `buildStockSimulation`（累積和のみ）（TC-SSC-J-001/005） | inventory-order-alert-list.js + 同上 | ✅ 2026/09/29 |
| 10 | JS: `renderStockSimulationChart`（日付軸・棒・縦線・水平線）（TC-SSC-J-002） | inventory-order-alert-list.js + 同上 | ✅ 2026/09/29 |
| 11 | list-client.js: `getResponseClass` に `simulation` を追加 | inventory-order-alert-list-client.js + 同上 | ✅ 2026/09/29 |
| 12 | CSS: 日次グラフのスタイル | app.css + test_inventory_order_alert_views.py | ✅ 2026/09/29 |
| 13 | 機能仕様書 rev 9.0・テスト仕様書の追随 | docs | ✅ 2026/09/29 |
| 14 | 全テスト実行・実データで受け入れ基準を確認し結果を記録（TC-SSC-R-001〜003） | scratchpad | ✅ 2026/09/29 |

## 依存関係

```
3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14
```

3（domain の純関数）が全体の土台。4 で既存判定が不変であることを確認してから先へ進む。

## 実データ確認の記録

（タスク 14。2026/09/29。基準日 2026/09/29 で Oracle から再集計し、取込と同じ後処理を通して計測。DB への書き込みなし。`src/tmp/verify_stock_simulation.py`）

### TC-SSC-R-001: 線と在庫切れ日の一致（最重要）

| 項目 | 結果 |
|---|---|
| 照合単位 | 2,031 |
| **不一致** | **0 件** |

在庫シミュレーションを累積して初めて 0 未満になる日が、保存されている在庫切れ日（V-232）と**全単位で一致**した。判定と描画が同じ配列を読む設計（09 design §1）が効いている。

### TC-SSC-R-002: 対応区分の件数（行数）

| 対応区分 | 件数 |
|---|---:|
| 発注遅れ | 191 |
| 納期確認 | 216 |
| 要発注 | 568 |
| 要監視 | 87 |
| 対象外 | 1,237 |

`stock_projection.py` の改修で判定結果は変わっていない（既存テスト TC-SRR-P/R/N-* が全件そのまま通過）。件数が 09/28 の計測（145 / 272 / 572 / 89 / 1,221）と違うのは基準日と内示の世代が 1 日ぶん動いたため。

### TC-SSC-R-003: 1 行あたりの増分

| 系列 | 平均 | 最大 |
|---|---:|---:|
| 日次出荷（V-234） | 3.9 | 25 |
| 日次入荷（V-235） | 2.8 | 22 |
| 予定入荷（V-236） | 0.5 | 23 |
| （参考）内示 日次・既存 | 24.9 | 68 |

新規 3 系列の合計は平均 7.2 件で、既存の内示日次（24.9 件）の 3 割以下。REQ-SSC-NF-002 を満たす。

### その他

| 項目 | 結果 |
|---|---|
| Oracle への問い合わせ回数 | 増えていない（TC-SSC-I-003 で固定） |
| 過去側（取込日より前）を描ける行 | 1,178 / 2,299。残りは過去 30 日に出荷も入荷もない行で、基準日から右だけを描く |
| 安全在庫の水準線が出る照合単位 | 825 / 2,031 |

### 全テスト

`application/inventory_order_alert` + `config` で **1,296 件 全件成功**（全タスク完了時点）。
