文書ID: TASK-STOCKOUT-RISK-2026-001
作成日: 2026/09/17
更新日: 2026/09/21
対応文書: ./design.md（DESIGN-STOCKOUT-RISK-2026-001）, ./test-design.md（TEST-STOCKOUT-RISK-2026-001）, ./requirements.md（REQ-STOCKOUT-RISK-2026-001）

# 06_stockout-risk タスクリスト

## 状況チェックシート

**凡例**: [ ] 未着手 / [~] 進行中 / [✅YYYY/MM/DD HH:MM] 完了 / [- YYYY/MM/DD HH:MM] スキップ

方針: 1 タスク = 原則 1 ファイル。TDD（テスト Red → 実装 Green）。第 1 段階を検証・報告してから第 2 段階へ。

### 第 1 段階: 判定と表示（設定は既定値）

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 1 | 発注残・補充見込みのテスト（D-001〜006） | domain/test | [✅2026/09/17 16:25] |
| 2 | `open_purchase_order.py` の実装 | domain | [✅2026/09/17 16:25] |
| 3 | 発注方式・リードタイムのテスト（D-010〜011） | domain/test | [✅2026/09/17 16:25] |
| 4 | `ordering_profile.py` の実装 | domain | [✅2026/09/17 16:25] |
| 5 | 設定 VO のテスト（D-054） | domain/test | [✅2026/09/17 16:28] |
| 6 | `app_settings.py` の実装（3 項目追加） | domain | [✅2026/09/17 16:28] |
| 7 | 在庫切れリスクのテスト（D-020〜053） | domain/test | [✅2026/09/17 16:28] |
| 8 | `stockout_risk.py` の実装 | domain | [✅2026/09/17 16:29] |
| 9 | 件数・ソート・フィルタ・ペイロード・CSV のテスト（D-060〜064） | domain/test | [✅2026/09/17 16:35] |
| 10 | `row_counts.py` / `row_display.py` / `table_display.py` / `list_rows.py` / `list_query.py` / `list_client_data.py` / `export_csv.py` の実装 | domain | [✅2026/09/17 16:35] |
| 11 | モデル・マイグレーション 0012・`settings_repository.py` | infrastructure | [✅2026/09/17 16:29] |
| 12 | 発注残・品目マスタクエリのテスト（I-001〜006） | infrastructure/test | [✅2026/09/17 16:31] |
| 13 | `summary_queries.py` の実装 | infrastructure | [✅2026/09/17 16:32] |
| 14 | 取込ユースケースのテスト（A-001〜002） | use_cases/test | [✅2026/09/17 16:32] |
| 15 | `import_stock.py` / `wiring.py` の実装 | use_cases / interfaces | [✅2026/09/17 16:33] |
| 16 | `list_page.py` / `portal_dashboard.py` / `summary_api.py` ほかの追随 | use_cases | [✅2026/09/17 16:40] |
| 17 | `list.html` / `dashboard.html` / 両 JS / `app.css` の実装 | interfaces | [✅2026/09/17 16:44] |
| 18 | ビュー・JS ソースのテスト（X-001〜009） | interfaces/test | [✅2026/09/17 16:47] |
| 19 | 実データ検証（§3）と DECISIONS 記録、全体検証 | 検証 | [✅2026/09/17 16:55] ブラウザ目視は未実施 |

### 第 2 段階: 設定画面・確認記録

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 20 | 設定画面・設定 API の 3 項目（F-010） | interfaces | [ ] |
| 21 | 確認記録への在庫切れリスク保存と危険化による未確認化（F-011、マイグレーション 0013） | domain / infrastructure | [ ] |
| 22 | 機能仕様書の改訂と第 2 段階の検証 | docs / 検証 | [ ] |

### 第 1 段階 補正（2026/09/18 レビュー指摘）: 発注残の重複除去キーと軽微修正

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 23 | 要件 F-001 に発注コード（`PUCH_ODR_CD`）、design §4.1/§5/§6.1 の重複除去キーを `order_cd` に改訂 | docs | [✅2026/09/18 20:50] |
| 24 | 重複除去のテスト（D-006 改訂、同キー別明細の追加） | domain/test | [✅2026/09/18 20:50] |
| 25 | `open_purchase_order.py`: `order_cd` と重複除去キーの変更 | domain | [✅2026/09/18 20:50] |
| 26 | 発注残クエリのテスト（I-001/I-002 に `PUCH_ODR_CD`、残数 ≤ 0 の除外） | infrastructure/test | [✅2026/09/18 20:50] |
| 27 | `summary_queries.py`: `PUCH_ODR_CD` の取得・`order_cd`・残数 ≤ 0 の除外 | infrastructure | [✅2026/09/18 20:50] |
| 28 | `test_build_summary_rows.py` の期待値追随 | infrastructure/test | [✅2026/09/18 20:50] |
| 29 | `stockout_risk.py`: 未使用 import 削除、空 `item_cd` 行のキャッシュ共有解消、`rows_of()` の呼び出し削減 | domain | [✅2026/09/18 20:50] |
| 30 | `app_settings.py`: 関数内 import を先頭へ | domain | [✅2026/09/18 20:50] |
| 31 | 07 タスク 6（`flow_quadrant_rules.py` 7 行化・3 列追加）と Red 3 件のテスト追随、`list.html` 判定ルール表の 3 列 | domain / interfaces | [✅2026/09/18 20:50] |
| 32 | 全テスト・`manage.py check`・実データ再計測と DECISIONS 追記、07 tasks.md の状態更新 | 検証 | [✅2026/09/18 20:50] |

### 第 1 段階 補正 2（2026/09/18 仕様判断）: 上流工程の混在ケース・予測グラフの需要

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 33 | 要件 F-005/F-006（混在時は注意・理由は両方）、design §4.1/§4.3/§6.4a（需要は照合単位合計）を改訂 | docs | [✅2026/09/18 21:30] |
| 34 | 補充見込みのテスト（上流の納期内残数 `upstream_pending_qty`） | domain/test | [✅2026/09/18 21:30] |
| 35 | `open_purchase_order.py`: `ReplenishmentOutlook.upstream_pending_qty` | domain | [✅2026/09/18 21:30] |
| 36 | 在庫切れリスクのテスト（混在 → 注意・理由 2 つ） | domain/test | [✅2026/09/18 21:30] |
| 37 | `stockout_risk.py`: 危険の除外条件と理由の独立化 | domain | [✅2026/09/18 21:30] |
| 38 | JS ソース断言（予測の需要は `demandForecast` の単位合計） | interfaces/test | [✅2026/09/18 21:30] |
| 39 | `inventory-order-alert-list.js`: `buildForecastStockTrend` の需要を単位合計に、`list.html` のキャッシュバスター | interfaces | [✅2026/09/18 21:30] |
| 40 | 全テスト・実データ計測（混在ケース件数・危険→注意）と DECISIONS 追記 | 検証 | [✅2026/09/18 21:30] |

### 第 1 段階 補正 3（2026/09/21 判定レビュー）: 目的に沿った危険・注意の再定義

契機: 「目的（在庫切れを起こさない）と背景を踏まえたリスク判定のレビュー」で 7 件を指摘し、ユーザーが全件採用。
選択: 長期納期超過の基準は LT＋安全日数 / MRP の先送りは対象外 / 発注方式「不明」は手動発注と同じ扱い。

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 41 | 用語集: V-226 の定義改訂、V-229 補充期限・V-230 長期納期超過の追加、V-224 補足 | docs | [✅2026/09/21] |
| 42 | 要件 F-003 / F-005 / F-006 / F-014 #5・#11 の改訂、§6.4 事項 8（発注残の状態 1）追加 | docs | [✅2026/09/21] |
| 43 | design §4.1（補充期限・`stale_qty`・上流の納期窓）/ §4.3 判定順 / §5 行キー / §6.3 ペイロード / §9 | docs | [✅2026/09/21] |
| 44 | test-design: D-034〜D-040 の改訂、D-045〜D-052 の追加 | docs | [✅2026/09/21] |
| 45 | 補充見込みのテスト（補充期限・長期納期超過の分離・上流の納期窓） | domain/test | [✅2026/09/21] |
| 46 | `open_purchase_order.py`: `replenishment_deadline()`、`ReplenishmentOutlook.stale_qty`、上流 pending の納期窓 | domain | [✅2026/09/21] |
| 47 | 在庫切れリスクのテスト（危険 = 不足、MRP 先送り = 対象外、免除は MRP のみ、発注忘れは発注残なしのみ） | domain/test | [✅2026/09/21] |
| 48 | `stockout_risk.py`: 判定順・免除・理由・行キー `replenishment_stale_qty` | domain | [✅2026/09/21] |
| 49 | ペイロードのテストと `list_client_data.py`（`replenishment.staleQty`） | domain/test + domain | [✅2026/09/21] |
| 50 | `inventory-order-alert-list.js` 詳細ダイアログの補充見込み表示、`list.html` キャッシュバスター | interfaces | [✅2026/09/21] |
| 51 | 全テスト・`manage.py check`・実データ再判定（前後比較、連鎖 3 工程以上の危険件数）と DECISIONS 追記 | 検証 | [✅2026/09/21] |

---

## タスク実行レポート

（各タスク完了時にここへ追記する）

--------------------
### タスク41〜51 実行レポート（2026/09/21、第 1 段階 補正 3）
- 契機: 目的と背景を踏まえたリスク判定のレビューで 7 件を指摘 → ユーザー「全部やって」。AskUserQuestion で 長期納期超過の基準 = LT＋安全日数 / MRP 先送り = 対象外 / 不明 = 手動発注と同じ を選択。仕様（用語 V-229/V-230、要件 F-003/F-005/F-006/F-014、design §4.1/§4.3/§5/§6.3/§9、test-design）を先に改訂
- 対象:
  - domain: `open_purchase_order.py` に `replenishment_deadline()`（V-229）、`build_replenishment_outlook(deadline, stale_after_days)`、`ReplenishmentOutlook.stale_qty`、上流 pending の納期窓。`stockout_risk.py` の危険条件を `short`（qty 0 または qty < 不足）に、直近入荷の免除を MRP に限定、MRP 先送り（通常流動品・上流納期超過なし）を対象外に、発注忘れは発注残が 1 件もないときのみ。行キー `replenishment_stale_qty`。キャッシュを (照合単位, 長期納期超過の閾値) に
  - domain: `list_client_data.py` ペイロード `replenishment.staleQty`
  - interfaces: `inventory-order-alert-list.js` 詳細の補充見込みに「補充期限より後 N」「長期納期超過 N は除外」。`list.html` キャッシュバスター `20260921-stale-overdue`
  - テスト: 発注残 21 件（D-001/002 改訂、D-007/008/009/009a 追加）、在庫切れリスク 59 件（D-035/036/041〜043 改訂、D-045〜049a・D-050a/b 追加）、ペイロード X-010、JS X-011、`test_stockout_risk_list.py` の期待値に `staleQty`
- 実装中の仕様判断: MRP 先送りを対象外にすると実データで対応要 3 区分 43 行が対象外に落ち受け入れ基準 1 に反したため、**通常流動品かつ上流納期超過なし** に限定（要件 F-005/F-014 #13、design §4.3、用語 S-204 を追随。D-048a）
- 結果: `pytest`（アプリ＋portal＋config）**1,452 passed**、`manage.py check` 問題なし、`node --check` 通過、ruff クリーン（変更ファイル。`list_client_data.py` の F401 と `test_list_client_data.py` の E402 は本補正前からの既存）
- 実データ（id 14 = 9/18、2,299 行、メモリ上で再判定・読み取りのみ）: 危険 199 → **290**、注意 1,005 → **744**、監視 995、対象外 100 → **270**。詳細は DECISIONS「追記（2026/09/21、補正 3）」
- 未対応: 注意の 592 行が JIT（直近に入荷あり）で占められる点、手動発注の危険 102 行中 59 行が直近入荷ありの妥当性、発注残の状態 1（§6.4 事項 8）。**SLIMS CSV を再取込するまで一覧は旧値**
--------------------

--------------------
### タスク33〜40 実行レポート（2026/09/18 21:30、第 1 段階 補正 2）
- 契機: レビューで仕様の曖昧さ 2 件を指摘 → AskUserQuestion で「上流の混在は 理由は両方・判定は注意」「予測グラフの需要は照合単位の合計」を選択。仕様（F-005/F-006/F-007、design §4.1a/§4.3/§6.4a）を先に改訂
- 対象:
  - domain: `ReplenishmentOutlook.upstream_pending_qty`（上流のうち納期超過でない残数。納期なしを含む）を追加。`assess_stockout_risk` の危険の除外条件を `upstream_pending_qty > 0` に、理由「上流工程に発注残あり」（pending > 0）と「上流工程で納期遅れ」（overdue）を独立に付与（従来の if/else を分離）
  - interfaces: `buildForecastStockTrend()` の需要を `demandForecast.currentMonthRemaining` / `monthly[offset-1]`（照合単位合計）に統一し、引数 `unconfirmedTrend` と呼び出し側の `getUnconfirmedOrderTrend` 渡しを削除。キャッシュバスター `20260918-unit-forecast`
  - テスト: 補充見込み 2 件（pending の集計）、在庫切れリスク 1 件（混在 → 注意・理由 2 つ）、JS ソース断言の改訂
- 結果: `pytest`（アプリ＋portal＋config）**1,431 passed**、`manage.py check` 問題なし、`node --check` 通過、ruff クリーン（変更ファイル）
- 実データ（2026/09/18、2,299 行、読み取りのみ）:
  - 危険 **199** / 注意 **1,005** / 監視 995 / 対象外 100（補正 1 直後は 207 / 997 / 995 / 100）。上流の混在（納期超過＋納期内）は 96 行、うち危険 → 注意 に下がったのは 8 行。理由が 2 つ付く行は 79 行（すべて注意）
  - 予測グラフの需要が変わる対象（2 行以上を持つ照合単位）: 2,031 単位中 149 単位・417 行。単一行の単位は変化なし
- スナップショット JSON・ペイロードのキーは不変。`upstream_pending_qty` は判定内部値で配信しない。**SLIMS CSV を再取込するまで一覧は旧値**
--------------------
--------------------
### タスク23〜32 実行レポート（2026/09/18 20:50、第 1 段階 補正）
- 契機: コードレビューで発注残の重複除去キー `(item_cd, vend_cd, due_date, remaining_qty)` が別明細を潰していることを発見。Oracle（読み取り）で状態 2・取消なし・残数 > 0 の 3,190 明細のうち **144 キー・1,059 明細（33%）・残数 771,140** が 1 件に潰れていた（例: `75X087-0007-9250` 納期 2026/03/27 × 20 個 × 50 明細 → 20 個扱い）。`PUCH_ODR_CD` は同条件の 3,192 明細で一意
- 対象:
  - docs: requirements F-001 に発注コード、design §4.1/§5.1/§6.1 を `order_cd` に改訂（コードより先）
  - domain: `open_purchase_order.py` に `OpenPurchaseOrder.order_cd`、重複除去は `order_cd`（空の旧スナップショット行は従来キー）。`stockout_risk.py` の未使用 import 削除・空 `item_cd` 行のキャッシュ共有解消・`rows_of()` はキャッシュ未登録時のみ。`app_settings.py` の関数内 import を先頭へ
  - infrastructure: `summary_queries.fetch_open_purchase_orders()` が `(order_cd, item_cd, vend_cd, due, remaining)` を返し残数 ≤ 0 を除外、生データ dict に `order_cd`
  - 07 タスク 6: `flow_quadrant_rules.py` を 7 行・`stock` / `demand` / `recent_incoming` 列に。`list.html` の判定ルール表に 在庫 / 需要 / 直近入荷 の 3 列と説明文、`app.css` の列幅（追加ファイル: 計画外だが列幅は `table-layout: fixed` のため必須）。キャッシュバスター `20260918-order-cd-legend7`（CSS のみ）
  - テスト: D-006 改訂 + D-006a/b 追加、I-001/I-002 追随、`test_build_summary_rows` 追随、`test_flow_quadrant_rules` を 7 行・TC-FQR-A-003 追加、`test_list_client_data` / `test_recommended_actions_config` / `test_inventory_order_alert_application` / `test_ioa_startup` の 4 前提・`rows[0]` 前提を解消
- 結果: `pytest`（アプリ＋portal＋config）**1,429 passed**、`manage.py check` 問題なし、`makemigrations --check` 差分なし、`node --check` 通過
- 実データ（2026/09/18、2,299 行、読み取りのみ。同じ集計結果に対し旧キーを再現して比較）:
  - 変更後 危険 **207** / 注意 **997** / 監視 995 / 対象外 **100**（変更前 207 / 999 / 995 / 98）。注意 → 対象外が 2 行。理由「数量不足」273 → 267
  - 行に付く補充見込みの合計 24,092,100 → 24,517,828（+425,728）、上流工程の発注残 15,591,751 → 15,804,675。行に付いた発注明細は 2,996 件（重複なし）
  - 判定への影響が小さいのは、潰れていた明細の多くが納期超過（2026/03 納期）で、既に「納期遅れ」で注意になっている行に集中していたため。数量は詳細ダイアログ・CSV の補充見込みに正しく出る
- 未対応（既存、今回の対象外）: `list_client_data.py` / `row_display.py` の未使用 import、`table_display.py` の E402（ruff）。**SLIMS CSV を再取込するまでスナップショットは旧値**
--------------------
--------------------
### タスク1〜19 実行レポート（2026/09/17 16:55、第 1 段階）
- 対象:
  - domain 新規: `open_purchase_order.py`（V-224/V-226）、`ordering_profile.py`（V-225/V-227）、`stockout_risk.py`（S-204、`attach_stockout_risk`）。`app_settings.py` に安全日数・既定リードタイム・監視期間（既定 14 日 / 5 日 / 6 か月）
  - infrastructure: `summary_queries.py` に `fetch_open_purchase_orders(_or_warn)`（状態 2・取消なし・残数 > 0、回答納期優先）と `fetch_item_ordering_profiles(_or_warn)`（`M_ITEM.FIXED_LT` / `MRP_ODR_TYP`、900 件ずつ）。`build_summary_rows` は行に `open_purchase_orders` / `lead_time_days` / `lead_time_source` / `ordering_method` を生データとして付ける（判定はしない）。モデル `InventoryOrderAlertSettings` に 3 列（マイグレーション 0012）、`settings_repository.py` / ports / use case に追随
  - use_cases: `ImportStock` が需要予測 → 在庫切れリスクの順に後処理を合成（設定は `load_app_settings` から。wiring で注入）。`list_page.py`（絞り込み状態）、`portal_dashboard.py`（危険・注意・監視の件数、tone は在庫切れリスク優先）、`summary_api.py`（counts に `danger` / `caution` / `watch` / `noneRisk`）
  - domain 一覧側: `table_display.py`（先頭列 `stockout_risk`、ソート専用 `days_until_stockout`、既定ソート `stockout_risk`、tiebreaker に猶予日数・流動区分）、`list_rows.py`（既定ソート・絞り込み）、`list_query.py`（`stockout_risk` / `ordering_method`）、`row_counts.py`、`row_display.py`（行クラス 確認状態 > 在庫切れリスク > 流動区分）、`list_client_data.py`、`export_csv.py`（末尾 9 列、計 37 列）、`list_filter.py`（リンクに絞り込みを引き継ぐ）
  - interfaces: `list.html`（在庫切れリスク列・フィルタ 2 つ・件数サマリ・詳細ダイアログの区分）、`dashboard.html`、両 JS、`app.css`、キャッシュバスター `20260917-stockout-risk`
  - テスト: 新規 `test_open_purchase_order.py`・`test_ordering_profile.py`・`test_stockout_risk.py`・`test_stockout_risk_list.py`・`test_open_purchase_order_query.py`、既存テストへの追加（build_summary_rows / import_stock / views / list_js / settings）
- 結果: `pytest` 全体 **2,003 passed**、`manage.py check` 問題なし、`makemigrations --check` 差分なし、`node --check` 通過
- 実データ（2026/09/17 基準、2,299 行、読み取りのみ）: 危険 **505** / 注意 697 / 監視 999 / 対象外 98。発注残 3,310 明細の取得 < 1 秒、品目マスタ 1,500 件 < 1 秒、判定 0.45 秒。詳細は DECISIONS ステージ20
- 懸念事項（**要判断**）:
  1. **通常流動品が危険 432 行**。うち 298 行は直近 30 日以内に入荷があり、272 行は在庫 0（納品直前の JIT 在庫）。発注が起票から数日で検収されるため（直近 1 か月の発注明細 19,568 件）、スナップショット時点で発注残がないのは JIT では普通。「直近に入荷がある品番は補充サイクルが動いている」とみなす条件を足さないと、危険が JIT で埋まる
  2. **発注残の状態コード**: 状態 1（1,048 明細、全件が未来納期・残数あり）を除外している（5年9組の条件に合わせた）が、実態は発行直後の発注の可能性がある。状態 1 の意味の確認が要る
  3. 危険のうち「発注忘れの可能性」（手動発注）は 91 行、「仕入先の生産可否を先に確認」は 51 行。この 2 つが本来の対象に近い
- 改善事項: 判定の入力（発注残・品目マスタ）を生データで行に持たせ、判定は domain の純関数にしたため、規則の変更（上記 1）はテストと `assess_stockout_risk` の修正だけで済む
- 設計の Good ポイント: 設定値を取込時に読むため、閾値の調整は再取込で反映され、コード変更が要らない
- チーム共有ポイント: 現行スナップショットは旧形式のため、**SLIMS CSV を再取込するまで在庫切れリスクは全行「監視」**（件数サマリは監視 N 件）
--------------------
### 画面確認による調整（2026/09/18 08:11）
- 指摘 1: 判定ルールダイアログで状況・推奨アクションの文字が隣の列に重なり、`{last_incoming}` がそのまま出ていた → 判定ルール表のセルを折り返し（`white-space: normal`）、凡例の状況は `describe_status_template()` で日付を `YYYY/MM/DD`・`{period}` を選択中の判定期間に置換（`FlowQuadrantRuleRow.status_example` / `status_text`）
- 指摘 2: 行の色がおかしい（監視なのに赤い行）→ AskUserQuestion で「在庫切れリスクだけで色を付ける」を選択。`row_alert_class` は 確認状態 > `stockout-{key}` のみを返し、流動区分は行の色に使わない。流動区分セルに色見本 `ioa-flow-swatch--{key}` を追加。requirements F-007 / design §6.4 を先に改訂
- 検証: `pytest`（アプリ＋portal＋config）1,375 件 Green、`node --check` 通過。キャッシュバスター `20260918-risk-row-color`
--------------------
### 画面確認による調整 2（2026/09/18 08:51）
- 指摘: 流動区分の色（入荷なし=赤・死蔵=橙・出荷なし=黄）は消す → 一覧セルの色見本、判定ルールダイアログの行色・色見本を撤去。流動区分は文字のみ
- 並び順: JS の同順位の並び（得意先コード → 得意先品番）がサーバ既定（猶予日数 → 流動区分 → 得意先コード → 得意先品番）と違っていたため、JS の tiebreaker をサーバに合わせた
- 検証: 1,375 件 Green。キャッシュバスター `20260918-no-quadrant-color`
--------------------
### 画面確認による調整 3（2026/09/18）
- 指摘: 9/18 の CSV で再取込しても JIT 品目（当日入荷・発注は即日検収）が危険になる。9/18 スナップショットで危険 540 行中 312 行が直近 19 日以内に入荷あり
- 対応（ユーザー選択「1 で直して」）: F-005 に「補充サイクル稼働中（最終入荷日が 基準日 − （リードタイム＋安全日数） 以降）は危険にしない」を追加し、`assess_stockout_risk` に `last_incoming_date` を渡す。理由「直近に入荷あり」を追加。発注残への状態 1 の追加は業務確認待ちで未実施
- 見込み: 危険 540 → 228（得意先 100 は 15 → 5）。**判定は取込時に保存するため、SLIMS CSV を再取込すると反映される**
- 検証: 1,380 件 Green
--------------------
### 138232-0213 の解析で見つかった課題の解消（2026/09/18）
- 課題: 発注残の突合が完成品直下の工程だけで、上流工程（誠豊電子）の未納 240 個が補充見込みにも納期遅れにも出なかった。リードタイムも直下の工程の値のみ。理由に「どの工程で止まっているか」が出ない
- 対応（要件 F-001a・F-002・F-005・F-006・F-007、design §4.1a、用語集 V-224/V-225 を先に改訂）:
  - `summary_queries.fetch_bom_chain_by_root()`（新規）: `M_PS` を `CONNECT BY NOCYCLE` で末端まで辿り、外注工程を階層順に返す。`build_summary_rows` は行に `process_chain`（階層・仕入先品番・仕入先・リードタイム）と **連鎖の全工程の発注残** を付ける。品目マスタも連鎖の全工程分を引く
  - `open_purchase_order.build_replenishment_outlook(level1_pairs=...)`: 直下の工程の発注残を補充見込み、それ以外を `upstream_qty` / `upstream_overdue` / `upstream_earliest_due` として区別
  - `stockout_risk.chain_lead_time()`: 階層ごとの最大値を足す（並列工程は同時に進む前提）。判定のリードタイムはこの値。理由「上流工程に発注残あり」（納期内 → 危険を注意に落とす）「上流工程で納期遅れ」（危険のまま）
  - 詳細ダイアログに「上流工程の発注残」と「工程の連鎖」表（階層 / 仕入先品番 / 仕入先 / リードタイム / 発注残（納期・納期超過））、CSV 末尾に `上流工程の発注残` / `上流工程の納期超過`（計 39 列）
- 実データ（9/18、読み取り）: 138232-0213 は **危険・理由「仕入先の生産可否を先に確認 / 上流工程で納期遅れ / リードタイム内 / リードタイム未設定」、連鎖 5 工程（丸栄NW → サーテック → 誠豊電子 → 豊臣熱処理 → 浅井産業）、リードタイム合計 24 日、上流工程の発注残 240（2026/06/15 納期超過）**。全体は 危険 207 / 注意 991 / 監視 995 / 対象外 106。上流工程に発注残がある行 412、うち納期超過 263。集計時間 70〜99 秒（従来と同程度）
- 検証: 1,394 件 Green、`manage.py check` 問題なし。キャッシュバスター `20260918-process-chain`
--------------------
### 推定在庫推移グラフの予測部分（2026/09/18）
- 要望: グラフに予測値を出す（内示を点線で）→ 仕様（06 F-007、design §6.4a、用語集 V-218）を先に改訂
- 実装（JS のみ、Python 変更なし）: `buildForecastStockTrend()`（現在の在庫 − 当月残の内示 − 翌月〜翌々々月の需要 ＋ 完成品直下の工程の発注残を納期の月に加算。内示がなければ月平均、需要なし・在庫未取得は描かない）、`renderAnchoredStockChart()` に 予測の点線（`stroke-dasharray`）・予定入荷の薄い棒・現在の縦線・在庫切れ予測月の縦破線とラベル・凡例 2 件を追加。横軸は 24 か月＋3 か月
- 検証: JS ソース断言 2 件追加、既存断言 2 件を新シグネチャに追随。1,396 件 Green。キャッシュバスター `20260918-forecast-line`。ブラウザ目視は未実施
--------------------
