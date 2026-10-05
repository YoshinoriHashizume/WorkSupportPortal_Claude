# タスク一覧: 在庫切れリスクを内示のみ・日次の判定に作り直す

文書ID: TSK-STOCKOUT-RISK-REWORK-2026-001
作成日: 2026/09/23
更新日: 2026/09/23
対応文書: [requirements.md](requirements.md)、[design.md](design.md)、[test-design.md](test-design.md)

TDD（Red → Green）。既存テストの期待値も同じタスクで更新する。

| # | タスク | 対象 | 状態 |
|---|---|---|---|
| 1 | 用語集: S-204 を対応区分に改称、V-231 安全在庫・V-232 在庫切れ日・V-233 発注期限を新設、撤去する用語に印 | ubiquitous_language.md | ✅ 2026/09/23 |
| 2 | 08 要件・設計・テスト設計・タスク | docs/spec/08 | ✅ 2026/09/23 |
| 3 | stock_projection: 日次の見通し（TC-SRR-P-001〜012） | stock_projection.py（新規）+ test_stock_projection.py | ✅ 2026/09/23 |
| 4 | stockout_risk: 対応区分・理由（TC-SRR-R-*, N-*） | stockout_risk.py + test_stockout_risk.py | ✅ 2026/09/23 |
| 5 | attach: 行への付与・旧キー撤去（TC-SRR-A-*） | stockout_risk.py + test_stockout_risk_list.py | ✅ 2026/09/23 |
| 6 | app_settings: safety_days / watch_months 撤去 | app_settings.py, settings_repository.py, models.py, ports.py, マイグレーション 0014 + tests | ✅ 2026/09/23 |
| 7 | open_purchase_order: 補充見込み系の撤去 | open_purchase_order.py + tests | ✅ 2026/09/23 |
| 8 | summary_queries: 安全在庫・日次内示（TC-SRR-I-001〜003） | summary_queries.py + test_build_summary_rows.py | ✅ 2026/09/23 |
| 9 | row_counts / list_client_data / row_display: 5 区分 | 各 + tests | ✅ 2026/09/23 |
| 10 | table_display / list_query / list_rows / list_filter: 列追加・並び・フィルタ（TC-SRR-C-002/003/005） | 各 + tests | ✅ 2026/09/23 |
| 11 | export_csv: 対応区分系 9 列（TC-SRR-C-004） | export_csv.py + test_export_csv.py | ✅ 2026/09/23 |
| 12 | summary_api / portal_dashboard / save_confirmation / reset_confirmations: 件数キー・帯 | 各 + tests | ✅ 2026/09/23 |
| 13 | list.html / dashboard.html / JS / CSS: 列・色・フィルタ・詳細ダイアログ | templates, static + tests | ✅ 2026/09/23 |
| 14 | 旧識別子の走査に新しい撤去語を追加（TC-SRR-C-009） | test_legacy_alert_identifiers_removed.py | ✅ 2026/09/23 |
| 15 | 機能仕様書 rev 8.0・テスト仕様書 rev 3.0 の追随 | docs | ✅ 2026/09/23 |
| 16 | 全テスト実行・実データで受け入れ基準を確認し結果を記録 | scratchpad | ✅ 2026/09/23 |

## 実データ確認の記録

（タスク 16。2026/09/23）

- **全テスト**: `application/inventory_order_alert` + `config` で **1,259 件 全件成功**
- **実データ**: 基準日 2026/09/23 で Oracle から集計しなおし、取込と同じ後処理（需要予測 → 流動区分 → 対応区分）を通して計測した（`src/tmp/verify_response_class.py`。DB への書き込みなし）。集計 2,299 行 / 照合単位 2,031 / SLIMS 在庫のある得意先品番 1,618 行

| 対応区分 | 行数 | 照合単位 |
|---|---:|---:|
| 発注遅れ | 145 | 143 |
| 納期確認 | 272 | 183 |
| 要発注 | 572 | 504 |
| 要監視 | 89 | 75 |
| 対象外 | 1,221 | 1,126 |

受け入れ基準の確認（すべて充足）:

| # | 基準 | 結果 |
|---|---|---|
| 1 | 内示が 0 の行は在庫が動かない扱いになる | 内示なしの行で 対象外／納期確認 以外になったものは **0 件** |
| 2 | 納期遅れの発注残は在庫に加算しない | 納期確認 272 行は**すべて**納期遅れの発注残を持つ |
| 3 | 発注期限を過ぎたものが最優先になる | 発注遅れ 145 行は**すべて** 発注期限 ≤ 基準日 |
| 4 | 納期遅れを加算しないことが結果に効く | 納期遅れの発注残を持つ照合単位 **222** のうち **174 単位**で、加算した場合より在庫切れ日が早くなる（または新たに切れる） |
| 5 | 安全在庫割れを層別する | 安全在庫が設定されている照合単位 **825** のうち、在庫は尽きないが安全在庫を下回る **75 単位（89 行）** が 要監視 になった。要監視の行は**すべて**在庫切れ日が空かつ安全在庫割れ |
| 8 | 89965-X1Y00 | **要発注** / 在庫切れ 2026/12/15 / 発注期限 2026/12/11 / リードタイム 4 日（品目マスタ）/ 安全在庫 1,000 を下回る。要件定義書に書いた「リードタイム 8 日・在庫切れ 12/11」は起草時の誤りで、実際の `FIXED_LT` は 4 日（requirements.md を訂正済み） |

**注**: 設計時の試算（発注遅れ 244 / 納期確認 104 / 要発注 494 / 要監視 74 / 対象外 1,115）は 2026/09/18 取込のスナップショットに対する概算であり、上表とは基準日・データ世代が異なる。正は上表とする。
