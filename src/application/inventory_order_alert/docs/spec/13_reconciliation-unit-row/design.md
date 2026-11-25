# 機能設計書: 一覧を照合単位ごとの 1 行にまとめる

文書ID: DESIGN-RECONCILIATION-UNIT-ROW-2026-001
作成日: 2026/11/25
更新日: 2026/11/25（実装に合わせて §6.1 のキー名・§10 を改訂）
対応文書: [requirements.md](./requirements.md)（REQ-RECONCILIATION-UNIT-ROW-2026-001）、[ubiquitous_language.md](../../ubiquitous_language.md)（UL-INVENTORY-ORDER-ALERT-2026-001）
アーキテクチャreference: django-clean-architecture version 1.0

---

## 1. 設計の目的

一覧・件数・絞り込み・詳細ダイアログ・CSV・確認記録の単位を、得意先 × 得意先品番の行から照合単位行（T-213）に改める。
判定（対応区分 S-204）はすでに照合単位で行っているため変えない。**表示の単位と、表示に使う数量（流動区分・グラフ）を判定と同じ照合単位にそろえる**ことが技術上の要点である。

設計の基本方針は次の 3 点。

1. **照合単位行へのまとめは「読み込み時」に行う。** 集計スナップショット（`InventoryOrderAlertSummarySnapshot.rows`）は今までどおり得意先 × 得意先品番の行で保存する。読み込み時に domain の純関数でまとめる。保存形式が変わらないため、旧スナップショットでもそのまま動き（REQ-RUR-NF-004）、取込の処理と Oracle への問い合わせも変わらない（REQ-RUR-NF-001）
2. **照合単位行は代表得意先（V-241）の得意先コード・得意先品番を「行の識別子」として持つ。** 画面の JavaScript と API は今の行キー（`得意先コード|得意先品番`）のまま動く。照合単位に属するすべての値は別のキー（一覧）として足す
3. **確認記録は得意先品番ごとに保存し、照合単位行で読み書きする。** 保存の単位を細かくしておけば、照合単位が分かれても・まとまっても記録は失われない（REQ-RUR-F-012）

---

## 2. 対象コンテキスト

`docs/strategic_design.md` の **B: 在庫発注アラート**（生産管理・コアサブドメイン）の中で完結する。他コンテキストへの影響は、ポータル（メニュー画面のアラート帯の件数）だけで、件数の数え方が照合単位行になる。アラート帯は在庫発注アラートの use case（`portal_dashboard.py`）が返す件数を表示しているだけなので、ポータル側のコードは変えない。

---

## 3. アーキテクチャ概要

| レイヤー | 本機能で置くもの |
|---|---|
| domain | 照合単位行へのまとめ（`reconciliation_unit_row.py` 新設）、確認記録の照合単位行への付与（`confirmation.py` 改修）、絞り込み・CSV の複数値対応（`list_rows.py`・`export_csv.py`）、配信データ（`list_client_data.py`） |
| use_cases | 確認状態の保存・確認メモを照合単位行に対して行う（`save_confirmation.py`・`confirmation_memos.py` 改修）。ポートの引数を得意先品番の集合に変える |
| infrastructure | 読み込み時のまとめの呼び出し（`summary_repository.py`）、確認記録の保存（`confirmation_repository.py`）、取込後の確認リセットを照合単位行で判定（`summary_aggregation.py`）、データ移行（migration 0017） |
| interfaces | 変更なし（views はペイロードをそのまま use case に渡している）。wiring の差し替えのみ |
| 画面（template・JS） | 「他 N」の印、得意先別内訳（V-242）、内示推移の得意先別内訳、絞り込みを照合単位行に含まれる値で行う |

依存方向（interfaces → use_cases → domain ← infrastructure）は変えない。新設する domain モジュールは Django を import しない。

### 3.1 読み込み時の処理順（`load_latest_summary`）

```
スナップショットの行（得意先 × 得意先品番）
  → attach_stock_fields（今と同じ。SLIMS 在庫数は得意先品番ごとに付く）
  → build_reconciliation_unit_rows（新設。照合単位行にまとめる）
  → attach_unit_confirmation_fields（改修。得意先品番の確認記録から照合単位行の確認状態を決める）
  → apply_flow_quadrants_to_rows（今と同じ関数。照合単位行の合算値で流動区分を判定する）
  → count_rows（今と同じ。照合単位行を数える）
```

今は「確認記録の付与 → 流動区分 → 在庫の付与」の順だが、**まとめの前に得意先品番ごとの SLIMS 在庫数が要る**ため、在庫の付与を先に、流動区分をまとめの後に移す。流動区分の判定関数は行の値（最終入荷日・最終出荷日・在庫・内示推移・入荷推移）だけを見るので、まとめた行に合算値を入れればそのまま照合単位で判定できる（REQ-RUR-F-003）。

---

## 4. ドメインモデル

### 4.1 エンティティ

#### E-201 確認記録（改修）

| 項目 | 変更前 | 変更後 |
|---|---|---|
| 保存キー | 得意先コード + 得意先品番 | **得意先品番** |
| 得意先コード | キーの一部 | 最後に記録した照合単位行の代表得意先コード（参考値。キーではない） |

照合単位行で確認状態を変えると、照合単位に属するすべての得意先品番の確認記録を **1 つのトランザクションで** 同じ値に更新する（記録がなければ作る）。

#### E-202 確認メモ（改修）

照合単位行に追加した確認メモは、照合単位に属する **得意先品番の数だけ複製** して各確認記録に付ける。複製には同じ **メモ識別子（`entry_group`）** を付け、表示するときはメモ識別子で 1 件にまとめる。

- 照合単位が分かれても、分かれた各照合単位行に元のメモが残る（REQ-RUR-F-012）
- 照合単位がまとまったときは、複製が重なっても 1 件として表示される（「同じ確認メモを重ねて出さない」）
- 既存のメモ（移行前）はメモ識別子が空。表示では各メモの `id` を識別子とみなす

### 4.2 バリューオブジェクト

#### ReconciliationUnitRow（T-213 照合単位行）

既存の行と同じく **辞書（`dict[str, object]`）** として表す（ISSUE-0001 のとおり本コンテキストの行は辞書中心であり、本機能で型を変えると影響が広すぎるため）。照合単位行は、既存の行のキーをすべて持つうえで、次のキーを足す。

| キー | 内容 |
|---|---|
| `unit_member_count` | 照合単位に属する得意先 × 得意先品番の行数 |
| `cust_codes` / `cust_names` | 照合単位に属する得意先コード・得意先名（代表得意先が先頭。以降は得意先コード順） |
| `cust_chrg_psn_cds` | 担当者コード（V-207）の一覧（代表得意先の値が先頭） |
| `item_cds` | 得意先品番の一覧（代表の値が先頭） |
| `level1_vend_cds` / `level1_vend_names` / `level1_item_cds` | 仕入先コード・仕入先名・仕入先品番の一覧（代表の値が先頭） |
| `customer_breakdown` | 得意先別内訳（V-242）。得意先 × 得意先品番ごとに、得意先コード・得意先名・得意先品番・担当者コード・内示推移（月次）・出荷推移（月次）・期間内出荷・最終出荷日 |

単数キー（`cust_code`・`item_cd`・`cust_chrg_psn_cd`・`level1_vend_cd` など）は **代表得意先の行の値** を入れる。画面の行キー・並べ替え（REQ-RUR-F-005 の文字列列）・既存の API はこの値を使う。

#### 照合単位行の値の決め方（REQ-RUR-F-002）

| 値 | まとめ方 |
|---|---|
| 代表得意先（V-241） | 得意先ごとに内示推移（`unconfirmed_order_trend`）の全月を合計し、最大の得意先。同数は得意先コードの小さい方。代表得意先が複数の得意先品番を持つときは、内示推移の合計が最大の得意先品番（同数は得意先品番の小さい方）の行を代表の行とする |
| 対応区分・在庫切れ日・発注期限・理由・判定サマリ・需要予測（V-220） | 代表の行の値（もともと照合単位で同じ値が全行に複製されている） |
| SLIMS 在庫数（V-206）・MARI 在庫数（V-215） | 得意先品番の重複を除いて合算。照合単位のすべての得意先品番が空なら空（在庫なしの判定 `row_stock_missing` を変えないため） |
| 在庫内訳（V-205） | 得意先品番の重複を除いて連結 |
| 最終入荷日・最終出荷日 | 最も新しい日 |
| 出荷回数・出荷数合計・期間内出荷 | 得意先 × 得意先品番ごとに合算 |
| 出荷推移（V-216）・日次出荷（V-234） | 得意先 × 得意先品番の重複を除いて日・月ごとに合算 |
| 入荷推移（V-217）・日次入荷（V-235）・期間内入荷 | 内作品番 × 仕入先の組の重複を除いて合算 |
| 内示推移（V-219）・日次の内示 | 得意先 × 内作品番の重複を除いて合算 |
| 発注残（V-224）・予定入荷（V-236） | 発注番号の重複を除いて連結し、予定入荷は納期ごとに合算 |
| 工程（`process_chain`）・リードタイム・発注方式 | 代表の行の値。発注方式は照合単位内に手動発注があれば手動発注（対応区分の判定 `has_manual_ordering` と同じ） |

重複除去の規則は、在庫シミュレーション（`stock_simulation.build_stock_simulation_input`）がすでに使っているもの（`pair_keys`）と同じにする。これで **グラフの材料が判定の材料と一致する**（REQ-RUR-F-008）。

### 4.3 集約

確認記録（E-201）と確認メモ（E-202）が 1 つの集約（確認記録がルート）であることは変えない。照合単位行は集約ではなく、読み込み時に作る **表示用の値** である（永続化しない）。

### 4.4 ドメインサービス

`domain/value_objects/reconciliation_unit_row.py`（新設）に純関数として置く。

| 関数 | 役割 |
|---|---|
| `build_reconciliation_unit_rows(rows) -> list[dict]` | 行を照合単位（`ReconciliationUnits.build`）ごとに 1 行にまとめる。得意先品番が空で照合単位に属さない行はそのまま 1 行で返す（REQ-RUR-F-001）。返す順は入力の代表の行の順 |
| `select_representative(unit_rows) -> dict` | 代表の行を選ぶ（V-241） |
| `unit_confirmation(item_cds, confirmations) -> ConfirmationRecord \| None` | 得意先品番ごとの確認記録から、照合単位行の確認状態を決める（最も新しく更新されたもの。REQ-RUR-F-012） |
| `merge_memo_entries(records) -> list` | 照合単位に属する確認記録のメモをメモ識別子で 1 件にまとめ、新しい順に並べる |

---

## 5. データモデル

### 5.1 `InventoryOrderAlertConfirmation`（変更）

| カラム | 変更 |
|---|---|
| `cust_code` | 残す。一意制約から外し、参考値とする |
| `item_cd` | **一意** にする（制約 `unique_inventory_order_alert_confirmation_item`） |

### 5.2 `InventoryOrderAlertConfirmationMemoEntry`（変更）

| カラム | 変更 |
|---|---|
| `entry_group` | **追加**。`CharField(max_length=36, blank=True, default="")`。照合単位行に追加したときの複製を束ねる識別子（UUID 文字列）。空は移行前のメモ |

### 5.3 migration `0017_confirmation_per_item`（新設・REQ-RUR-F-013）

1. `entry_group` を追加する
2. データ移行（`RunPython`）:
   - 得意先品番ごとに確認記録を束ね、`updated_at` が最も新しい記録を残す（確認状態・確認者・確認日時・確認時の流動区分はその記録の値）
   - 残さない記録の確認メモは、残す記録へ付け替える（メモは 1 件も削除しない）
   - 付け替えたあと、残さない確認記録を削除する
   - 移行の前後で「確認記録の得意先品番の数」と「確認メモの件数」を標準出力に出す。確認メモの件数が変わったら例外にして移行を中止する
3. 一意制約を `(cust_code, item_cd)` から `item_cd` に付け替える

逆方向（ロールバック）は、一意制約を戻すだけで確認記録・メモは移行後の状態のまま残す（統合した記録を元の得意先ごとに分け直す情報はないため）。本番では移行前にデータベースを退避する（要件 §6.2）。

### 5.4 集計スナップショット

**変更しない。** 照合単位行は読み込み時に作る。

---

## 6. API / インターフェース設計

### 6.1 一覧画面への配信データ（`list_client_data.row_to_client_dict`）

照合単位行 1 件を 1 要素として配信する。既存のキーは残し、次を足す。

| キー | 内容 |
|---|---|
| `unit_member_count` | 照合単位に属する行数 |
| `cust_codes` / `cust_names` / `cust_chrg_psn_cds` / `item_cds` / `level1_vend_cds` / `level1_vend_names` / `level1_item_cds` | 一覧（代表が先頭） |
| `customer_breakdown` | 得意先別内訳。各要素に `cust_code`・`cust_name`・`item_cd`・`cust_chrg_psn_cd`・`unconfirmed_order_trend`（月次の内示推移）・`shipment_trend`（月次の出荷推移）・`post_shipment_count`・`post_shipment_total_qty`・`last_ship_date` |

グラフ用の `dailyShipment`・`dailyIncoming`・`unconfirmedOrderDaily`・`plannedIncoming` は **照合単位行の合算値** になる（キー名は変えない）。これで在庫シミュレーションのグラフは JavaScript を変えずに判定と一致する。

配信データ量（REQ-RUR-NF-003）: 行数は 1,996 → 1,726 に減り、照合単位を共有する行に重複していた日次・月次の系列が 1 回になる。一方で `customerBreakdown` と一覧キーが増える。実装後に変更前後の JSON の大きさを測り、tasks.md に記録する。上回る場合は `customerBreakdown` の月次系列を詳細ダイアログを開いたときの別 API に移す案を検討する。

### 6.2 確認状態の保存（`POST /api/inventory-order-alert/confirmation`）

リクエストは今と同じ（`custCode`・`itemCd`・`status`・`memo`）。`custCode`・`itemCd` は **照合単位行の代表の値** として受け取る。use case は最新の集計から該当する照合単位行を探し、その `item_cds` すべてに保存する。

- 該当する照合単位行がない（取込で消えた）ときは、受け取った得意先品番 1 件だけに保存する（今と同じ振る舞い）
- レスポンスの件数（`counts`）は照合単位行で数えた値

### 6.3 確認メモ（一覧取得・追加 API）

URL とパラメータは今と同じ。追加は照合単位行の `item_cds` すべてに、同じ `entry_group` で複製する。一覧取得は照合単位行の `item_cds` の確認記録からメモを集め、`entry_group`（空なら `id`）で 1 件にまとめる。

### 6.4 一覧データ API（`GET /api/inventory-order-alert/summary`）

返す行が照合単位行になる。既存のキーは残すため、キーを読むだけの利用者は動き続ける（追加キーが増えるだけ）。ただし **行数が減り、`cust_code` は代表得意先の値になる**。ポータルの画面以外の利用者の有無は未確認（要件 §6.2）。

### 6.5 CSV（REQ-RUR-F-010）

1 行 = 照合単位行。次の列は一覧キーを「、」で連結して出す: 得意先コード・得意先名・担当者コード・得意先品番・仕入先コード・仕入先名・仕入先品番。その他の列は照合単位行の値。列の構成（列名と順）は変えない。

### 6.6 画面

| 場所 | 変更 |
|---|---|
| 一覧の表 | 得意先コード・得意先名・担当者コード・得意先品番・仕入先の各セルで、一覧が 2 件以上なら代表の値の後ろに「他 N」の印（`<span class="ioa-unit-more" title="全件を「、」で連結">`）を出す |
| 絞り込み（得意先・担当者・得意先品番・仕入先品番） | `custCodes` などの一覧のどれかが一致すれば表示する（REQ-RUR-F-004）。選択肢も一覧のすべての値から作る。サーバ側の絞り込み（`filter_summary_rows`。CSV・API が使う）も同じ規則にする |
| 詳細ダイアログ | 見出しの下に「得意先別内訳」の表を新設する（得意先コード・得意先名・得意先品番・担当者コード・期間内出荷・最終出荷日・今月以降の内示推移）。得意先が 1 つでも表を出す。得意先が 2 つ以上なら見出しに「得意先 N 社」と出す（REQ-RUR-F-006） |
| 内示推移（V-219） | 合算の月次を今の表示のまま出し、その下に得意先別の月次を表で出す（REQ-RUR-F-007） |
| 在庫シミュレーション・推定在庫推移 | 表示は変えない（材料が照合単位行の合算になる） |

JavaScript には判定や合算を持ち込まない（REQ-RUR-NF-005）。「他 N」の N と内訳はサーバが作った一覧・内訳をそのまま表示する。

---

## 7. 既存コードへの変更点

| # | ファイル | 変更概要 |
|---|---|---|
| 1 | `domain/value_objects/reconciliation_unit_row.py` | **新設**。§4.4 の関数 |
| 2 | `domain/value_objects/confirmation.py` | `attach_confirmation_fields` を得意先品番キーの確認記録から照合単位行に付ける形に改修。`ConfirmationRecord` にメモ識別子を足す |
| 3 | `domain/value_objects/list_rows.py` | `filter_summary_rows` の得意先・仕入先の絞り込みを一覧キーで判定 |
| 4 | `domain/value_objects/list_filter.py` | 絞り込みの選択肢を一覧キーから作る |
| 5 | `domain/value_objects/list_client_data.py` | §6.1 のキーを足す |
| 6 | `domain/value_objects/export_csv.py` | §6.5 の連結 |
| 7 | `domain/repositories/ports.py` | 確認記録の保存・メモのポートを「得意先品番の集合」を受ける形に変える |
| 8 | `use_cases/save_confirmation.py` | 照合単位行を探し、`item_cds` すべてに保存 |
| 9 | `use_cases/confirmation_memos.py` | 照合単位行の `item_cds` でメモを読み書き |
| 10 | `infrastructure/persistence/summary_repository.py` | §3.1 の処理順に組み替え |
| 11 | `infrastructure/persistence/confirmation_repository.py` | 得意先品番キーでの読み書き、1 トランザクションでの一括保存、メモの複製と `entry_group`、`reconcile_confirmations_after_import` を照合単位行の流動区分で判定 |
| 12 | `infrastructure/oracle/summary_aggregation.py` | 確認リセットに渡す行を照合単位行（まとめ → 流動区分）にする（REQ-RUR-F-014） |
| 13 | `use_cases/patch_snapshot_row.py` | 確認リセットに渡す行を #12 と同じにする |
| 14 | `models.py` | §5.1・§5.2 |
| 15 | `migrations/0017_confirmation_per_item.py` | **新設**。§5.3 |
| 16 | `interfaces/wiring.py` | ポート差し替え |
| 17 | `templates/inventory_order_alert/list.html` | 得意先別内訳・内示推移の得意先別表の枠 |
| 18 | `static/js/inventory-order-alert-list-client.js` | 絞り込みを一覧キーで、「他 N」の描画 |
| 19 | `static/js/inventory-order-alert-list.js` | 詳細ダイアログの得意先別内訳・内示推移の得意先別表の描画 |
| 20 | `static/css/`（一覧の CSS） | 「他 N」の印・内訳表 |
| 21 | 機能仕様書・テスト仕様書・用語集 | 照合単位行に合わせて改訂 |

---

## 8. エラーハンドリング方針

| 事象 | 振る舞い |
|---|---|
| 旧スナップショット（`reconciliation_unit_key` などがない） | まとめは `ReconciliationUnits.build` で行のつながりから求めるため、キーがなくても動く（REQ-RUR-NF-004） |
| 照合単位行の値の一部が欠けている・壊れている | 欠けた値は 0・空として合算し、例外にしない（今の `_sparse_series` と同じ） |
| 確認状態の保存中に一部の得意先品番で失敗 | 1 トランザクションで行うので全件を取り消し、エラーを返す（REQ-RUR-F-011。一部だけ更新された状態を残さない） |
| 保存しようとした照合単位行が最新の集計にない | 受け取った得意先品番 1 件に保存する（§6.2） |
| 移行で確認メモの件数が変わる | 例外で移行を中止する（§5.3） |

---

## 9. リスクと対策

| リスク | 対策 |
|---|---|
| 流動区分が 77 照合単位で変わり、件数サマリ・アラート帯の流動区分別の件数が変わる | 意図した変更（REQ-RUR-F-003）。機能仕様書の変更履歴に実測の件数を残す |
| 流動区分の悪化による確認リセットが、照合単位で判定し直すことで導入直後にまとめて起きる | 導入時の取込でリセット件数をログと取込結果に出す（今の仕組み）。件数が多いときは利用者に周知する |
| 一覧データ API の利用者が画面以外にいる | 既存キーは残す（追加のみ）。行数と `cust_code` の意味が変わる点を機能仕様書に明記する。利用者が見つかれば別途対応 |
| 配信データ量が増える | §6.1 のとおり実測し、上回れば内訳を別 API に移す |
| 確認記録の移行の失敗・取り違え | 退避・件数の照合・メモ件数が変わったら中止（§5.3） |
| 変更範囲が広い（L3 指摘 #4） | **1 回のリリースにまとめる**。保存形式を変えない設計のため段階に分ける利点が小さく、表示（照合単位行）と確認記録（照合単位で 1 つ）を別々に出すと、1 行に複数の確認状態が出る中間状態ができるため。実装は domain（まとめ）→ 確認記録 → 画面の順に進め、各段階でテストを通す |
| 照合単位の顔ぶれが変わったときに確認状態が予期せず変わる | 最も新しい記録を採る規則を domain の純関数に置き、テストで固定する（分割・統合・品番追加・記録なし） |

---

**承認**: Hashizume / 2026/11/25 17:06（承認ゲート③ 機能設計）

---

## 10. 実装時の改訂（2026/11/25）

| # | 箇所 | 改訂 | 理由 |
|---|---|---|---|
| 1 | §6.1 | 配信データの一覧キーは camelCase（`custCodes` など）ではなく行のキーの snake_case（`cust_codes`・`customer_breakdown`・`unit_member_count`）のまま使う | 配信データは行の全キーを snake_case で写す作り（`row_to_client_dict`）で、camelCase の別名を足すと同じ値を二重に配信し REQ-RUR-NF-003 に反する |
| 2 | §4.2 | **1 行だけの照合単位は元の行の値をそのまま使う**（一覧キー・内訳・行数だけを足す）。2 行以上でも、どの行にもないキーは作らない | 旧スナップショットの「未取得」（キーがないこと）の区別と、推移の並び順を変えないため（既存テストが検出） |
| 3 | §4.4 | `unit_confirmation`・`merge_memo_entries` は `confirmation.py` に置く（`reconciliation_unit_row.py` からも読める）。照合単位行を探す `find_unit_row`・`unit_item_cds_for`、照合単位行にまとめて流動区分を付ける `list_rows.unit_rows_with_reference_flow` を足した | `attach_confirmation_fields` からの循環 import を避ける。確認リセットの呼び出し元が 2 か所（取込・スナップショット修正）あるため |
| 4 | §6.6・§7 | サーバ側の絞り込み `list_filter.apply_list_filters`（一覧画面の描画・保存後の件数）も一覧キーのどれかで当たるようにした | 設計時に見落としていた |
| 5 | §6.3 | `ConfirmationMemos` は `load_summary` を任意の引数で受け、照合単位行の得意先品番を引く | メモの一覧・追加を照合単位行で行うため |
| 6 | §6.1 | 配信データ量は 20,254,152 → 20,635,327 バイト（+1.9%）。目安（上回らない）を超えた | 得意先別内訳と一覧キーが増えた分。行が 1,996 → 1,726 に減っても、行の全キーを写す作りのため相殺しきれなかった |
