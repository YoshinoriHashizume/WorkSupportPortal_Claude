# テスト設計書: 在庫切れリスクを内示のみ・日次の判定に作り直す

文書ID: TST-STOCKOUT-RISK-REWORK-2026-001
作成日: 2026/09/23
更新日: 2026/09/23
対応文書: [requirements.md](requirements.md)、[design.md](design.md)

---

## 1. 方針

- 基準日は **2026-09-18** に固定する
- 06 の在庫切れリスクのテスト（`TC-SOR-*`）は、補充見込み・猶予日数・監視期間を前提とするものを廃止し、本書のケースへ置き換える
- 日次の計算は純関数（`build_stock_projection`）で単体テストし、区分の判定は結果を与えて検証する

## 2. テストケース

### 2.1 日次の見通し（tests/test_stock_projection.py 新規）

| ID | 内容 | 期待 |
|---|---|---|
| TC-SRR-P-001 | 内示が 1 件もない | `has_demand=False`、`stockout_date=None` |
| TC-SRR-P-002 | 在庫 100・内示が 10/01 に 60、10/10 に 60 | `stockout_date=2026-10-10` |
| TC-SRR-P-003 | 同上＋納期 10/05 の発注残 50 | 在庫が戻り `stockout_date=None` |
| TC-SRR-P-004 | 同上だが発注残の納期が 10/20（在庫切れの後） | `stockout_date=2026-10-10`（一時的に切れる） |
| TC-SRR-P-005 | 発注残の納期が基準日以前（納期遅れ） | 在庫に加算しない。`overdue_order_qty` に計上 |
| TC-SRR-P-006 | リードタイム 8 日・在庫切れ 12/11 | `order_deadline=2026-12-03` |
| TC-SRR-P-007 | 在庫が未取得（None） | 在庫 0 として計算する |
| TC-SRR-P-008 | 安全在庫 50・在庫が最低 30 まで下がるが 0 未満にならない | `below_safety_stock=True`、`stockout_date=None` |
| TC-SRR-P-009 | 安全在庫 0（未設定） | `below_safety_stock=False` |
| TC-SRR-P-010 | 照合単位に同じ (得意先, 内作品番) の行が 2 つ | 内示を二重に数えない |
| TC-SRR-P-011 | 同じ発注番号が複数行にある | 予定入荷を二重に数えない |
| TC-SRR-P-012 | リードタイムが未設定 | 既定値で補い `lead_time_source=default` |

### 2.2 対応区分（tests/test_stockout_risk.py 置き換え）

| ID | 在庫の見通し | 納期遅れ | 期待 |
|---|---|---|---|
| TC-SRR-R-001 | 動かない（内示 0） | なし | 対象外 |
| TC-SRR-R-002 | 動かない | あり | 納期確認 |
| TC-SRR-R-003 | 切れない・安全在庫以上 | なし | 対象外 |
| TC-SRR-R-004 | 切れない・安全在庫以上 | あり | 納期確認 |
| TC-SRR-R-005 | 切れないが安全在庫割れ | なし | **要監視** |
| TC-SRR-R-006 | 切れないが安全在庫割れ | あり | 納期確認 |
| TC-SRR-R-007 | 切れる・発注期限が未来 | なし | **要発注** |
| TC-SRR-R-008 | 切れる・発注期限が未来 | あり | 納期確認 |
| TC-SRR-R-009 | 切れる・発注期限が当日 | なし | **発注遅れ**（当日は過ぎたとみなす） |
| TC-SRR-R-010 | 切れる・発注期限を過ぎた | あり | 発注遅れ |
| TC-SRR-R-011 | ランク | 発注遅れ 0 → 納期確認 1 → 要発注 2 → 要監視 3 → 対象外 4 |
| TC-SRR-R-012 | 旧区分の正規化 | 危険→発注遅れ / 注意→要発注 / 監視→要監視 / 対象外→対象外 |

### 2.3 理由（同上）

| ID | 内容 | 期待 |
|---|---|---|
| TC-SRR-N-001 | 在庫切れ日あり | 「在庫切れ 2026/10/10」「発注期限 2026/10/02」が並ぶ |
| TC-SRR-N-002 | 納期遅れあり | 「納期遅れの発注残 2 件 300 個」 |
| TC-SRR-N-003 | 安全在庫割れ | 「安全在庫 50 を下回る」 |
| TC-SRR-N-004 | リードタイム未設定 | 「リードタイム未設定」 |
| TC-SRR-N-005 | 内示なし | 「内示なし（在庫は動かない）」 |
| TC-SRR-N-006 | 対象外で該当なし | 理由は空 |

### 2.4 行への付与（tests/test_stockout_risk_list.py）

| ID | 内容 | 期待 |
|---|---|---|
| TC-SRR-A-001 | `attach_stockout_risk` | 照合単位ごとに 1 回判定し、単位内の全行に同じ値が入る |
| TC-SRR-A-002 | 付与キー | `response_class` / `response_class_key` / `response_reasons` / `stockout_date` / `order_deadline` / `below_safety_stock` / `overdue_order_qty` |
| TC-SRR-A-003 | 旧キーがない | `stockout_risk` / `days_until_stockout` / `replenishment_qty` を付けない |
| TC-SRR-A-004 | 旧スナップショット（キーなし） | 例外にならず「対象外」 |
| TC-SRR-A-005 | 入力を書き換えない | 元の行は変わらない |

### 2.5 集計・並び・画面・CSV

| ID | 内容 | 期待 |
|---|---|---|
| TC-SRR-C-001 | `count_rows` | 5 区分の件数。`attention` は対象外以外 |
| TC-SRR-C-002 | 既定の並び | 対応区分ランク → 発注期限（空は末尾）→ 在庫切れ日 → 出荷数量降順 |
| TC-SRR-C-003 | フィルタ `response_class=order-needed` | 要発注の行のみ |
| TC-SRR-C-004 | CSV | 対応区分 / 在庫切れ日 / 発注期限 / 納期遅れ数量 の 4 列が出る |
| TC-SRR-C-005 | 一覧の列 | 在庫切れ日・発注期限が並べ替えできる |
| TC-SRR-C-006 | 行の色 | 発注遅れ＝赤系、納期確認・要発注＝黄系、要監視・対象外＝色なし |
| TC-SRR-C-007 | メニュー帯 | 「発注遅れ N 件 / 要発注 N 件 / 納期確認 N 件」 |
| TC-SRR-C-008 | summary_api の件数キー | `orderOverdue` / `deliveryCheck` / `orderNeeded` / `watch` / `none` |
| TC-SRR-C-009 | 旧識別子の走査 | `stockout_risk` / `danger` / `caution` / 補充見込み系が残らない |

### 2.6 取込（tests/test_build_summary_rows.py / test_import_stock_usecase.py）

| ID | 内容 | 期待 |
|---|---|---|
| TC-SRR-I-001 | `fetch_item_ordering_profiles` | 安全在庫を返す。問い合わせ回数は増えない |
| TC-SRR-I-002 | 行に `safety_stock` / `unconfirmed_order_daily` が付く | 基準日より後の所要日のみ・疎な配列 |
| TC-SRR-I-003 | 安全在庫の取得失敗 | 取込を止めず安全在庫なしで続行 |
| TC-SRR-I-004 | 取込の順序 | 需要予測 → 流動区分 → 対応区分 |
