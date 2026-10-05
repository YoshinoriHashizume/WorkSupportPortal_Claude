# テスト設計書: 流動区分の 7 分類化

文書ID: TST-FLOW-QUADRANT-REFINEMENT-2026-001
作成日: 2026/09/18
更新日: 2026/09/21（在庫切れ予測月・欠品の危険条件を追加。TC-FQR-F-006 の比較対象を確定し F-006a/006b を追加。期間判断の統一基準に伴い F-005 系・L-006/007・C-005 系を改訂）
対応文書: [requirements.md](requirements.md)、[design.md](design.md)

---

## 1. 方針

- 既存の 05・06 テストは 7 区分・新ランク・需要予測の内示のみ化（実績ベースの廃止）に合わせて期待値を更新する。実績ベースを前提とするテストは「なし」になる期待に書き換える（テスト ID は残す）
- 基準日は `2026-09-18` 固定。直近入荷の境界は 30 日（8/19 は含む、8/18 は含まない）
- 実データでの受け入れ（requirements §8）は scratchpad のスクリプトで確認し、tasks.md に結果を記録する

## 2. テストケース

### 2.1 flow_quadrant（tests/test_flow_quadrant.py 追記）

| ID | 内容 | 期待 |
|---|---|---|
| TC-FQR-Q-001 | 在庫なし・需要あり・直近入荷なし | 欠品（入荷なし） |
| TC-FQR-Q-002 | 在庫なし・需要あり・直近入荷あり | 欠品 |
| TC-FQR-Q-003 | 在庫なし・需要なし（直近入荷の有無によらず） | 打ち切り候補 |
| TC-FQR-Q-004 | 在庫あり（stock_missing=False）は従来 4 分岐 | 4 区分 |
| TC-FQR-Q-005 | 行列（Y1/Y3/Y5）: 在庫なし行は全キー同値 | 3 キーとも同じキー |
| TC-FQR-Q-006 | ランク: 欠品（入荷なし）0 … 通常流動品 6、`FLOW_QUADRANTS` がランク順 7 値 | |
| TC-FQR-Q-007 | `is_flow_escalated(低流動品（入荷なし）, 欠品（入荷なし）)` True、逆は False | |
| TC-FQR-Q-008 | `normalize_flow_quadrant` が新キー・新ラベル・旧称を扱う。「欠品（入荷即出荷）」「stockout-pass-through」→ 欠品 | |
| TC-FQR-Q-009 | `is_recent_incoming` 境界（8/19 True、8/18 False、None False） | |
| TC-FQR-Q-010 | `FlowThresholds` 範囲外（0 日・91 日）は ValueError。`demand_window_months` フィールドを持たない | |

### 2.2 flow_facts（tests/test_flow_facts.py 新規）

| ID | 内容 | 期待 |
|---|---|---|
| TC-FQR-F-001 | `row_stock_missing`: stock_qty "" かつ unit 合計 None/0 → True。stock_qty "5" → False。キーなし → False。stock_qty "" だが unit 合計 3 → False | |
| TC-FQR-F-002 | `row_has_demand`: basis 内示 → True、なし → False、旧値「実績ベース」→ False。basis なし・内示推移（翌月〜翌々々月）qty>0 → True。basis なし・内示 0・出荷推移直近 3 か月 >0 → **False**（出荷は見ない） | |
| TC-FQR-F-003 | `build_flow_facts` が 3 真偽と日付を組み立てる | |
| TC-FQR-F-004 | 理由: 欠品（入荷なし）+ 最終入荷空 → 「入荷の記録なし・経路要確認」 | |
| TC-FQR-F-005 | 理由: 欠品 2 区分 + 期間内出荷なし → 「{判定期間}以上出荷なし・経路要確認」（判定期間 1 年なら「1年以上出荷なし・経路要確認」）。期間内出荷あり → なし。判定期間を 5 年にすると同じ行で理由が消える（2026/09/21 改訂） | 2026/09/21 |
| TC-FQR-F-005a | 最終出荷日が空の行も「期間内出荷なし」として理由が付く | 2026/09/21 |
| TC-FQR-F-005b | 低流動品（出荷なし）・打ち切り候補・通常流動品には本理由を付けない（欠品 2 区分のみ） | 2026/09/21 |
| TC-FQR-F-006 | 理由: 欠品 + 最終入荷日が属する月の入荷合計 10 < 翌月の内示 20 → 「入荷 < 需要」。同月の入荷 20 以上 → なし。翌月の内示 0（需要は翌々月から）→ なし。最終入荷日が空 → なし（2026/09/21 確定。REQ-FQR-F-005） | 2026/09/21 |
| TC-FQR-F-006a | `row_last_incoming_month_qty`: 最終入荷 2026/08/25・入荷推移 2026-08 が 10 → 10（当月 2026-09 が 0 でも 10）。最終入荷日が空・推移なし → 0 | 2026/09/21 |
| TC-FQR-F-006b | `row_next_month_demand`: basis 内示・monthly (0, 320, 290) → 0。monthly (20, …) → 20。basis なし → 0 | 2026/09/21 |
| TC-FQR-F-007 | 理由: 低流動品（出荷なし）+ basis 内示 → 「内示あり（立ち上がり／出荷経路要確認）」 | |
| TC-FQR-F-008 | 理由: 打ち切り候補 + phase_out_date 2026/03/31 → 「適用終了日 2026/03/31」。未来日・空 → なし | |
| TC-FQR-F-009 | 通常流動品の理由は空 | |

### 2.3 list_rows（tests/test_list_rows.py 追記）

| ID | 内容 | 期待 |
|---|---|---|
| TC-FQR-L-001 | 在庫なし・basis 内示・最終入荷 9/10 の行 → flow_quadrant 欠品、key、flow_reasons、flow_quadrants 全キー同値 | |
| TC-FQR-L-002 | 在庫なし・basis なし → 打ち切り候補、状況に最終出荷、推奨アクションが営業向け | |
| TC-FQR-L-003 | 旧行（stock_qty キーなし・basis なし・推移なし）→ 4 区分（在庫死蔵品等）、欠品にならない | |
| TC-FQR-L-004 | 既定並び: 在庫切れリスク同値なら ランク順（欠品（入荷なし）が低流動品（入荷なし）より前） | |
| TC-FQR-L-005 | フィルタ `flow_quadrant=stockout` で該当行のみ | |
| TC-FQR-L-006 | 行が `flow_reasons_by_period`（Y1/Y3/Y5）を持ち、各期間の区分に対応した理由が入る。`flow_reasons` は表示中の判定期間のもの（2026/09/21） | 2026/09/21 |
| TC-FQR-L-007 | 低流動品（出荷なし）の行は Y1 で「内示あり（立ち上がり／出荷経路要確認）」、期間を広げて通常流動品になる Y5 では理由なし（期間切替で理由が古いまま残らない） | 2026/09/21 |

### 2.4 recommended_action / rules（既存テスト更新）

| ID | 内容 | 期待 |
|---|---|---|
| TC-FQR-A-001 | `DEFAULT_RECOMMENDED_ACTIONS` は 7 件・ランク順。6 件だと ValueError | |
| TC-FQR-A-002 | 欠品（入荷なし）の状況が `{recent_days}` を 30 に埋める。打ち切り候補の状況は「在庫なし・内示なし（最終出荷 {last_ship}）」で `{demand_window}` を含まない | |
| TC-FQR-A-003 | 判定ルール行 7 行、条件列（在庫/需要/直近入荷/期間内入荷/期間内出荷）が表どおり | |
| TC-FQR-A-004 | 定義ファイルの上書きが新キー（`stockout-no-incoming` 等）で効く | |

### 2.5 demand_forecast（既存テスト更新）

| ID | 内容 | 期待 |
|---|---|---|
| TC-FQR-D-001 | 内示 0・出荷推移 直近 3 か月 (10, 20, 30) → **なし**（basis `なし`・月平均 0。従来は実績ベース） | |
| TC-FQR-D-002 | 出荷が 4〜12 か月前のみ → なし | |
| TC-FQR-D-003 | `DEMAND_FORECAST_BASES` は (`内示`, `なし`) の 2 値。`DemandForecast(basis="実績ベース")` は ValueError | |
| TC-FQR-D-004 | `attach_demand_forecast`: 内示なし・出荷ありの行は 在庫切れ予測月・在庫月数が None | |
| TC-FQR-D-005 | `stockout_forecast_month`: 在庫 0・当月残 0・月別 (0, 320, 290) → **2026-11**（従来は当月）。在庫 0・当月残 50 → 当月。在庫 0・月別 (200, …) → 翌月 | 2026/09/21 |
| TC-FQR-D-006 | 05 の D-100 系「在庫 0 以下は当月」の期待値を D-005 の規則に更新（在庫 0 かつ当月残 > 0 の場合だけ当月） | 2026/09/21 |

### 2.6 stockout_risk（tests/test_stockout_risk.py 追記）

| ID | 内容 | 期待 |
|---|---|---|
| TC-FQR-R-001 | 在庫なし・需要あり（猶予 0）・直近入荷あり・MRP・発注残なし → 危険（従来は「直近に入荷あり」で注意）。理由に「在庫なし」「供給遅延（入荷即出荷）」、「直近に入荷あり」は付かない | |
| TC-FQR-R-002 | 在庫なし・発注残が不足数量以上・納期遅れなし → 注意（対象外にしない）。理由「在庫なし」 | |
| TC-FQR-R-003 | 在庫なし・猶予 0・発注残 < 不足数量 → 危険 | |
| TC-FQR-R-003a | 在庫なし・猶予 44 日（> LT＋安全日数）・発注残なし・MRP → **注意**（MRP 先送りは在庫ありのみ。危険は猶予内のみ。2026/09/21） | |
| TC-FQR-R-003b | 在庫なし・猶予 0・発注残なし・上流工程に補充期限内の発注残あり → 注意（上流の免除は欠品でも有効） | |
| TC-FQR-R-004 | 在庫あり・直近入荷あり・MRP・発注残なし → 注意（06 補正 3 の規則は維持）。手動発注なら危険 | |
| TC-FQR-R-005 | 在庫なし・需要なし → 監視 | |
| TC-FQR-R-007 | 在庫あり・内示なし・出荷推移あり → basis なし → 監視（理由なし）。理由「需要は実績ベース」は存在しない | |
| TC-FQR-R-008 | `_forecast_of`: 旧スナップショットの basis「実績ベース」→ `NO_DEMAND`（監視） | |
| TC-FQR-R-006 | `attach_stockout_risk` が行の stock_qty "" を在庫なしとして渡す（stock_qty "0" も同様に扱わない: 0 は SLIMS 行ありの在庫ゼロ → 在庫あり扱い・従来判定） | |

### 2.7 集計・帯・API・CSV・JS

| ID | 内容 | 期待 |
|---|---|---|
| TC-FQR-C-001 | `count_rows` の by_quadrant 7 キー、attention に欠品を含む | |
| TC-FQR-C-002 | メニュー帯文言「欠品（入荷なし） N 件 / 欠品 N 件 / …」 | |
| TC-FQR-C-003 | summary_api counts に `stockoutNoIncoming` 等 3 キー | |
| TC-FQR-C-004 | CSV の流動区分に 7 種の値が出る（列数 39 のまま） | |
| TC-FQR-C-005 | list_client_data に `flowReasons`・`flowReasonsByPeriod`・`flowQuadrantOrder` | |
| TC-FQR-C-005a | JS: `getFlowReasons(custCode, itemCd, periodKey)` が期間キーで理由を引き直す。詳細ダイアログは選択中の期間の理由を出す（2026/09/21） | 2026/09/21 |
| TC-FQR-C-005b | 判定ルールダイアログの説明文に期間判断の基準が書かれ、需要の定義に出荷実績が含まれない（2026/09/21） | 2026/09/21 |
| TC-FQR-C-006 | JS: FLOW_RANK 7 キー、フィルタ選択肢 7、ルールダイアログ列 | |
| TC-FQR-C-007 | JS: 推定在庫推移の予測部分（`buildForecastStockTrend`）は basis が「内示」のときのみ点を返す（「なし」・旧値「実績ベース」は空配列） | |
| TC-FQR-C-007 | 旧識別子走査に「通過品」「ランク 3 = 通常流動品」等の旧記述が残らない | |

### 2.8 取込順序

| ID | 内容 | 期待 |
|---|---|---|
| TC-FQR-I-001 | `ImportStock._enrich_rows` の出力行に `flow_quadrant` が需要予測を反映した値で入り、`stockout_risk` は在庫なし分岐を通る | |
| TC-FQR-I-002 | 適用終了日の取得失敗が警告になり取込は続く | |
