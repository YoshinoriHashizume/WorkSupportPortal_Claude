# 機能設計書: 対応区分の判定材料を「今日手を打てるもの」に絞る

文書ID: DES-JUDGEMENT-SCOPE-2026-001
作成日: 2026/10/27
更新日: 2026/10/27
対応文書: [requirements.md](requirements.md)、[test-design.md](test-design.md)、[ubiquitous_language.md](../../ubiquitous_language.md)

---

## 1. 設計方針

1. **算出と判定を分ける。** 在庫切れ日・発注期限・安全在庫割れ・在庫シミュレーションの**算出は 1 行も変えない**。
   絞り込みは「算出した値を対応区分に反映するか」の段階だけで行う（REQ-JS-NF-004）
2. そのため **絞り込みは `assess_response_class`（判定）に置き、`build_stock_projection`（算出）には置かない**。
   こうすると `_assessment_fields` が保存する在庫切れ日・発注期限は従来どおりの実値になり、表示が壊れない（REQ-JS-F-004）
3. **判定に必要な材料は `DailyStockProjection` に持たせる。** 判定関数の引数を増やさず、2 軸マトリクスの形を保つ
4. 滞留の判定は**推定**なので、しきい値は設定値にし、文言にも推定である旨を残す（REQ-JS-NF-003）
5. **Oracle へのクエリは増やさない。** `UPDATED_DATE` は既存の発注残クエリに列を足すだけ（REQ-JS-NF-001）

## 2. ドメイン

### 2.1 app_settings.py（設定 2 件追加）

```python
MIN_JUDGEMENT_HORIZON_DAYS = 1
MAX_JUDGEMENT_HORIZON_DAYS = 365
MIN_STALE_ORDER_DAYS = 1
MAX_STALE_ORDER_DAYS = 730

@dataclass(frozen=True)
class AppSettings:
    ...
    #: 判定ホライズン（V-239）。在庫切れ日をここまでしか対応区分に反映しない
    judgement_horizon_days: int = 30
    #: 滞留発注残（V-238）と見なすまでの未更新日数
    stale_order_days: int = 30
```

既存 4 件と同じ作り（`_require_in_range` / `clamp_*` / `parse_settings_payload` / `settings_payload`）。
API のキーは `judgementHorizonDays` / `staleOrderDays`。

### 2.2 stock_simulation.py（発注残の 3 分）

```python
@dataclass(frozen=True)
class OverdueBreakdown:
    """納期を過ぎた発注残の内訳（V-224 / V-238）。"""
    overdue_qty: int = 0      # 納期遅れ（生きている）
    overdue_count: int = 0
    stale_qty: int = 0        # 滞留発注残
    stale_count: int = 0


def overdue_order_breakdown(
    unit_rows, *, as_of_date, stale_after_days: int | None
) -> OverdueBreakdown:
    """納期 ≤ 基準日 の発注残を「生きている」「滞留」に分ける。

    滞留の条件: `as_of_date - updated_at >= stale_after_days`
    `stale_after_days=None` または `updated_at` がない明細は**滞留としない**（REQ-JS-F-007）。
    """
```

既存の `overdue_orders()` は**残す**。内部で `overdue_order_breakdown(..., stale_after_days=None)` を呼び、
従来どおり「納期を過ぎた全部」の (数量, 件数) を返す。既存テストがそのまま通る。

`planned_incoming_by_due()`・`build_stock_simulation_input()` は**変更しない**。
滞留かどうかは**納期が過ぎた明細の話**であり、予定入荷（納期が未来）には影響しないため。

### 2.3 stock_projection.py（判定材料を載せる）

`DailyStockProjection` に 3 つ足す。**既定値つきなので既存の生成箇所は壊れない。**

```python
@dataclass(frozen=True)
class DailyStockProjection:
    ...（既存 9 項目は変更なし）
    #: 照合単位に手動発注（V-227）の行が 1 つでもあるか。要監視を出すかの判定に使う
    has_manual_ordering: bool = False
    #: 滞留発注残（V-238）。判定には使わず、表示のみ
    stale_order_qty: int = 0
    stale_order_count: int = 0
```

- `overdue_order_qty` / `overdue_order_count` の意味が **「納期遅れ（生きている）」に変わる**（滞留を含まない）
- `build_stock_projection` に `stale_order_days: int | None = None` を追加し、`overdue_order_breakdown` を呼ぶ
- `has_manual_ordering` は `_has_manual_ordering(unit_rows)` で求める。**単位内に 1 つでも手動発注があれば True**（安全側。人に見せる方へ倒す）
- **撤去**: 未使用の `_parse_date`（`parse_optional_ymd` を import せずに参照しており、呼ぶと `NameError` になる死んだコード）

在庫切れ日・発注期限・安全在庫割れの計算式は**一切変更しない**。

### 2.4 stockout_risk.py（判定の絞り込み）

```python
#: 判定ホライズン（V-239）の既定値。設定から渡す
DEFAULT_JUDGEMENT_HORIZON_DAYS = 30


def effective_stockout_date(
    projection, *, as_of_date, judgement_horizon_days
) -> date | None:
    """対応区分の判定に使う在庫切れ日。ホライズンより先なら None（REQ-JS-F-001）。"""
    stockout = projection.stockout_date
    if stockout is None:
        return None
    if (stockout - as_of_date).days >= judgement_horizon_days:
        return None
    return stockout


def assess_response_class(
    projection, *, as_of_date, judgement_horizon_days=DEFAULT_JUDGEMENT_HORIZON_DAYS
) -> ResponseAssessment:
```

判定（2 軸マトリクスの形は保つ）:

```python
stockout = effective_stockout_date(projection, as_of_date=as_of_date,
                                   judgement_horizon_days=judgement_horizon_days)
overdue = projection.overdue_order_qty > 0          # 滞留は含まない
watchable = projection.below_safety_stock and projection.has_manual_ordering

if stockout is not None:
    deadline = projection.order_deadline
    if deadline is not None and deadline <= as_of_date:
        response_class = RESPONSE_ORDER_OVERDUE
    else:
        response_class = RESPONSE_DELIVERY_CHECK if overdue else RESPONSE_ORDER_NEEDED
elif overdue:
    response_class = RESPONSE_DELIVERY_CHECK
elif watchable:
    response_class = RESPONSE_WATCH
else:
    response_class = RESPONSE_NONE
```

理由（`response_reasons`）は**判定に使わなかった材料も出す**（REQ-JS-F-004）。

| 条件 | 理由の文言 |
|---|---|
| 在庫切れ日あり・ホライズン内 | `在庫切れ 2026/11/10` ＋ `発注期限 2026/11/06` |
| 在庫切れ日あり・**ホライズン外** | `在庫切れ 2026/12/09（30 日より先のため対応区分に反映していません）` |
| 納期遅れ（生きている） | `納期遅れの発注残 3 件 120 個` |
| **滞留発注残あり** | `滞留発注残 5 件 87 個（納期切れのまま更新がなく入荷見込みに数えていません）` |
| 安全在庫割れ・手動発注 | `安全在庫 1,000 を下回る` |
| 安全在庫割れ・**MRP 発注／不明** | `安全在庫 1,000 を下回る（MRP が自動補充するため対応区分に反映していません）` |
| リードタイム未設定 | `リードタイム未設定`（変更なし） |
| 内示なし | `内示なし（在庫は動かない）`（変更なし） |

`_assessment_fields` に `stale_order_qty` / `stale_order_count` を追加。**在庫切れ日・発注期限は実値のまま保存する。**

`attach_response_class` に `judgement_horizon_days` / `stale_order_days` を追加し、`build_stock_projection` と `assess_response_class` へ渡す。

### 2.5 assessment_summary.py（判定サマリの文言）

見出しは**対応区分に従う**ので、ホライズン外の行は「在庫は切れません」系になる。これは正しくない表現なので分岐を足す。

| 対応区分 | 条件 | 見出し |
|---|---|---|
| 対象外・要監視 | 在庫切れ日が**ホライズン外にある** | `在庫は {在庫切れ日} に切れますが、{N} 日より先なので今は対応不要です` |
| 納期確認 | 滞留のみ（生きている納期遅れなし） | ※ 滞留は判定に使わないので納期確認にならない |

`build_assessment_summary(row, *, as_of_date, judgement_horizon_days)` に引数を追加する。

### 2.6 変更しないも

`stockout_risk` の `normalize_response_class` / `RESPONSE_CLASS_*` / `LEGACY_*`、
`flow_quadrant.py`、`stock_simulation.simulation_range()`、`unconfirmed_order_trend.py` は**一切変更しない**。

## 3. インフラ

### 3.1 summary_queries.py（列を足すだけ）

```sql
SELECT TRIM(p.PUCH_ODR_CD) AS ORDER_CD,
       TRIM(p.ITEM_CD)     AS ITEM_CD,
       TRIM(p.VEND_CD)     AS VEND_CD,
       p.PUCH_ODR_DLV_DATE,
       p.UPDATED_DATE,                      -- ★ 追加（V-238）
       p.PUCH_ODR_QTY - NVL((...), 0) AS ZAN
  FROM T_RLSD_PUCH_ODR p
 WHERE p.PUCH_ODR_STS_TYP = '2'
   AND NVL(p.ODR_CANCEL_SLIP_ISS_FLG, '0') = '0'
```

- **`CONFIRM_DLV_DATE` を SELECT から外す**（80 万件中 10 件しか入力がなく、納期の決定に使われていない。V-224 改訂）
- `fetch_open_purchase_orders` の戻りを **6 要素**に（`order_cd, item_cd, vend_cd, due, updated_at, remaining`）
- 行に載せる `open_purchase_orders` の dict に **`updated_at`**（`YYYY/MM/DD`）を追加
- **問い合わせ回数は 1 回のまま**

### 3.2 models.py / マイグレーション 0015

```python
judgement_horizon_days = models.PositiveIntegerField(default=30)
stale_order_days = models.PositiveIntegerField(default=30)
```

`0015_judgement_scope_settings.py`（AddField × 2）。**既存カラムの削除・変更はしない**（破壊的でない）。

### 3.3 settings_repository.py

`load_app_settings` / `save_app_settings` に 2 件を追加（既存 4 件と同じ `clamp_*` の形）。

## 4. ユースケース

| ファイル | 変更 |
|---|---|
| `use_cases/app_settings.py` | 設定 2 件の受け渡し |
| `domain/repositories/ports.py` | `SaveAppSettings` の署名に 2 件 |
| `use_cases/import_stock.py` | `attach_response_class` へ `judgement_horizon_days` / `stale_order_days` を渡す |
| `interfaces/wiring.py` | 設定の読み出しは既存経路のまま（変更不要） |

## 5. インターフェース

| ファイル | 変更 |
|---|---|
| `domain/value_objects/list_client_data.py` | `staleOrderQty` / `staleOrderCount` / `judgementHorizonDays` を配信 |
| `domain/value_objects/export_csv.py` | 末尾に **`滞留発注残件数` / `滞留発注残数量`** の 2 列（REQ-JS-F-006） |
| `templates/inventory_order_alert/list.html` | 「在庫と発注残」に **滞留発注残** の行を追加 |
| `templates/inventory_order_alert/settings.html` | 判定ホライズン日数・滞留判定日数の入力欄 |
| `static/js/inventory-order-alert-list.js` | 滞留発注残の描画（0 件なら隠す） |
| `static/js/inventory-order-alert-list-client.js` | `staleOrderQty` 等の受け渡し |
| キャッシュバスター | `?v=` を上げる |

## 6. エラーハンドリング

| 状況 | 挙動 |
|---|---|
| `updated_at` がない旧スナップショットの明細 | **滞留としない**（従来どおり納期遅れ。REQ-JS-F-007） |
| `updated_at` が解析できない | 同上（滞留としない。安全側） |
| `stale_order_days` が None（呼び出し側が渡さない） | 滞留判定をしない |
| 設定が範囲外（既存行） | `clamp_*` で丸める（既存と同じ） |
| 発注方式が空・不明 | **MRP 発注と同じ扱い**（要監視にしない。V-227 の規定どおり） |
| 在庫切れ日が基準日より前（理論上起きない） | 日数が負になりホライズン内と判定される（＝従来どおり判定に使う。安全側） |

## 7. 影響範囲のまとめ

**判定が変わる**: 対応区分（S-204）の件数、メニュー帯の件数、件数サマリ、行の背景色、既定ソート順。
**変わらない**: 在庫切れ日・発注期限・安全在庫・在庫シミュレーション・流動区分・確認状態・在庫内訳・工程の連鎖。
