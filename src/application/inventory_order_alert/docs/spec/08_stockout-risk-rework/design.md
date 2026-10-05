# 機能設計書: 在庫切れリスクを内示のみ・日次の判定に作り直す

文書ID: DES-STOCKOUT-RISK-REWORK-2026-001
作成日: 2026/09/23
更新日: 2026/09/23
対応文書: [requirements.md](requirements.md)（REQ-STOCKOUT-RISK-REWORK-2026-001）、[test-design.md](test-design.md)、[ubiquitous_language.md](../../ubiquitous_language.md)、[06_stockout-risk/design.md](../06_stockout-risk/design.md)

---

## 1. 設計方針

1. **日次の見通しを作る純関数を 1 つ新設**し（`stock_projection.py`）、そこに計算を閉じ込める。判定（対応区分）はその結果を読むだけにする
2. 計算に要る材料（内示の日次・安全在庫）は **行に持たせる**。infrastructure が取込時に詰め、domain は行から読む（既存の `unconfirmed_order_trend` と同じ作り）
3. 対応区分は **2 軸の組み合わせ**。実装は上から順の分岐で書くが、条件は重ならない
4. 旧 `stockout_risk.py` は**対応区分の判定に置き換える**。補充見込み（V-226）・補充期限（V-229）・長期納期超過（V-230）・猶予日数（V-228）は使わなくなるため撤去する
5. 流動区分（S-203）側は変更しない

## 2. ドメイン

### 2.1 stock_projection.py（新規）— 日次の見通し

```python
@dataclass(frozen=True)
class DailyStockProjection:
    """照合単位ごとの日次の在庫見通し（REQ-SRR-F-002/003）。"""
    has_demand: bool             # 内示が 1 件でもあるか
    stockout_date: date | None   # 初めて 0 未満になる日
    order_deadline: date | None  # 在庫切れ日 − リードタイム
    below_safety_stock: bool     # 期間内に安全在庫を下回る日があるか
    safety_stock: float          # 照合単位の安全在庫合計（0 なら未設定）
    overdue_order_qty: int       # 納期遅れの発注残の数量
    overdue_order_count: int     # 同 件数
    lead_time_days: int
    lead_time_source: str

def build_stock_projection(
    unit_rows, *, as_of_date, stock_total, settings
) -> DailyStockProjection
```

計算（REQ-SRR-F-002）:

```
在庫 = stock_total（None は 0）
日付は 基準日の翌日 〜 内示の最終所要日
  在庫 -= その日の内示
  在庫 += その日に届く予定入荷（納期 > 基準日 の発注残）
  初めて 在庫 < 0 になった日を stockout_date
  safety_stock > 0 かつ 在庫 < safety_stock の日があれば below_safety_stock = True
order_deadline = stockout_date − lead_time_days（stockout_date が無ければ None）
```

- **内示の重複除去**: 照合単位内の `(得意先, 内作品番)` の重複を除いて合算する（需要予測 V-220 と同じ規則）
- **発注残の重複除去**: 発注番号で重複を除く。対象は完成品直下の工程の発注残のみ
- **安全在庫**: 照合単位内の内作品番の重複を除いて合算する
- リードタイムは工程の連鎖の合計（既存 `chain_lead_time`）。未設定は設定の既定値

### 2.2 stockout_risk.py — 対応区分（S-204 改称）

```python
RESPONSE_ORDER_OVERDUE = "発注遅れ"      # key: order-overdue,  rank 0
RESPONSE_DELIVERY_CHECK = "納期確認"     # key: delivery-check, rank 1
RESPONSE_ORDER_NEEDED = "要発注"         # key: order-needed,   rank 2
RESPONSE_WATCH = "要監視"                # key: watch,          rank 3
RESPONSE_NONE = "対象外"                 # key: none,           rank 4
```

判定（REQ-SRR-F-004）:

```
overdue = projection.overdue_order_qty > 0

if projection.stockout_date is not None:
    if projection.order_deadline <= as_of_date:   # 発注期限を過ぎた
        return 発注遅れ
    return 納期確認 if overdue else 要発注
# 切れない
if overdue:
    return 納期確認
if projection.below_safety_stock:
    return 要監視
return 対象外
```

理由（REQ-SRR-F-005）は上から順に積む。

| 理由 | 条件 |
|---|---|
| `在庫切れ {日付}` | `stockout_date` あり |
| `発注期限 {日付}` | `order_deadline` あり |
| `納期遅れの発注残 {件数} 件 {数量} 個` | `overdue_order_qty > 0` |
| `安全在庫 {数量} を下回る` | `below_safety_stock` |
| `リードタイム未設定` | `lead_time_source == default` |
| `内示なし（在庫は動かない）` | `has_demand` が False |

### 2.3 行に付ける項目

`attach_stockout_risk` が照合単位ごとに 1 回計算し、単位内の全行へ複製する。

| キー | 内容 |
|---|---|
| `response_class` / `response_class_key` | 対応区分・CSS キー |
| `response_reasons` | 理由の配列 |
| `stockout_date` | `YYYY/MM/DD` または空 |
| `order_deadline` | `YYYY/MM/DD` または空 |
| `below_safety_stock` | 真偽 |
| `safety_stock` | 数量 |
| `overdue_order_qty` / `overdue_order_count` | 納期遅れの発注残 |
| `lead_time_days` / `lead_time_source` | 既存 |

旧キー（`stockout_risk` / `stockout_risk_key` / `stockout_risk_reasons` / `days_until_stockout` / `shortage_qty` / `replenishment_*`）は撤去する。旧スナップショットの読込時は `response_class` が無ければ `対象外` として扱う。

### 2.4 撤去するもの

| 対象 | 理由 |
|---|---|
| `open_purchase_order.py` の 補充見込み・補充期限・長期納期超過 | 新判定では「納期が基準日より後か」だけを見る。発注残の生データ読み取りは残す |
| `StockoutRiskSettings.safety_days` / `watch_months` | 安全日数・監視期間を使わない |
| 猶予日数（V-228）・不足数量 | 在庫切れ日と発注期限に置き換わる |

### 2.5 並び順

既定は **対応区分ランク → 発注期限（空は末尾）→ 在庫切れ日（空は末尾）→ 出荷数量降順**。

## 3. ユースケース

`ImportStock._enrich_rows` の順序は変えない（需要予測 → 流動区分 → 対応区分）。`attach_stockout_risk` に安全在庫と日次内示が行経由で渡る。

## 4. インフラ

### 4.1 summary_queries

| 追加 | 内容 |
|---|---|
| `fetch_item_ordering_profiles` に `SAFETY_STOCK` を追加 | 既存の `M_ITEM` 問い合わせに列を足すだけ（REQ-SRR-NF-001） |
| 行に `safety_stock` | 内作品番の安全在庫 |
| 行に `unconfirmed_order_daily` | 内示の所要日と数量の疎な配列 `[{"date": "YYYY-MM-DD", "qty": n}]`。基準日より後のみ |

`unconfirmed_order_trend`（月次）は需要予測（V-220）が使い続けるため残す。

### 4.2 データ量

内示明細は 106,526 件・2,299 行なので 1 行あたり平均 46 件。`shipment_trend`（24 件）と同程度の増分に収まる。

## 5. インターフェース

- 一覧: 「在庫切れリスク」列 → 「対応区分」。列に **在庫切れ日**・**発注期限** を追加
- 行の色: 発注遅れ＝赤系、納期確認・要発注＝黄系、要監視・対象外＝色なし
- 詳細ダイアログ: 在庫切れリスク区分を **対応区分** に改め、理由を箇条書き。補充見込みの表示は撤去
- フィルタ: 5 区分
- CSV: 対応区分 / 在庫切れ日 / 発注期限 / 納期遅れ数量 を出す（列数が変わる）
- メニュー帯: 「発注遅れ N 件 / 要発注 N 件 / 納期確認 N 件」

## 6. 影響ファイル

| レイヤー | ファイル | 変更 |
|---|---|---|
| domain | `stock_projection.py`（新規） | 日次の見通し |
| domain | `stockout_risk.py` | 対応区分の判定に作り直し |
| domain | `open_purchase_order.py` | 補充見込み系を撤去、納期での振り分けのみ残す |
| domain | `app_settings.py` | `safety_days` / `watch_months` を撤去 |
| domain | `row_counts.py` / `list_client_data.py` / `list_rows.py` / `export_csv.py` / `table_display.py` / `list_query.py` / `row_display.py` | 区分・列・並び順・フィルタ |
| use_cases | `summary_api.py` / `portal_dashboard.py` / `save_confirmation.py` / `reset_confirmations.py` | 件数キー・帯 |
| infrastructure | `oracle/summary_queries.py` | 安全在庫・日次内示 |
| interfaces | `views.py`、`templates`、`static/js`、`static/css` | 表示 |
