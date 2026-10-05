# タスク一覧: 詳細ダイアログを「在庫が切れるか」を軸に整理する

文書ID: TSK-DETAIL-DIALOG-CLEANUP-2026-001
作成日: 2026/09/30
更新日: 2026/09/30
対応文書: [requirements.md](requirements.md)、[design.md](design.md)、[test-design.md](test-design.md)

TDD（Red → Green）。既存テストの期待値も同じタスクで更新する。

| # | タスク | 対象 | 状態 |
|---|---|---|---|
| 1 | 用語集: T-211 判定サマリ を新設、V-220〜V-222 に「詳細ダイアログから撤去」の印 | ubiquitous_language.md | ✅ 2026/09/30 |
| 2 | 10 要件・設計・テスト設計・タスク | docs/spec/10 | ✅ 2026/09/30 |
| 3 | assessment_summary: 見出し・次にすること・期限（TC-DDC-S-001〜014） | assessment_summary.py（新規）+ test_assessment_summary.py | ✅ 2026/09/30 |
| 4 | 判定が変わらないことの確認（TC-DDC-C-001〜003） | 既存テストの実行 | ✅ 2026/09/30 |
| 5 | list_client_data: `assessmentSummary` の配信（TC-DDC-P-001〜003） | list_client_data.py + test_list_client_data.py | ✅ 2026/09/30 |
| 6 | list.html: 区分の再編（判定サマリ / 在庫と発注残 / 参考）（TC-DDC-X-001〜005） | templates + test_inventory_order_alert_views.py | ✅ 2026/09/30 |
| 7 | JS: `renderAssessment` 新設・`renderDemandForecast` 撤去・並びの差し替え（TC-DDC-J-001〜004） | inventory-order-alert-list.js + test | ✅ 2026/09/30 |
| 8 | list-client.js: `summary` の受け渡し | inventory-order-alert-list-client.js + test | ✅ 2026/09/30 |
| 9 | CSS: 判定サマリのスタイル | app.css + test | ✅ 2026/09/30 |
| 10 | キャッシュバスターを上げる（TC-DDC-X-007） | base.html / list.html + test | ✅ 2026/09/30 |
| 11 | 機能仕様書 rev 10.0・テスト仕様書の追随 | docs | ✅ 2026/09/30 |
| 12 | 全テスト実行・実データで受け入れ基準を確認し記録（TC-DDC-R-001/002） | scratchpad | ✅ 2026/09/30 |
| 13 | 在庫シミュレーション下の注記（在庫切れ日 / 発注期限）を撤去、在庫と発注残を参考の中へ統合（TC-DDC-X-001） | list.html / JS / CSS + test | ✅ 2026/09/30 |
| 14 | REQ-DDC-F-008: 流動区分の区分を撤去、参考 → 品番情報 に改称、在庫と発注残を品目の右隣へ（TC-DDC-X-008/009・TC-DDC-J-005） | list.html / JS / CSS / 用語集 / docs + test | ✅ 2026/09/30 |
| 15 | REQ-DDC-F-009: 安全在庫・リードタイム・発注方式を「品目」へ移す（TC-DDC-X-010/011） | list.html / docs + test | ✅ 2026/10/05 |

## 依存関係

```
3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15
```

タスク 4 で「判定が 1 件も変わっていない」ことを確認してから表示の再編に入る。

## 実データ確認の記録

（タスク 12。2026/09/30。snapshot id=17 / 基準日 2026-09-30 / 2,299 行。`src/tmp/verify_assessment.py`）

### TC-DDC-R-001: 見出しと対応区分の整合

| 項目 | 結果 |
|---|---|
| 行 | 2,299 |
| **矛盾** | **0 件** |

### TC-DDC-R-002: 対応区分の件数（判定は不変）

| 対応区分 | 件数 |
|---|---:|
| 発注遅れ | 177 |
| 納期確認 | 271 |
| 要発注 | 525 |
| 要監視 | 83 |
| 対象外 | 1,243 |

対応区分・在庫切れ日・発注期限・流動区分の既存テストは全件そのまま通過（REQ-DDC-NF-001）。

### 実装中に見つけて直した誤り

**納期確認の見出しが 271 行中 216 行で事実と逆だった。**

当初 納期確認 を一律「在庫は足ります。ただし納期遅れの発注残が…」としていたが、S-204 のマトリクスでは
**「切れる かつ 納期遅れあり」も納期確認**になる。実データでは 納期確認 271 行のうち **216 行（80%）に在庫切れ日があり**、
「在庫は足ります」と表示しながら理由には「在庫切れ 2026/10/05」と書かれる状態だった。

在庫切れ日の有無で文を分けるよう、用語集 T-211・design・実装・テストを修正した。修正後の見出しの内訳:

| 見出しの型 | 件数 |
|---|---:|
| 切れる | 918 |
| 切れない | 1,243 |
| 安全在庫割れ | 83 |
| 納期遅れのみ | 55 |

「切れる」が 702 → **918 件**になり、隠れていた 216 件が正しく現れた。

### 全テスト

`application/inventory_order_alert` + `config` で **1,334 件 全件成功**。

## タスク 14（REQ-DDC-F-008）の確認記録

2026/09/30。snapshot id=19 / 基準日 2026-09-30 / 2,299 行。`src/tmp/verify_detail_dialog.py`（読み取りのみ）。

### TC-DDC-X-008: 詳細ダイアログからの撤去

| 対象 | 結果 |
|---|---|
| `ioa-detail-flow-section` / `-flow-quadrant` / `-flow-status` / `-flow-reasons` / `-evaluation-period` / `-recommended-action` / `-department` | **全て不在** |
| `ioa-detail-demand-forecast-section` / `-response-class-section`（タスク 6・13 ぶん） | **全て不在** |
| 区分の見出し | `在庫シミュレーション` / `品番情報` / `メモ`（判定サマリは見出し文そのものが見出しなので `ioa-detail-section-title` を持たない） |

### TC-DDC-X-001: 出現順（HTML 上の位置）

判定サマリ → 在庫シミュレーション → 品番情報〈品目 → 在庫と発注残 → 在庫内訳＋工程の連鎖 → 在庫推移（実績）〉→ メモ の順で **昇順**。

### TC-DDC-X-009: 一覧が使う材料が欠けていないこと

| 配信キー | 欠け |
|---|---:|
| `flowQuadrants` / `flowQuadrantKey` | 0 件 |
| `flowReasonsByPeriod` | 0 件 |
| `assessmentSummary.headline` | 0 件 |

### 全テスト（タスク 13・14 後）

`application/inventory_order_alert` + `config` + `application/portal` で **1,660 件 全件成功**。

## タスク 15（REQ-DDC-F-009）の確認記録

2026/10/05。snapshot id=19 / 基準日 2026-09-30 / 2,299 行。`src/tmp/verify_detail_dialog.py`（読み取りのみ）。

### TC-DDC-X-010 / X-011: 置き場所と並び

| `<dl>` | レンダリング結果 |
|---|---|
| 品目 | 得意先 / 得意先品番 / 仕入先 / 仕入先品番 / **リードタイム / 発注方式 / 安全在庫** / 最終入荷日 / 最終出荷日 |
| 在庫と発注残 | 在庫数(SLIMS) / 在庫数(MARI) / 届く予定 / 納期遅れ / 客先の出荷予定（月別） |

`ioa-detail-stockout-lead-time` / `-stockout-ordering-method` / `-safety-stock` の 3 つとも
**品目=True・在庫と発注残=False**。区分の出現順（TC-DDC-X-001）は昇順のまま。

### 全テスト（タスク 15 後）

`application/inventory_order_alert` + `config` + `application/portal` で **1,660 件 全件成功**。
class 名を変えていないため JS・CSS は無変更で、既存の描画テストもそのまま通過した。

### 残った気付き（未対応・報告のみ）

- `inventory-order-alert-list-client.js` の公開 getter `getFlowStatus` / `getRecommendedAction` / `getResponsibleDepartment` / `getFlowReasons` / `getEvaluationPeriodLabel` は**呼び出し元が 0 になった**。削除は撤去範囲を越えるため行わず、コメントで経緯を残した
- `test_inventory_order_alert_list_js.py` の `test_inventory_order_alert_list_js_import_overlay_has_spinner_css` に、`def` 行を失って前のテストへ吸収された判定ルールダイアログ CSS のアサーション群が残っている（HEAD 時点から存在。アサーション自体は実行されている）
