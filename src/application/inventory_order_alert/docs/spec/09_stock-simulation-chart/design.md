# 機能設計書: 在庫推移グラフを「実績」と「在庫シミュレーション」の2つに分ける

文書ID: DES-STOCK-SIMULATION-CHART-2026-001
作成日: 2026/09/29
更新日: 2026/09/29
対応文書: [requirements.md](requirements.md)（REQ-STOCK-SIMULATION-CHART-2026-001）、[test-design.md](test-design.md)、[ubiquitous_language.md](../../ubiquitous_language.md)

---

## 1. 設計方針

1. **判定と描画で材料を共有する**。在庫切れ日（V-232）を出す `build_stock_projection` と、グラフの線が**同じ配列**を読む形にする。別々に組み立てると必ずずれる（本件の発端がそれ）
2. **重複除去はサーバで済ませる**。発注番号での重複除去・完成品直下の工程の絞り込みは domain が行い、**クライアントには除去済みの日付と数量だけを渡す**。JS には累積和しか置かない（spec/05 NF-005 の「判定ロジックを JS に持ち込まない」を守る）
3. **在庫切れ日・発注期限・安全在庫はサーバ判定値をそのまま描く**。JS で再計算しない
4. 既存の月次グラフ（V-218）は**描画関数ごと残し**、予測部分の引数を外すだけにする。日次グラフは別関数として新設する
5. Oracle への問い合わせは増やさない

## 2. ドメイン

### 2.1 stock_simulation.py（新規）— 日次の系列

```python
@dataclass(frozen=True)
class DailyMovement:
    """1 日ぶんの在庫の動き。"""
    date: date
    ship: int = 0        # 実績の出荷（過去側）
    incoming: int = 0    # 実績の入荷（過去側）
    demand: int = 0      # 内示（未来側）
    planned: int = 0     # 予定入荷（未来側）


def build_stock_simulation_input(
    unit_rows: list[dict[str, object]],
    *,
    as_of_date: date,
    past_days: int = 30,
) -> list[DailyMovement]:
    """照合単位の行から、クライアントが累積するだけで描ける日次の動きを組み立てる。

    過去側（基準日の past_days 前 〜 基準日）は 日次出荷（V-234）・日次入荷（V-235）、
    未来側（基準日の翌日 〜 内示の最終所要日 or 予定入荷の最終納期）は
    内示（V-219）・予定入荷（V-236）。重複除去はここで済ませる。
    """
```

重複除去のキーは既存の規則をそのまま使う。

| 合算するもの | キー | 既存の実装 |
|---|---|---|
| 日次出荷 | (得意先コード, 得意先品番) | `shipment_trend` と同じ |
| 日次入荷 | (仕入先品番, 仕入先コード) | `incoming_trend` と同じ |
| 内示 | (得意先コード, 内作品番) | `_daily_demand`（stock_projection.py） |
| 予定入荷 | 発注番号（`order_cd`）。完成品直下の工程のみ | `_planned_and_overdue`（同上） |

### 2.2 stock_projection.py（改修）— 同じ材料を使う

`build_stock_projection` の内部を `build_stock_simulation_input` の未来側から組み立てるよう変える。**在庫切れ日は、この系列を累積して初めて 0 未満になる日**になる（定義どおり）。

```python
def build_stock_projection(unit_rows, *, as_of_date, stock_total, default_lead_time_days=...):
    movements = build_stock_simulation_input(unit_rows, as_of_date=as_of_date, past_days=0)
    # 未来側だけを順に累積し、初めて 0 未満になった日を在庫切れ日とする
```

- **判定結果は一切変えない**。既存テスト（TC-SRR-P-001〜012）がそのまま通ることを変更の条件とする
- `_daily_demand` / `_planned_and_overdue` は `stock_simulation.py` へ移し、両者から使う

### 2.3 撤去するもの

なし。V-218 の予測部分は JS 側の描画のみで、domain には無い。

## 3. ユースケース

`ImportStock._enrich_rows` の順序は変えない（需要予測 → 流動区分 → 対応区分）。行への日次データの付与は infrastructure（集計時）で行うため、use_case に変更はない。

## 4. インフラストラクチャ

### 4.1 行に持たせるデータ（oracle/summary_queries.py）

| キー | 内容 | 増分 |
|---|---|---|
| `daily_shipment` | `[{"date": "YYYY-MM-DD", "qty": n}]`。基準日の 30 日前〜基準日。疎 | 営業日ベースで最大 ~22 件 |
| `daily_incoming` | 同上（入荷） | 同 ~22 件 |
| `planned_incoming` | `[{"date": "YYYY-MM-DD", "qty": n}]`。**発注番号で重複除去済み・完成品直下の工程のみ・納期 > 基準日** | 数件 |

- `daily_shipment` は `group_shipments_by_pair(all_shipments)` の結果を、月次に束ねるのと**同じ入力**から日次で束ねる
- `daily_incoming` は `incoming_by_pair`（`fetch_incoming_receipts` の結果）から同様
- **Oracle への追加問い合わせはゼロ**（REQ-SSC-NF-001）
- `planned_incoming` は `open_purchase_orders`（既に行が持つ生データ）から `_planned_and_overdue` と同じ規則で作る

```python
PAST_DAYS_FOR_SIMULATION = 30

def build_daily_series(lines: list[tuple[date, int]], *, as_of_date: date, past_days: int) -> list[dict]:
    """日ごとに合算した疎な配列。基準日の past_days 前 〜 基準日 の範囲のみ。"""
```

### 4.2 既存キーの扱い

`shipment_trend` / `incoming_trend`（月次 24 件）は **V-218 のためにそのまま残す**。

## 5. インターフェース

### 5.1 配信ペイロード（list_client_data.py）

| キー | 内容 |
|---|---|
| `dailyShipment` / `dailyIncoming` | 行の同名キーをそのまま |
| `plannedIncoming` | 同上 |
| `unconfirmedOrderDaily` | 既存の `unconfirmed_order_daily`（現在は未配信のため追加） |
| `stockoutDate` / `orderDeadline` / `safetyStock` / `overdueOrderQty` | 既存（`responseClass` 系で配信済み） |

`getResponseClass()` に `simulation` を足し、上記をまとめて返す。

### 5.2 テンプレート（list.html）

「推定在庫推移（参考値）と入荷実績」区分を 2 つに分ける。

```
<section class="ioa-detail-anchored-stock-trend-section">   ← 既存。予測を描かない
  <h4>在庫推移（実績）</h4>
  ...
</section>
<section class="ioa-detail-stock-simulation-section">        ← 新規
  <h4>在庫シミュレーション</h4>
  <div class="ioa-detail-stock-simulation-chart"></div>
  <p class="ioa-detail-stock-simulation-empty" hidden>…</p>
  <p class="ioa-detail-stock-simulation-note muted"></p>     ← 在庫切れ日・発注期限・安全在庫の注記
</section>
```

5年9組リンクは「在庫推移（実績）」側に残す。

### 5.3 JS

| 関数 | 変更 |
|---|---|
| `buildForecastStockTrend` | **撤去**（V-218 の予測部分） |
| `renderAnchoredStockChart` | 引数から `forecastSeries` / `stockoutMonth` を外す。`drawPlannedBars` / `drawStockoutMarker` を削除 |
| `buildStockSimulation`（新規） | 起点 ＋ `dailyShipment` / `dailyIncoming` / `unconfirmedOrderDaily` / `plannedIncoming` から日次の配列を作る。**累積和のみ** |
| `renderStockSimulationChart`（新規） | 日付軸の折れ線 ＋ 棒（予定入荷・納期遅れ）＋ 縦線（在庫切れ日・発注期限）＋ 水平線（安全在庫） |

```js
// 累積するだけ。重複除去・絞り込みはサーバ側で済んでいる
function buildStockSimulation(anchorQty, asOfDate, daily) {
  // 過去: 基準日から遡って  前日 = 当日 + 出荷 − 入荷
  // 未来: 基準日から進んで  当日 = 前日 − 内示 + 予定入荷
}
```

### 5.4 描画の仕様

| 要素 | 描き方 |
|---|---|
| 折れ線（過去側） | 実線。基準日まで |
| 折れ線（未来側） | 点線。基準日から |
| 基準日 | 縦の実線＋「取込日」ラベル |
| 予定入荷 | 納期の日に棒（薄い青） |
| 納期遅れの発注残 | 基準日の位置に棒（赤系）。**線には加算しない** |
| 在庫切れ日（V-232） | 縦の破線（赤）＋ラベル |
| 発注期限（V-233） | 縦の破線（橙）＋ラベル |
| 安全在庫（V-231） | 水平の破線（灰）＋ラベル。0 なら描かない |
| ゼロ基準線 | 既存と同じ |

横軸は**日付**。ラベルは月初とおおよそ 2 週間おきに間引く。

## 6. 影響ファイル

| レイヤー | ファイル | 変更 |
|---|---|---|
| domain | `stock_simulation.py`（新規） | 日次の動きの組み立て |
| domain | `stock_projection.py` | 上を使うよう改修（判定結果は不変） |
| infrastructure | `oracle/summary_queries.py` | `daily_shipment` / `daily_incoming` / `planned_incoming` を行へ |
| domain | `list_client_data.py` | 配信キーの追加 |
| interfaces | `templates/inventory_order_alert/list.html` | 区分を 2 つに |
| interfaces | `static/js/inventory-order-alert-list.js` | 予測の撤去・日次グラフの新設 |
| interfaces | `static/js/inventory-order-alert-list-client.js` | `getResponseClass` に `simulation` を追加 |
| interfaces | `static/css/app.css` | 日次グラフのスタイル |

## 7. エラーハンドリング

| 状況 | 挙動 |
|---|---|
| 在庫が未取得 | 在庫シミュレーションを描かず「在庫シミュレーションを算出できません（SLIMS 在庫が未取得です）。」 |
| `dailyShipment` / `dailyIncoming` が無い（旧スナップショット） | 過去側を描かず、基準日から右だけを描く。注記に「取込し直すと取込日より前も表示されます」 |
| 内示が 1 件もない | 基準日より後は水平線。縦線は描かない |
| 日付の解析に失敗 | その点を捨てる。例外にしない |
