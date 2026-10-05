# 機能設計書: 詳細ダイアログを「在庫が切れるか」を軸に整理する

文書ID: DES-DETAIL-DIALOG-CLEANUP-2026-001
作成日: 2026/09/30
更新日: 2026/09/30
対応文書: [requirements.md](requirements.md)、[test-design.md](test-design.md)、[ubiquitous_language.md](../../ubiquitous_language.md)

---

## 1. 設計方針

1. **文言は domain に置く**。見出し・次にすることは対応区分（S-204）から決まる業務文言なので、判定と同じ層に置く（REQ-DDC-NF-003）。JS は受け取った文字列を差し込むだけ
2. **判定は 1 行も触らない**。読み替えるだけ。既存テストが全件そのまま通ることを改修の条件にする
3. **配信データを増やさない**。判定サマリは既に配信済みの値（`responseClass` / `stockoutDate` / `orderDeadline` / `responseReasons` / `safetyStock` / `overdueOrderQty`）から作る
4. 区分の並べ替えはテンプレートの順序変更で行い、JS の描画関数は流用する

## 2. ドメイン

### 2.1 assessment_summary.py（新規）

```python
@dataclass(frozen=True)
class AssessmentSummary:
    """判定サマリ（T-211）。対応区分から読み替えるだけで、新しい判定はしない。"""
    headline: str          # 「この品番は 2026/10/10 に在庫が切れます。2026/10/05 までに発注が必要です」
    response_class: str    # 対応区分（S-204）
    next_action: str       # 次にすること
    deadline_text: str     # 「2026/10/05（あと 5 日）」／在庫切れ日がなければ空
    reasons: tuple[str, ...]


#: 対応区分ごとの「次にすること」（T-211）。流動区分由来の推奨アクション（T-207）とは別。
NEXT_ACTIONS = {
    RESPONSE_ORDER_OVERDUE: "生産管理: 至急手配し、客先へ納期を調整する",
    RESPONSE_DELIVERY_CHECK: "購買: 仕入先へ納期を確認する",
    RESPONSE_ORDER_NEEDED: "生産管理: 発注期限までに発注する",
    RESPONSE_WATCH: "生産管理: 様子を見る",
    RESPONSE_NONE: "対応不要",
}


def build_assessment_summary(row, *, as_of_date) -> AssessmentSummary:
    """行の判定値から判定サマリを組み立てる。例外は投げない。"""
```

見出しの分岐は用語集 T-211 の表をそのまま実装する。

| 対応区分 | 見出し |
|---|---|
| 発注遅れ | `この品番は {在庫切れ日} に在庫が切れます。発注期限 {発注期限} は過ぎています` |
| 要発注 | `この品番は {在庫切れ日} に在庫が切れます。{発注期限} までに発注が必要です` |
| 納期確認（在庫切れ日あり） | `この品番は {在庫切れ日} に在庫が切れます。{発注期限} までに発注が必要です。あわせて納期遅れの発注残 {件数} 件 {数量} 個の納期を確認してください` |
| 納期確認（在庫切れ日なし） | `在庫は足ります。ただし納期遅れの発注残が {件数} 件 {数量} 個あります` |
| 要監視 | `在庫は切れませんが、安全在庫 {安全在庫} を下回ります` |
| 対象外 | `在庫は切れません` |

- 在庫切れ日が空なのに区分が 発注遅れ / 要発注 になることはない（S-204 の定義上）。もし起きたら「在庫は切れません」に倒す（安全側）
- 残り日数は `在庫切れ日 − 基準日`。当日は「本日」、過去は「{n} 日超過」
- **納期確認だけは在庫切れ日の有無で文が変わる**（2026-09-30 修正）。S-204 のマトリクスは「在庫の見通しが切れる かつ 納期遅れの発注残あり」も納期確認にするため、一律「在庫は足ります」とすると事実と逆になる（実データ 271 行中 216 行が該当していた）

### 2.2 変更しないもの

`stockout_risk.py` / `stock_projection.py` / `stock_simulation.py` / `flow_quadrant.py` は**一切変更しない**。

## 3. インターフェース

### 3.1 配信ペイロード（list_client_data.py）

`getResponseClass()` が返す値に `summary` を足す。**新しい行データは増やさない**（既存キーから domain が組み立てる）。

```python
client_row["assessmentSummary"] = {
    "headline": summary.headline,
    "nextAction": summary.next_action,
    "deadlineText": summary.deadline_text,
    "reasons": list(summary.reasons),
}
```

### 3.2 テンプレート（list.html）

区分を並べ替え、統合する。

| 順 | class | 見出し | 中身 |
|---|---|---|---|
| 1 | `ioa-detail-assessment-section`（新規） | （見出し文そのもの） | 対応区分 / 発注期限 / 次にすること / そう判断した理由 |
| 2 | `ioa-detail-stock-simulation-section` | 在庫シミュレーション | グラフのみ。**在庫切れ日・発注期限を繰り返す注記は置かない**（判定サマリと重複するため。2026-09-30 改訂）。取込し直しの案内だけ残す |
| 3 | `ioa-detail-reference-section`（新規の入れ物） | **品番情報** | 下表のとおり |
| 4 | `ioa-detail-memo-section` | メモ | 現状のまま |

**2026-09-30 改訂 (1)**: 「在庫と発注残」を独立区分にせず、参考の中の先頭へ入れて **4 区分**にした（ユーザー判断）。
`ioa-detail-stock-section` は class をそのまま保ち、置き場所だけ参考の中へ移す（JS の参照を変えずに済む）。

**2026-09-30 改訂 (2)**: 見出しを「参考」→「品番情報」に改称し、流動区分の区分を撤去した（REQ-DDC-F-008）。品番情報の中は次の 3 段にする。

| 段 | 要素 | 中身 |
|---|---|---|
| 1 | `ioa-detail-columns` の 2 列 | 左 `ioa-detail-item-section`（品目）／右 `ioa-detail-stock-fields-section`（**新規**・在庫と発注残の `<dl>` ＋ `ioa-detail-demand-monthly`） |
| 2 | `ioa-detail-stock-section` | 在庫内訳(SLIMS) ＋ 工程の連鎖（`<dl>` は 1 段目へ移したので、ここは表と連鎖だけになる） |
| 3 | `ioa-detail-anchored-stock-trend-section` | 在庫推移（実績・月次）＋ 5年9組へのリンク |

`ioa-detail-stock-fields-section` は流動区分があった格子の位置をそのまま使う（CSS は `.ioa-detail-flow-section` のセレクタを改名するだけ）。

**2026-10-05 改訂 (3)**: 品目マスタ由来の 3 項目を 1 段目の**左（品目）**へ移した（REQ-DDC-F-009）。`<dl>` の中身は次のとおり。

| `<dl>` | 項目（この順） |
|---|---|
| 左・品目 | 得意先 / 得意先品番 / 仕入先 / 仕入先品番 / **リードタイム**（`ioa-detail-stockout-lead-time`）/ **発注方式**（`ioa-detail-stockout-ordering-method`）/ **安全在庫**（`ioa-detail-safety-stock`）/ 最終入荷日 / 最終出荷日 |
| 右・在庫と発注残 | 在庫数(SLIMS) / 在庫数(MARI) / 届く予定 / 納期遅れ / 客先の出荷予定（月別） |

**class 名を変えないため JS・CSS の変更はない**（`detailFields` / `riskFields` は class で引いており、`<dl>` をまたいでも同じ要素に当たる）。

**撤去**: `ioa-detail-demand-forecast-section`（区分ごと）、`ioa-detail-response-class-section`（判定サマリと「在庫と発注残」へ吸収）、
`ioa-detail-flow-section`（**区分ごと** — `ioa-detail-flow-quadrant` / `ioa-detail-flow-status` / `ioa-detail-flow-reasons` / `ioa-detail-evaluation-period` / `ioa-detail-recommended-action` / `ioa-detail-department`）。

### 3.3 JS

| 関数 | 変更 |
|---|---|
| `renderResponseClass` | → `renderAssessment` に改称。見出し・次にすること・期限・理由を**差し込むだけ**にする |
| `renderStockSimulationChart` の注記 | 在庫切れ日・発注期限・納期遅れ・安全在庫の繰り返しをやめ、**取込し直しの案内だけ**にする（2026-09-30） |
| `renderDemandForecast` | **撤去**（月別内示は `renderMonthlyDemand` として「在庫と発注残」へ） |
| `renderFlowReasons` | **撤去**（REQ-DDC-F-008。`getFlowStatus` / `getRecommendedAction` / `getEvaluationPeriodLabel` も詳細ダイアログからは呼ばない。一覧が使う `flowQuadrantDepartments` 等の対応表は残す） |
| `detailFields` | 流動区分の 4 項目を外し、`cust` / `itemCd` / `vend` / `level1ItemCd` / `lastIncoming` / `lastShip` / `stockSlims` / `stockMari` だけにする |
| `renderProcessChain` | 「在庫と発注残」区分へ移動（関数はそのまま） |
| `fillDetailSections` | 呼び出しの並びを新しい区分に合わせる |

文言は**サーバから受け取った文字列をそのまま入れる**。JS 内に「在庫が切れます」等の文言を書かない。

## 4. 影響ファイル

| レイヤー | ファイル | 変更 |
|---|---|---|
| domain | `assessment_summary.py`（新規） | 判定サマリの組み立て |
| domain | `list_client_data.py` | `assessmentSummary` の配信 |
| interfaces | `templates/inventory_order_alert/list.html` | 区分の再編 |
| interfaces | `static/js/inventory-order-alert-list.js` | 描画の差し替え |
| interfaces | `static/js/inventory-order-alert-list-client.js` | `summary` の受け渡し |
| interfaces | `static/css/app.css` | 判定サマリのスタイル |
| interfaces | `templates`（キャッシュバスター） | `?v=` を上げる |

## 5. エラーハンドリング

| 状況 | 挙動 |
|---|---|
| `response_class` が無い旧行 | 対象外として「在庫は切れません」 |
| 在庫切れ日が空なのに 発注遅れ / 要発注 | 「在庫は切れません」に倒す（安全側） |
| 理由が空 | 「そう判断した理由」の行ごと隠す |
| 日付が解析できない | 残り日数を出さず、日付文字列だけを出す |
