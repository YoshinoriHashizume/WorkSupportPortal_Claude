# タスク一覧: 流動区分の 7 分類化

文書ID: TSK-FLOW-QUADRANT-REFINEMENT-2026-001
作成日: 2026/09/18
更新日: 2026/09/21（第 1 段階・第 2 段階とも全タスク完了。期間判断の基準を判定期間に一本化する改訂を含む）
対応文書: [requirements.md](requirements.md)、[design.md](design.md)、[test-design.md](test-design.md)

TDD（Red → Green → Refactor）。各タスクで既存テストの期待値も更新する。

## 第 1 段階（既定閾値・表示・判定）

| # | タスク | 対象 | 状態 |
|---|---|---|---|
| 1 | 用語集 S-203/T-205/T-206/T-209/T-210/V-220 改訂 | ubiquitous_language.md | ✅ |
| 2 | 07 要件・設計・テスト設計・タスク | docs/spec/07 | ✅ |
| 3 | flow_quadrant: 7 区分・ランク・FlowThresholds・is_recent_incoming・resolve 拡張 | flow_quadrant.py + test_flow_quadrant.py | ✅ 2026/09/18（`demand_window_months` の撤去は 7b） |
| 4 | flow_facts: 行 → 判定材料・理由 | flow_facts.py（新規）+ test_flow_facts.py | ✅ 2026/09/21（「入荷 < 需要」の比較対象をユーザー選択で確定し requirements/design/test-design を先に改訂） |
| 5 | recommended_action: 7 件・`{recent_days}` | recommended_action.py + tests | ✅ 2026/09/18（`{demand_window}` の撤去は 7c） |
| 6 | flow_quadrant_rules: 7 行・条件列 | flow_quadrant_rules.py + test_flow_quadrant_rules.py | ✅ 2026/09/18（06 補正と同時。TC-FQR-A-003） |
| 7 | demand_forecast: **実績ベースの削除（内示のみ）**。`BASIS_ACTUAL`・`ACTUAL_BASIS_MONTHS`・出荷推移フォールバックを削除（TC-FQR-D-001〜004） | demand_forecast.py + test_demand_forecast.py | ✅ 2026/09/21 |
| 7a | 07 仕様の改訂（用語集 V-220/S-203/T-209/T-210/T-207/V-218/V-222/V-223、requirements F-001/F-002/F-005/F-008、design、test-design、本書） | docs | ✅ 2026/09/18 |
| 7b | flow_quadrant: `FlowThresholds.demand_window_months`・`DEFAULT/MIN/MAX_DEMAND_WINDOW_MONTHS` を削除（TC-FQR-Q-010） | flow_quadrant.py + test_flow_quadrant.py | ✅ 2026/09/21 |
| 7c | recommended_action: `PLACEHOLDER_DEMAND_WINDOW`・`demand_window_months` 引数を削除、打ち切り候補の状況を「在庫なし・内示なし（最終出荷 {last_ship}）」に（TC-FQR-A-002） | recommended_action.py + test_recommended_action.py / test_flow_quadrant_rules.py | ✅ 2026/09/21 |
| 7e | 欠品（入荷即出荷）→ **欠品** 改名: `QUADRANT_STOCKOUT`・キー `stockout`・状況文言・`LEGACY_QUADRANT_ALIASES` 追加（TC-FQR-Q-008）。rules / recommended_action / list_client_data のテスト追随 | flow_quadrant.py, recommended_action.py, flow_quadrant_rules.py + tests | ✅ 2026/09/21（状況文言も「在庫なし・入荷はあるが在庫が残らない」に統一） |
| 7f | **2026/09/21 追加**: 仕様改訂 — 在庫切れ予測月（V-221）の「在庫 0 以下は当月」を廃止し「累積需要が初めて負になる月」に一本化（用語集 V-221、07 requirements F-002/F-004、design §2.5/§2.6、test-design）。06 補正 3 とのすり合わせ（補充サイクル免除 = 在庫あり かつ MRP、MRP 先送り = 在庫ありのみ、欠品の危険は猶予日数を使う） | docs | ✅ 2026/09/21 |
| 7g | demand_forecast: `stockout_forecast_month` の在庫 0 ショートカット削除（TC-FQR-D-005/006） | demand_forecast.py + test_demand_forecast.py | ✅ 2026/09/21 |
| 7h | 07 tasks.md 本表の更新（着手前に書き出し） | 本書 | ✅ 2026/09/21 |
| 7d | stockout_risk: `REASON_ACTUAL_BASIS`・`BASIS_ACTUAL` 分岐を削除、`_forecast_of` で旧値「実績ベース」を NO_DEMAND に（TC-FQR-R-007/008）。test_import_stock_usecase の実績ベース期待値を更新 | stockout_risk.py + tests | ✅ 2026/09/21 |
| 8 | list_rows: facts・理由の付与、並び | list_rows.py + test_list_rows.py | ✅ 2026/09/21（`thresholds` 引数・`flow_reasons` 付与。TC-FQR-L-001〜005） |
| 9 | stockout_risk: 在庫なし分岐・理由・attach で stock_missing | stockout_risk.py + test_stockout_risk.py / test_stockout_risk_list.py | ✅ 2026/09/21（TC-FQR-R-001〜006） |
| 10 | import_stock: 需要予測 → 流動区分 → 在庫切れリスク | import_stock.py + test_import_stock_usecase.py | ✅ 2026/09/21（TC-FQR-I-001） |
| 11 | row_counts / list_client_data / export_csv / summary_api / portal_dashboard | 各 + tests | ✅ 2026/09/21（`attention` = 通常流動品以外に明確化、API キーは `stockout`。TC-FQR-C-001〜005） |
| 12 | summary_queries: 適用終了日（phase_out_date） | summary_queries.py + test_build_summary_rows.py | ✅ 2026/09/21（`fetch_cust_item_phase_out_dates(_or_warn)`。TC-FQR-I-002） |
| 13 | list.html / JS / CSS: 7 区分・ルールダイアログ列・理由表示・フィルタ。list.js の予測部分を basis「内示」のみに（TC-FQR-C-007） | templates, static + views/js tests | ✅ 2026/09/21（`FLOW_QUADRANT_RANK` 7 キー・`getFlowReasons`・詳細ダイアログの理由・区分バッジ CSS・予測は内示のみ） |
| 14 | recommended_actions.example.json 7 キー・旧識別子走査 | config + tests | ✅ 2026/09/21（見本を 7 キーに。走査に 07 の旧識別子 14 語を追加。TC-FQR-A-004 / TC-FQR-C-007） |
| 15 | 全テスト実行・実データで受け入れ基準 §8 を確認し結果を記録 | scratchpad | ✅ 2026/09/21（下記「実データ確認の記録」。基準 2 のみ前提不一致で要判断） |

## 第 2 段階（設定）

| # | タスク | 対象 | 状態 |
|---|---|---|---|
| 16 | AppSettings に recent_incoming_days（`demand_window_months` は設けない）、設定画面、取込・表示で使用 | app_settings.py, settings 画面, list_page.py, wiring.py, migration | ✅ 2026/09/21（既定 30・範囲 1〜90・`to_flow_thresholds()`・payload `recentIncomingDays`。旧残置カラム `recent_incoming_days`（既定 90）を再利用し 0013 で既定値と既存行を 30 に移行。取込・一覧・メニュー帯の 3 経路で使用） |
| 17 | 機能仕様書 rev 6.0（05/06/07 の反映） | docs/在庫発注アラート_機能仕様書.md | ✅ 2026/09/21（版番号は spec 番号に合わせ **6.0（06 の反映）と 7.0（07 の反映）の 2 版**として記録。05 は 5.0〜5.2 で反映済み） |

## 実データ確認の記録

### 2026/09/21 実施（第 1 段階の完了確認）

- 対象: 2026/09/18 取込のスナップショット（id=14、基準日 2026-09-18、2,299 行）に取込パイプライン
  （需要予測 → 流動区分の引き直し → 在庫切れリスク）を適用して集計
- 自動テスト: プロジェクト全体 **2,157 passed**（在庫発注アラート 1,072 件を含む）

**流動区分（判定期間 1 年）**

| 区分 | 件数 |
|---|---|
| 欠品（入荷なし） | 69 |
| 欠品 | 182 |
| 低流動品（入荷なし） | 270 |
| 在庫死蔵品 | 320 |
| 低流動品（出荷なし） | 77 |
| 打ち切り候補 | 427 |
| 通常流動品 | 954 |

**需要予測の算出根拠**: 内示 1,343 / なし 956（改訂前は 内示 1,343 / 実績ベース 425 / なし 531。実績ベースの 425 行がすべて「なし」へ）

**在庫切れリスク**: 危険 233 / 注意 602 / 監視 1,233 / 対象外 231

**流動区分の理由（判定期間ごと。2026/09/21 の基準統一後）**

| 判定期間 | 入荷 < 需要 | 内示あり（立ち上がり／出荷経路要確認） | {期間}以上出荷なし・経路要確認 | 入荷の記録なし・経路要確認 |
|---|---|---|---|---|
| 1年 | 123 | 60 | 25 | 3 |
| 3年 | 123 | 30 | 6 | 3 |
| 5年 | 123 | 0 | 0 | 3 |

（適用終了日はスナップショットに `phase_out_date` がないため 0。次回の取込から付く）

**受け入れ基準（§8）の結果**

| # | 結果 | 実測 |
|---|---|---|
| 1 | ✅ | SLIMS 在庫なし 678 行がすべて 欠品（入荷なし） 69 / 欠品 182 / 打ち切り候補 427 に振り分き、4 区分に残った行は **0**（母数は測定時の 693 と異なり、スナップショット差） |
| 2 | ✅（2026/09/21 再確認） | 旧記述では「出荷の記録なし（最終出荷日が空）」を条件としていたが、**スナップショット全 2,299 行のうち最終出荷日が空の行は 0 件**（一覧は出荷実績のある行から組み立てるため構造上存在しない。要件 §1.2 と整合）で理由が一度も出なかった。**期間判断を判定期間に一本化する改訂**（用語集 V-211）に伴い条件を「期間内出荷なし」・対象を欠品 2 区分に改め、再確認: 313 234056-8000-JP は 欠品（入荷なし）・判定期間 1 年で理由「1年以上出荷なし・経路要確認」が付き、3 年・5 年では消える |
| 2b | ✅ | 欠品 2 区分 251 行のうち本理由が付くのは 1 年 25 行 / 3 年 6 行 / 5 年 0 行。理由の出現数（1 年）は 入荷 < 需要 123 / 内示あり 60 / 1年以上出荷なし 25 / 入荷の記録なし 3。判定期間で理由が変わる行は 91 行あり、3 期間ぶん保持しないと期間切替で古い理由が残る |
| 3 | ✅ | 406 9089-10115B = 打ち切り候補・監視 |
| 3b | ✅ | 在庫なし・内示なし 427 行はすべて 打ち切り候補・監視。在庫あり・内示なし・出荷ありの 529 行はすべて 監視 |
| 4 | ✅ | 195 138232-0213（在庫 5・内示あり・最終入荷 2025/01/13）= 低流動品（入荷なし）・危険 |
| 5 | ✅ | 判定期間で値が変わる在庫なし行 **0** |
| 6 | ✅ | 在庫数キーのない旧行 50 件は 低流動品（入荷なし）のみで、欠品・打ち切り候補は出ない |
| 7 | ✅ | 旧称・旧キーは `LEGACY_QUADRANT_ALIASES` で正規化（TC-FQR-Q-008・単体テスト） |
| 8 | ✅ | 191 062616-0160 = 欠品・在庫切れ予測月 2026-11・猶予 44 日・**注意**・理由「在庫なし」「供給遅延（入荷即出荷）」 |
| 9 | ✅ | 在庫なし・当月残の内示あり・発注残なしの 29 行はすべて 猶予 0・**危険** |

**欠品 2 区分の在庫切れリスク**: 危険 151 / 注意 100（打ち切り候補は全件 監視、通常流動品に監視以下が集まる形になり、目的 3 を満たす）
