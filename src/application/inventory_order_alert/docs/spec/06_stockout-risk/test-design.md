# テスト設計書: 在庫切れリスクの判定と表示

文書ID: TEST-STOCKOUT-RISK-2026-001
作成日: 2026/09/17
更新日: 2026/09/21
対応文書: [requirements.md](./requirements.md)（REQ-STOCKOUT-RISK-2026-001）、[design.md](./design.md)（DESIGN-STOCKOUT-RISK-2026-001）

**状態: 草案（承認ゲート ③ 待ち。実装を先行）**

---

## 1. テスト戦略

| レイヤー | 方法 |
|---|---|
| Domain | pytest（Django 非依存）。判定表 F-005 と理由 F-006 の全分岐を固定 |
| Infrastructure | Oracle は `MagicMock` のカーソルで SQL と行変換を検証。取込フローは `@pytest.mark.django_db` |
| Interfaces | Django test client で HTML・CSV・JSON を断言。JS はソース断言＋ `node --check` |
| 実データ | 取込を実行せず読み取りのみで件数を測定し DECISIONS に記録（§3） |

## 2. テストケース

### 2.1 Domain

#### 発注残・補充見込み（`open_purchase_order.py`）

| # | ケース | 入力 | 期待 | REQ |
|---|---|---|---|---|
| TC-SOR-D-001 | 補充期限までの残数を合算（2026/09/21 改訂） | 基準日 2026/09/17、予測月 2026-12、補充期限 12/15、納期 10/5 100・12/15 50・12/16 30 | qty 150、later_qty 30、earliest 2026/10/05 | F-003 |
| TC-SOR-D-002 | 納期超過（LT＋安全日数以内）は含めて has_overdue（2026/09/21 改訂） | 基準日 9/17、stale_after 19、納期 2026/09/01 20 | qty 20、has_overdue True、stale_qty 0 | F-003, F-014#12 |
| TC-SOR-D-007 | 長期納期超過は補充に数えない（2026/09/21 追加） | 納期 2026/06/01 20（超過 108 日 > 19） | qty 0、stale_qty 20、has_overdue True | F-003, F-014#11 |
| TC-SOR-D-008 | 長期納期超過の境界 | 超過 = stale_after / +1 | qty に含む / stale_qty | F-003 |
| TC-SOR-D-009 | 補充期限 | 予測月 2026-10・基準日 9/17・安全 14 → 10/15。予測月 2026-09（当月）→ 10/1 | V-229 |
| TC-SOR-D-009a | 上流の pending は補充期限以前かつ納期超過なしのみ（2026/09/21 追加） | 上流: 納期 2027/03/01 100・納期なし 50・納期 10/1 30 | upstream_pending_qty 30、upstream_qty 180 | F-003 |
| TC-SOR-D-003 | 予測月が空なら qty 0 | stockout_month None | qty 0、earliest None | F-003 |
| TC-SOR-D-004 | 残数が負は 0 | remaining -5 | 0 | F-014#6 |
| TC-SOR-D-005 | 納期が空は数えない | due None | later 扱い（qty に含めない） | F-014 |
| TC-SOR-D-006 | 重複明細は 1 回 | 同じ (item, vend, due, qty) が 2 行から | 1 回だけ合算 | F-003 |

#### 発注方式・リードタイム（`ordering_profile.py`）

| # | ケース | 入力 | 期待 | REQ |
|---|---|---|---|---|
| TC-SOR-D-010 | コード写像 | "4" / 4 / "5" / "6" / None | 手動発注 / 手動発注 / MRP 発注 / 不明 / 不明 | F-002 |
| TC-SOR-D-011 | リードタイム既定 | 3 / 0 / None / "abc" with default 5 | (3, master) / (5, default) / (5, default) / (5, default) | F-002 |

#### 在庫切れリスク（`stockout_risk.py`）

| # | ケース | 入力 | 期待 | REQ |
|---|---|---|---|---|
| TC-SOR-D-020 | 猶予日数 | 基準日 9/17、予測月 2026-09 / 2026-10 / 2027-01 / None | 0 / 14 / 106 / None | V-228 |
| TC-SOR-D-021 | 予測月までの需要 | 当月残 100、月別 (200,200,200)、平均 200、予測月 2026-12 | 700（100+200+200+200） | F-004 |
| TC-SOR-D-022 | 4 か月目以降は平均 | 予測月 2027-02 | 100 + 600 + 200×2 | F-004 |
| TC-SOR-D-023 | 不足数量 | 需要 700、在庫 500 | 200。在庫 1000 なら 0 | F-004 |
| TC-SOR-D-030 | 監視: 需要なし | basis なし | 監視、理由なし | F-005 |
| TC-SOR-D-031 | 監視: 予測月が監視期間より先 | 予測 2027-05、監視 6 か月 | 監視 | F-005 |
| TC-SOR-D-032 | 監視: 在庫未取得 | stock_total None | 監視 | F-005, F-013 |
| TC-SOR-D-033 | 注意: 取得失敗 | outlook.unknown | 注意、理由「発注残を取得できませんでした」 | F-005, F-014#1 |
| TC-SOR-D-034 | 危険: 猶予 ≤ LT+安全日数 かつ qty 0 | 予測 2026-09、LT 5、安全 14、qty 0 | 危険、理由「リードタイム内」 | F-005 |
| TC-SOR-D-035 | 危険の境界 | 猶予 19 と LT 5+14=19 → 危険、猶予 20 → 注意（手動発注） | | F-005 |
| TC-SOR-D-036 | 注意: qty 0 で猶予あり（手動発注・不明） | 猶予 60 | 注意 | F-005 |
| TC-SOR-D-037 | 注意: 数量不足（猶予あり） | 猶予 60、qty 100、不足 200 | 注意、理由「数量不足」 | F-005, F-006 |
| TC-SOR-D-038 | 注意: 納期超過 | qty 300 ≥ 不足 200、has_overdue | 注意、理由「納期遅れ」 | F-005 |
| TC-SOR-D-039 | 対象外 | qty 300 ≥ 不足 200、超過なし | 対象外、理由なし | F-005 |
| TC-SOR-D-040 | 理由: 発注忘れ | 手動発注、直下の発注残なし | 「発注忘れの可能性」 | F-006 |
| TC-SOR-D-045 | 危険: リードタイム内で数量不足（2026/09/21 追加） | 猶予 0、qty 1、不足 400 | 危険、理由「リードタイム内」「数量不足」 | F-005 |
| TC-SOR-D-046 | 危険: 唯一の発注残が長期納期超過 | 猶予 0、qty 0、stale_qty 400、has_overdue | 危険、理由「リードタイム内」「納期遅れ」 | F-005, F-014#11 |
| TC-SOR-D-047 | 対象外: MRP 先送り | MRP 発注、猶予 60、qty 0、超過なし | 対象外、理由なし | F-005, F-014#13 |
| TC-SOR-D-048 | MRP 先送りの除外条件 | MRP・猶予 60・qty 0 で has_overdue → 注意。MRP・猶予 60・qty 100 < 不足 → 注意 | | F-005 |
| TC-SOR-D-048a | MRP 先送りは通常流動品のみ | MRP・猶予 60・qty 0 で 低流動品（入荷なし）／在庫死蔵品／低流動品（出荷なし） → 注意。upstream_overdue → 注意 | | F-005, F-014#13 |
| TC-SOR-D-049 | 直近入荷の免除は MRP のみ | 猶予 0・qty 0・入荷 10 日前: MRP → 注意「直近に入荷あり」、手動発注 → 危険「発注忘れの可能性」（「直近に入荷あり」なし）、不明 → 危険 | | F-005, F-014#14 |
| TC-SOR-D-049a | 発注忘れは発注残が 1 件もないときのみ | 手動発注、qty 0、later_qty 100 → 付かない。stale_qty 100 → 付かない | | F-006, F-014#5 |
| TC-SOR-D-041 | 理由: 仕入先確認 | 低流動品（入荷なし）／在庫死蔵品 | 「仕入先の生産可否を先に確認」 | F-006 |
| TC-SOR-D-042 | 理由: 立ち上がり品 | 低流動品（出荷なし）・内示 | 「立ち上がり品」 | F-006 |
| TC-SOR-D-043 | 理由: LT 未設定・仕入先未解決・実績ベース | source default / level1 空 / basis 実績ベース | それぞれ付く | F-006 |
| TC-SOR-D-044 | 監視・対象外には理由なし | | reasons == () | F-006 |
| TC-SOR-D-050 | attach: 照合単位で判定し全行に複製 | 96160 単位 4 行 | 4 行とも同じ risk | F-003 |
| TC-SOR-D-051 | attach: 旧行（キーなし） | demand_forecast キーなし | 監視、replenishment_unknown False | F-013 |
| TC-SOR-D-052 | attach: 入力を破壊しない | | 元 dict に新キーなし | NF |
| TC-SOR-D-053 | ランク順 | 危険 0 → 注意 1 → 監視 2 → 対象外 3 | | F-008 |
| TC-SOR-D-054 | 設定 VO | safety 0 / 61、default LT 0、watch 13 | ValueError。既定 14/5/6 | F-010 |

#### 一覧（`row_counts` / `table_display` / `list_query` / `list_client_data` / `export_csv`）

| # | ケース | 期待 | REQ |
|---|---|---|---|
| TC-SOR-D-060 | 件数サマリ | `danger` / `caution` / `watch` / `none_risk` を数える。旧行は監視 | F-009 |
| TC-SOR-D-061 | 既定ソート | 危険 → 注意 → 監視 → 対象外、同順位は猶予日数昇順（空末尾）、次に流動区分 | F-008 |
| TC-SOR-D-062 | フィルタ解釈 | `stockout_risk=danger`、`ordering_method=manual`。未知は空 | F-008 |
| TC-SOR-D-063 | ペイロード | 行に `stockoutRisk` 等、`stockoutRiskOrder`、`sortOnlyColumns` に猶予日数 | F-007 |
| TC-SOR-D-064 | CSV | 既存 28 列不変、末尾 9 列。理由は `・` 区切り、空は "" | F-012 |

### 2.2 Application / Infrastructure

| # | ケース | 期待 | REQ |
|---|---|---|---|
| TC-SOR-A-001 | `ImportStock` は需要予測 → 在庫切れリスクの順で後処理を合成する | 保存行に `stockout_risk` | F-005 |
| TC-SOR-A-002 | 設定値を wiring から注入 | safety_days 30 なら境界が変わる | F-010 |
| TC-SOR-I-001 | 発注残クエリ | `T_RLSD_PUCH_ODR`、`PUCH_ODR_STS_TYP = '2'`、取消なし、SELECT のみ 1 回 | F-001 |
| TC-SOR-I-002 | 行変換 | 回答納期優先、TRIM、負は 0、納期空は None | F-001, F-003 |
| TC-SOR-I-003 | 品目マスタクエリ | `M_ITEM`、900 件ずつ IN | F-002 |
| TC-SOR-I-004 | `build_summary_rows` が行に発注残・LT・発注方式を付ける（判定はしない） | `stockout_risk` キーなし | F-001, F-002 |
| TC-SOR-I-005 | 発注残の取得失敗 | 行に `open_purchase_orders_unknown`、warnings に文言、取込成功 | F-014#1 |
| TC-SOR-I-006 | 品目マスタの取得失敗 | LT 既定・発注方式不明、警告 | F-014#2 |

### 2.3 Interfaces

| # | ケース | 期待 | REQ |
|---|---|---|---|
| TC-SOR-X-001 | 一覧に在庫切れリスク列が先頭にあり、セルは段階名のみ | `<th>在庫切れリスク`、`ioa-stockout-risk` | F-007 |
| TC-SOR-X-002 | 行クラスは 確認状態 > 在庫切れリスク > 流動区分 | `alert-row--stockout-danger` | F-007 |
| TC-SOR-X-003 | 件数サマリが在庫切れリスク | 「危険 N 件 / 注意 N 件 / 監視 N 件 / 対象外 N 件」 | F-009 |
| TC-SOR-X-004 | メニュー帯 | 「危険 N 件 / 注意 N 件 / 未確認 N 件」、「監視期間 6か月」 | F-009 |
| TC-SOR-X-005 | 詳細ダイアログの項目 | `ioa-detail-stockout-risk` / `-reasons` / `-days` / `-replenishment` / `-shortage` / `-lead-time` / `-ordering-method` | F-007 |
| TC-SOR-X-006 | フィルタ | `?stockout_risk=danger` で絞れる、`?ordering_method=manual` | F-008 |
| TC-SOR-X-007 | CSV | 末尾 9 列 | F-012 |
| TC-SOR-X-008 | 旧スナップショット | 200、監視 | F-013 |
| TC-SOR-X-009 | JS ソース | 在庫切れリスクのランク・行クラス・猶予日数ソート（空末尾）・詳細描画 | F-007, F-008 |
| TC-SOR-X-010 | ペイロード `replenishment.staleQty`（2026/09/21 追加） | 行の `replenishment_stale_qty` が写る。旧行は 0 | F-007 |
| TC-SOR-X-011 | JS ソース: 詳細の補充見込みに「長期納期超過 N は除外」 | `staleQty` を参照 | F-007 |

## 3. 実データでの検証（自動テスト外、DECISIONS に記録）

| 検証 | 期待 |
|---|---|
| 危険・注意・監視・対象外の件数 | 危険は対応要 3 区分の 146 行を中心に、通常流動品の大半は注意以下 |
| 立ち上がり品（低流動品（出荷なし）・内示）で危険になる件数 | 記録して §6.4 事項 7 の判断材料に |
| 発注残・品目マスタの取得時間 | 合計 10 秒以内 |
| 96160-00500 | 監視 |
| 補正 3 の前後比較（2026/09/21） | 危険・注意・監視・対象外の件数、危険のうち理由「納期遅れ」、注意 → 対象外（MRP 先送り）の件数、連鎖 3 工程以上の危険件数 |

## 4. 境界値・異常系

| 対象 | 境界 | ケース |
|---|---|---|
| 猶予日数 vs LT+安全日数 | 等しい / +1 | D-035 |
| 補充見込み vs 不足数量 | 等しい / −1 | D-037, D-039, D-045 |
| 納期超過日数 vs LT+安全日数 | 等しい / +1 | D-008 |
| 納期 vs 補充期限 | 等しい / +1 | D-001 |
| 監視期間 | 予測月 = 基準日+6 か月 の月 / その翌月 | D-031 |
| 設定値 | 各範囲の下限−1 / 上限+1 | D-054 |
| 残数 | −1 / 0 / 正 | D-004 |
