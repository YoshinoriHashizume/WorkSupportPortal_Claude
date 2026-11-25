# 機能設計書: 直送品を在庫発注アラートの対象から外す

文書ID: DESIGN-DIRECT-SHIPMENT-EXCLUSION-2026-001
作成日: 2026/11/25
更新日: 2026/11/25（実装に合わせて既定値の型・save_view を追記）
対応文書: [requirements.md](./requirements.md)（REQ-DIRECT-SHIPMENT-EXCLUSION-2026-001）、[ubiquitous_language.md](../../ubiquitous_language.md)（V-240・T-212・S-204）
アーキテクチャreference: django-clean-architecture version 1.0

---

## 1. 設計の目的

取込時に直送品（T-212）を判定し、**集計スナップショットに保存する前に取り除く**。
スナップショットに直送品の行が残らないため、一覧・件数サマリ・アラート帯・CSV・絞り込み候補は、どれも**読む側を変えずに**直送品を含まなくなる（REQ-DSE-F-003/F-004）。
あわせて、直送仕入先（V-240）を設定画面で変更できるようにする（REQ-DSE-F-001）。

## 2. 対象コンテキスト

| 項目 | 内容 |
|---|---|
| 境界づけられたコンテキスト | **B: 在庫発注アラート**（生産管理・コア） |
| 基幹（MARI） | 共有カーネル H（`application/sales/infrastructure/oracle/`）経由で **SELECT のみ**。今回は設定画面での仕入先マスタ（`M_VEND_CTRL`）参照を 1 つ追加する |
| SLIMS | 順応者。取込 CSV の扱いは変えない |
| 他コンテキストへの影響 | なし。ポータルのダッシュボード（アラート帯）は本アプリの `PortalDashboard` がスナップショットを読むだけなので、変更は要らない |

## 3. アーキテクチャ概要

```
interfaces  views.settings_page / api_settings ──→ wiring ──→ AppSettingsUseCase
                                                         └──→ ImportStock
use_cases   ImportStock._enrich_rows: ①直送品を除く → ②需要予測 → ③流動区分 → ④対応区分
            AppSettingsUseCase: 直送仕入先の検証（新規コードのみ実在確認）・仕入先名の解決
domain      DirectShipmentSuppliers（VO）・exclude_direct_shipment_items（純関数）
            AppSettings に直送仕入先を追加・LookupVendorNames ポート
infra       InventoryOrderAlertSettings に JSON 列を追加・settings_repository
            oracle/vendor_lookup.py（M_VEND_CTRL を SELECT）
```

依存方向は interfaces → use_cases → domain ← infrastructure を守る。views は wiring 経由でのみ組み立てる。

### 3.1 なぜ「保存前に除く」か

| 案 | 内容 | 判断 |
|---|---|---|
| **A. 保存前に除く（採用）** | 取込の後処理の最初で直送品の行を除き、残りだけをスナップショットに保存する | 一覧・CSV・件数・アラート帯・絞り込み候補・`total_count` が**読む側の変更なし**で揃う。直送品を確かめる画面は設けない方針（REQ-DSE-F-003）なので、直送品を保存しておく理由がない |
| B. 印を付けて保存し、読む側で除く | 行に「直送品」の印を付け、一覧・CSV・件数・アラート帯・API でそれぞれ除く | 除き忘れる箇所が出やすい（読む側が 5 か所以上ある）。読む側の変更が多い |

- 確認記録は消えない。取込後の突き合わせ（`reconcile_confirmations_after_import`）は、スナップショットに行がない確認記録を**飛ばすだけ**で削除しない（REQ-DSE-F-006）
- 旧スナップショットは作り直さないので、次回取込まですべての行が出る（REQ-DSE-F-005）

## 4. ドメインモデル

### 4.1 エンティティ

追加なし。

### 4.2 バリューオブジェクト

#### DirectShipmentSuppliers（直送仕入先 V-240）— `domain/value_objects/direct_shipment.py`（新規）

| 項目 | 内容 |
|---|---|
| 構成要素 | `codes: tuple[str, ...]`（仕入先コード。前後の空白を除き、昇順に並べる） |
| 不変条件 | 各コードは空でない。20 文字以内。重複しない。0 件を許す |
| 生成 | `DirectShipmentSuppliers.parse(values)`: 入力の検証に使う。空・重複・長すぎは `ValueError`（メッセージは §8） |
| 生成（保存値） | `DirectShipmentSuppliers.from_stored(value)`: DB の値を読む。不正な要素は黙って捨てる（既存の `clamp_*` と同じく、壊れた保存値で画面を落とさない） |
| 振る舞い | `contains(vend_cd) -> bool`・`is_empty`・`added_since(other) -> tuple[str, ...]`（`other` になく自分にあるコード。実在確認の対象を絞るのに使う） |
| 既定値 | `DEFAULT_DIRECT_SHIPMENT_SUPPLIERS = DirectShipmentSuppliers(("9100", "9200", "9250"))`（丸栄豊田・テクノス工場・丸栄豊田（福岡））。モデルの既定値の関数もこの値を返す（値の正は domain） |

#### AppSettings（既存）— `domain/value_objects/app_settings.py`

- フィールド `direct_shipment_suppliers: DirectShipmentSuppliers` を追加する（既定値は上記）
- `SettingsInput` にも同じフィールドを追加する
- `parse_settings_payload`: キー `directShipmentSupplierCodes`（文字列の配列）を受ける。**未指定なら現在値を引き継ぐ**（既存の規則どおり）。配列でない・要素が文字列でないときは `ValueError`
- `settings_payload`: `directShipmentSupplierCodes` を出す

#### VendorName（仕入先名の解決結果）— `direct_shipment.py`

| 項目 | 内容 |
|---|---|
| 構成要素 | `code: str`・`name: str`・`status: "found" \| "not_found" \| "unavailable"` |
| 用途 | 設定画面で直送仕入先の名前を表示する（REQ-DSE-F-001）。`not_found` は「仕入先マスタに見つかりません」、`unavailable` は「仕入先名を取得できません」と表示する |

### 4.3 集約

追加なし。直送仕入先は設定（`AppSettings`、単一行）の一部として扱う。

### 4.4 ドメインサービス（純関数）

#### `is_direct_shipment(unit_rows, suppliers) -> bool` — `direct_shipment.py`

照合単位 1 つ分の行について、直送品（T-212）かどうかを返す。

| 条件 | 判定 |
|---|---|
| `suppliers` が空 | False |
| 行のうち 1 つでも `level1_vend_cd`（前後の空白を除く）が空 | False（REQ-DSE-F-002） |
| 行のうち 1 つでも `level1_vend_cd` が `suppliers` にない | False（混在する照合単位は直送品としない） |
| 行のうち 1 つでも `stock_qty` が空（`None` または `""`）でない | False（**数量 0 は空でない**。REQ-DSE-F-002） |
| 上のどれにも当たらない | True |

#### `exclude_direct_shipment_items(rows, suppliers) -> DirectShipmentExclusion` — `direct_shipment.py`

- `ReconciliationUnits.build(rows)` で照合単位を作り、単位ごとに `is_direct_shipment` を評価する
- 得意先品番が空で照合単位に属さない行は、その行 1 つを単位とみなして評価する（`attach_response_class` と同じ扱い）
- 戻り値 `DirectShipmentExclusion`: `kept_rows`（入力の並び順のまま。dict は複製しない＝後続の後処理が複製する）・`excluded_row_count`・`excluded_unit_count`
- **直送品の照合単位は丸ごと除く**ため、残る照合単位の構成（連結成分）は除く前と変わらない。したがって後続の需要予測・流動区分・対応区分の結果は、直送品でない照合単位について除く前と同じになる（REQ-DSE-NF-003）

## 5. データモデル

### 5.1 `InventoryOrderAlertSettings`（既存・単一行）に列を追加

| 列 | 型 | 既定値 | 説明 |
|---|---|---|---|
| `direct_shipment_supplier_codes` | `JSONField`（文字列の配列） | `default_direct_shipment_supplier_codes()`（`["9100", "9200", "9250"]` を返す） | 直送仕入先（V-240）。変更者・変更日時は既存の `updated_by`・`updated_at` に残る（REQ-DSE-NF-004） |

- **マイグレーション `0016_direct_shipment_suppliers`**: `AddField`。既定値の関数により、**既存の設定行にも初期値 3 件が入る**。本番導入時は `migrate` だけで初期値が登録された状態になる（REQ-DSE-F-001）
- 別テーブルにしない理由: 直送仕入先は既存の判定設定（判定ホライズン等）と同じく「次回取込から効く設定値」で、変更者・変更日時の扱いも同じ。件数は数件で、行ごとの履歴も要件にない

### 5.2 集計スナップショット

列・JSON の形式は変えない。**直送品の行が入らなくなる**だけ（`total_count` も直送品を含まない数になる）。

## 6. API / インターフェース設計

### 6.1 設定 API `GET/PUT /api/inventory-order-alert/settings`（既存）

| 方向 | 追加するキー | 内容 |
|---|---|---|
| GET 応答 `settings` | `directShipmentSupplierCodes: string[]` | 登録済みのコード（昇順） |
| GET 応答（トップレベル） | `directShipmentSuppliers: {code, name, status}[]` | 名前の解決結果（§4.2 VendorName）。基幹に接続できなくても GET は成功させ、`status: "unavailable"` で返す |
| PUT 要求 | `directShipmentSupplierCodes: string[]`（省略可） | 省略時は現在値を引き継ぐ。配列全体で置き換える |
| PUT 応答 | GET と同じ形 | 保存後の値と名前 |

PUT の検証（`AppSettingsUseCase.save`）:

1. 既存の項目と `directShipmentSupplierCodes` を `parse_settings_payload` で検証する（空・重複・形式。§8）
2. **新しく加わったコードだけ**（`added_since(current)`）を `LookupVendorNames` で実在確認する
   - 見つからないコードがある → 400「仕入先マスタに存在しない仕入先コードです: 9999」
   - 基幹に接続できない → 503「基幹に接続できないため仕入先コードを確認できませんでした。時間をおいて保存し直してください。」。**何も保存しない**（REQ-DSE-F-001）
   - 新しいコードがなければ基幹に問い合わせない（基幹が止まっていても、他の設定や直送仕入先の削除は保存できる）
3. 既に登録済みで仕入先マスタから消えたコードは検証しない（登録を残し、判定に使い続ける。REQ-DSE-F-001）

### 6.2 `LookupVendorNames` ポート — `domain/repositories/ports.py`

```python
class LookupVendorNames(Protocol):
    """仕入先コード → 仕入先名（見つかったものだけ）。基幹に接続できなければ VendorLookupUnavailableError。"""
    def __call__(self, codes: list[str]) -> dict[str, str]: ...
```

- 実装 `infrastructure/oracle/vendor_lookup.py`: `SELECT TRIM(VEND_CD), TRIM(VEND_ANAME) FROM M_VEND_CTRL WHERE TRIM(VEND_CD) IN (:c0, :c1, ...)`（共有 ACL の `oracle_connection` を使う。SELECT のみ）
- `OracleNotConfiguredError`・`OracleQueryError`・接続時の例外は `VendorLookupUnavailableError`（domain の例外。`domain/value_objects/errors.py` に追加）に包む
- `use_mock()` が真のとき（開発用モック）: 渡されたコードをすべて実在扱いにし、名前はコードを返す

### 6.3 設定画面 SCR-02（`templates/inventory_order_alert/settings.html`）

既存の設定フォームの最後（滞留判定日数の下）に「**直送仕入先**」の欄を追加する。

| 要素 | 内容 |
|---|---|
| 説明文 | 「品物を得意先へ直接納入し、SLIMS の倉庫を通らない仕入先です。ここに登録した仕入先の得意先品番のうち、SLIMS 在庫数がないものは一覧・CSV に表示しません。変更は次回の SLIMS 在庫 CSV 取込から反映されます。」 |
| 登録済みの一覧 | 行ごとに「コード ／ 仕入先名 ／ 削除ボタン」。名前が `not_found` なら「（仕入先マスタに見つかりません）」、`unavailable` なら「（仕入先名を取得できません）」 |
| 追加 | 仕入先コードの入力欄＋「追加」ボタン。押すと画面上の一覧に加わる（名前は保存後に表示） |
| 保存 | 既存の「保存」ボタンで他の設定とまとめて PUT する。応答で一覧を描き直す |

- `views.settings_page` は `app_settings_usecase().load_view()` から、名前の解決結果も受け取って描画する（Oracle が止まっていても画面は開ける）

### 6.4 取込（`use_cases/import_stock.py`）

```python
def execute(self, raw_bytes, *, user=None, file_name=""):
    settings = self._load_settings()          # 取込開始時点の設定を 1 回だけ読む（REQ-DSE-F-002）
    return self._import_stock(
        decode_slims_csv_bytes(raw_bytes), user=user, file_name=file_name,
        enrich_rows=lambda rows, as_of: self._enrich_rows(rows, as_of, settings),
    )

def _enrich_rows(self, rows, as_of_date, settings):
    exclusion = exclude_direct_shipment_items(rows, settings.direct_shipment_suppliers)  # ① 追加
    with_forecast = attach_demand_forecast(exclusion.kept_rows, as_of_date)               # ②〜④ 既存
    ...
```

- 設定を読む時点を「後処理の時点」から「取込の開始時点」に早める。判定ホライズンなど既存の設定も同じ時点の値になる（同じ取込の中で設定が混ざらない）
- 除いた件数は `logging` の INFO に出す（運用調査用。画面には出さない＝REQ-DSE-F-003）

### 6.5 変えないもの

一覧（`ListPage`）・CSV（`ExportCsv`）・アラート帯（`PortalDashboard`）・サマリ API・仕入先 API（`Vendors`）・詳細ダイアログ・JS は**変更しない**。スナップショットに直送品が入らないため、自動的に除かれる。

- 仕入先 API（`GET /api/inventory-order-alert/vendors`）はスナップショットから仕入先を集めるため、直送品しか持たない仕入先（丸栄豊田など）は候補に出なくなる。一覧に出る行の仕入先だけになるので、要件（REQ-DSE-F-003「候補は一覧に出す行から作る」）と合う

## 7. 既存コードへの変更点

| # | ファイル | 区分 | 変更概要 |
|---|---|---|---|
| 1 | `domain/value_objects/direct_shipment.py` | 新規 | `DirectShipmentSuppliers`・`VendorName`・`is_direct_shipment`・`exclude_direct_shipment_items`・`DirectShipmentExclusion`・既定値 |
| 2 | `domain/value_objects/errors.py` | 追加 | `VendorLookupUnavailableError` |
| 3 | `domain/value_objects/app_settings.py` | 修正 | `AppSettings`・`SettingsInput` にフィールド追加。`parse_settings_payload`・`settings_payload` に `directShipmentSupplierCodes` |
| 4 | `domain/repositories/ports.py` | 修正 | `SaveAppSettings` に `direct_shipment_suppliers` 引数。`LookupVendorNames` を追加 |
| 5 | `use_cases/import_stock.py` | 修正 | 設定を開始時に 1 回読む。後処理の最初で直送品を除く |
| 6 | `use_cases/app_settings.py` | 修正 | コンストラクタに `lookup_vendor_names`。`save` で新規コードの実在確認（戻り値の形は従来どおり）。`load_view`・`save_view`（名前の解決結果つき。設定 API の GET/PUT 応答）・`vendor_names` を追加 |
| 7 | `infrastructure/django/models`（`models.py`） | 修正 | `InventoryOrderAlertSettings.direct_shipment_supplier_codes` と既定値の関数 |
| 8 | `migrations/0016_direct_shipment_suppliers.py` | 新規 | `AddField` |
| 9 | `infrastructure/persistence/settings_repository.py` | 修正 | 読込（`from_stored`）・保存 |
| 10 | `infrastructure/oracle/vendor_lookup.py` | 新規 | `lookup_vendor_names`（M_VEND_CTRL を SELECT） |
| 11 | `interfaces/wiring.py` | 修正 | `AppSettingsUseCase` に `lookup_vendor_names` を渡す |
| 12 | `interfaces/views.py` | 修正 | `settings_page` に直送仕入先の表示用データ。`api_settings` の 503 応答と `directShipmentSuppliers` |
| 13 | `templates/inventory_order_alert/settings.html` | 修正 | 直送仕入先の欄と JS |
| 14 | `tests/` | 新規・修正 | テスト設計書（test-design.md）で定める |
| 15 | `docs/在庫発注アラート_機能仕様書.md`・`docs/在庫発注アラート_テスト仕様書.md` | 修正 | 実装完了時（§4.1 一覧・CSV の「全件」→「直送品を除く全件」、§4.2 設定、§8.10 設定 API、§6.2 対応区分） |

削除する既存コードはない。

## 8. エラーハンドリング方針

| 状況 | 振る舞い | 応答 |
|---|---|---|
| `directShipmentSupplierCodes` が配列でない・要素が文字列でない | 保存しない | 400「直送仕入先は仕入先コードの配列で指定してください。」 |
| 空のコード | 保存しない | 400「直送仕入先に空の仕入先コードは登録できません。」 |
| 重複したコード | 保存しない | 400「直送仕入先に同じ仕入先コードが重複しています: 9100」 |
| 20 文字を超えるコード | 保存しない | 400「仕入先コードは 20 文字以内で指定してください。」 |
| 新しいコードが仕入先マスタにない | 保存しない | 400「仕入先マスタに存在しない仕入先コードです: 9999」 |
| 新しいコードがあり、基幹に接続できない | 保存しない | 503「基幹に接続できないため仕入先コードを確認できませんでした。時間をおいて保存し直してください。」 |
| 設定画面の表示時に基幹に接続できない | 画面は開く。名前を「取得できません」と表示 | 200 |
| DB の保存値が壊れている（配列でない等） | `from_stored` で不正な要素を捨てて読む | — |
| 管理者以外 | 既存どおり | 画面 403・API 403 |
| 取込中の後処理で例外 | 既存どおり集計失敗として扱う（直送品の判定は純関数で、Oracle に問い合わせない） | — |

## 9. リスクと対策

| リスク | 対策 |
|---|---|
| 直送仕入先の登録を誤り、本来見るべき得意先品番が一覧から消える | SLIMS 在庫数が 1 つでもある照合単位は除かない（直送品の条件 2）。見えるのは SLIMS 在庫数が空のものだけに限られる。外せば次回取込から戻る |
| 直送品を確かめる手段がなく、誤りに気づきにくい | ユーザー判断で画面には出さない。取込ログ（INFO）に除いた件数を残し、運用で調べられるようにする |
| 照合単位の一部だけ除くと、残りの単位の在庫計算が変わる | 照合単位を丸ごと除く（連結成分ごと除くので、他の単位の構成は変わらない）。既存テストを全件そのまま通すことで確かめる（REQ-DSE-NF-003） |
| 設定を読む時点を早めたことで、既存の判定の挙動が変わる | 変わるのは「取込中に設定を変えた場合」だけ。通常の取込の結果は変わらない |
| 設定画面の表示が基幹の応答で遅くなる | 登録コード数件の IN 問い合わせ 1 回だけ。接続できないときは名前なしで描画する |

---

## レビュー履歴

<!-- design-review-l1 / l2 がこのセクションに追記する。 -->
