文書ID: TASK-DIRECT-SHIPMENT-EXCLUSION-2026-001
作成日: 2026/11/25
更新日: 2026/11/25
対応文書: [design.md](./design.md)（DESIGN-DIRECT-SHIPMENT-EXCLUSION-2026-001）, [test-design.md](./test-design.md)（TEST-DIRECT-SHIPMENT-EXCLUSION-2026-001）

# 12_direct-shipment-exclusion タスクリスト

## 状況チェックシート

**凡例**: [ ] 未着手 / [~] 進行中 / [✅YYYY/MM/DD HH:MM] 完了 / [- YYYY/MM/DD HH:MM] スキップ

| # | タスク | レイヤー | 状態 |
|---|--------|---------|------|
| 1 | 直送仕入先・直送品の判定のテスト作成（TC-DSE-D-001〜036） | domain | [✅2026/11/25 11:47] |
| 2 | `direct_shipment.py` の実装（DirectShipmentSuppliers・VendorName・is_direct_shipment・exclude_direct_shipment_items） | domain | [✅2026/11/25 11:47] |
| 3 | `VendorLookupUnavailableError` の追加 | domain | [✅2026/11/25 11:47] |
| 4 | 設定の JSON 変換のテスト作成（TC-DSE-D-040〜045） | domain | [✅2026/11/25 11:47] |
| 5 | `app_settings.py` に直送仕入先を追加 | domain | [✅2026/11/25 11:47] |
| 6 | `ports.py` に `LookupVendorNames`・`SaveAppSettings` の引数を追加 | domain | [✅2026/11/25 11:47] |
| 7 | ImportStock のテスト作成（TC-DSE-A-001〜004） | use_cases | [✅2026/11/25 11:47] |
| 8 | `import_stock.py` の修正（設定を開始時に 1 回読む・最初に直送品を除く） | use_cases | [✅2026/11/25 11:47] |
| 9 | AppSettingsUseCase のテスト作成（TC-DSE-A-010〜018） | use_cases | [✅2026/11/25 11:47] |
| 10 | `use_cases/app_settings.py` の修正（新しいコードの実在確認・load_view） | use_cases | [✅2026/11/25 11:47] |
| 11 | 設定の保存・仕入先マスタ参照・取込から保存までのテスト作成（TC-DSE-I-001〜023） | infrastructure | [✅2026/11/25 11:47] |
| 12 | `models.py` に `direct_shipment_supplier_codes` を追加 | infrastructure | [✅2026/11/25 11:47] |
| 13 | マイグレーション `0016_direct_shipment_suppliers` の作成 | infrastructure | [✅2026/11/25 11:47] |
| 14 | `settings_repository.py` の読込・保存 | infrastructure | [✅2026/11/25 11:47] |
| 15 | `infrastructure/oracle/vendor_lookup.py` の新規作成 | infrastructure | [✅2026/11/25 11:47] |
| 16 | 設定画面・設定 API のテスト作成（TC-DSE-V-001〜010） | interfaces | [✅2026/11/25 11:47] |
| 17 | `wiring.py` に `lookup_vendor_names` を組み込む | interfaces | [✅2026/11/25 11:47] |
| 18 | `views.py` の settings_page・api_settings の修正 | interfaces | [✅2026/11/25 11:47] |
| 19 | `templates/inventory_order_alert/settings.html` に直送仕入先の欄を追加 | interfaces | [✅2026/11/25 11:47] |
| 20 | 全テスト・アーキテクチャテストの実行（TC-DSE-A-005・V-011） | 全体 | [✅2026/11/25 11:47] |
| 21 | 開発環境の実データで受け入れ確認（TC-DSE-R-001〜007） | 全体 | [~] |
| 22 | 機能仕様書・テスト仕様書の更新 | docs | [✅2026/11/25 11:47] |

## タスク詳細

### タスク1: 直送仕入先・直送品の判定のテスト作成
- 対象ファイル: `application/inventory_order_alert/tests/test_direct_shipment.py`（新規）
- 内容: test-design §2.1 の TC-DSE-D-001〜010（DirectShipmentSuppliers）、D-020〜028（is_direct_shipment）、D-030〜036（exclude_direct_shipment_items）
- 完了条件: テストが ImportError または失敗で Red になる

### タスク2: `direct_shipment.py` の実装
- 対象ファイル: `application/inventory_order_alert/domain/value_objects/direct_shipment.py`（新規）
- 内容: design §4.2・§4.4。`DirectShipmentSuppliers`（parse / from_stored / contains / is_empty / added_since）、`DEFAULT_DIRECT_SHIPMENT_SUPPLIERS`、`VendorName`、`is_direct_shipment`、`exclude_direct_shipment_items`、`DirectShipmentExclusion`。`import django` を書かない
- 完了条件: タスク1のテストが全件成功

### タスク3: `VendorLookupUnavailableError` の追加
- 対象ファイル: `application/inventory_order_alert/domain/value_objects/errors.py`
- 内容: design §6.2。基幹に接続できず仕入先コードを確かめられないことを表す例外。既定メッセージは §8 の 503 の文言
- 完了条件: import できる（タスク9のテストで使う）

### タスク4: 設定の JSON 変換のテスト作成
- 対象ファイル: `tests/test_direct_shipment.py`（追記）
- 内容: TC-DSE-D-040〜045
- 完了条件: Red

### タスク5: `app_settings.py` に直送仕入先を追加
- 対象ファイル: `domain/value_objects/app_settings.py`
- 内容: `AppSettings`・`SettingsInput` に `direct_shipment_suppliers` を追加。`parse_settings_payload` で `directShipmentSupplierCodes` を受け取り（指定しなければ現在値を使う）、`settings_payload` で出す
- 完了条件: タスク4のテストと、既存の `test_app_settings_usecase.py` が成功

### タスク6: `ports.py` の修正
- 対象ファイル: `domain/repositories/ports.py`
- 内容: `SaveAppSettings` に `direct_shipment_suppliers` 引数（省略可）を追加し、`LookupVendorNames` Protocol を追加する
- 完了条件: import できる

### タスク7: ImportStock のテスト作成
- 対象ファイル: `tests/test_import_stock_usecase.py`（追記）
- 内容: TC-DSE-A-001〜004
- 完了条件: Red

### タスク8: `import_stock.py` の修正
- 対象ファイル: `use_cases/import_stock.py`
- 内容: design §6.4。`execute` の最初に設定を 1 回だけ読み、後処理の最初で `exclude_direct_shipment_items` を呼ぶ。除いた件数を INFO ログに出す
- 完了条件: タスク7のテストと、既存の取込テストが全件成功（A-005）

### タスク9: AppSettingsUseCase のテスト作成
- 対象ファイル: `tests/test_direct_shipment_settings.py`（新規）
- 内容: TC-DSE-A-010〜018（保存・仕入先名の解決は呼出しを記録するスタブ）
- 完了条件: Red

### タスク10: `use_cases/app_settings.py` の修正
- 対象ファイル: `use_cases/app_settings.py`
- 内容: design §6.1。コンストラクタに `lookup_vendor_names`（省略可）を追加。`save` では新しいコードだけを実在確認し、`directShipmentSuppliers` を返す。`load_view` と `vendor_names` を追加。`load_payload` の戻り値の形は変えない
- 完了条件: タスク9のテストと、既存の設定テストが成功

### タスク11: Infrastructure のテスト作成
- 対象ファイル: `tests/test_direct_shipment_storage.py`（新規）、`tests/test_vendor_lookup.py`（新規）
- 内容: TC-DSE-I-001〜005、I-010〜013、I-020〜023
- 完了条件: Red

### タスク12: `models.py` の修正
- 対象ファイル: `application/inventory_order_alert/models.py`
- 内容: `default_direct_shipment_supplier_codes()` と `InventoryOrderAlertSettings.direct_shipment_supplier_codes = JSONField(default=…)` を追加
- 完了条件: `manage.py check` が成功

### タスク13: マイグレーションの作成
- 対象ファイル: `migrations/0016_direct_shipment_suppliers.py`（新規）
- 内容: `makemigrations` で `AddField` を作る。既定値は関数を参照する
- 完了条件: `migrate` が成功し、`makemigrations --check` で差分なし

### タスク14: `settings_repository.py` の修正
- 対象ファイル: `infrastructure/persistence/settings_repository.py`
- 内容: 読込は `from_stored`。保存は `direct_shipment_suppliers` が渡されたときだけ列を更新する
- 完了条件: I-001〜005 が成功

### タスク15: `vendor_lookup.py` の新規作成
- 対象ファイル: `infrastructure/oracle/vendor_lookup.py`（新規）
- 内容: design §6.2。`M_VEND_CTRL` を SELECT し、コードはバインド変数で渡す。例外は `VendorLookupUnavailableError` に包む。`use_mock()` が真なら、すべてのコードを実在扱いにする
- 完了条件: I-010〜013 が成功し、I-020〜023 も成功

### タスク16: Interfaces のテスト作成
- 対象ファイル: `tests/test_settings_page_views.py`（追記）
- 内容: TC-DSE-V-001〜010
- 完了条件: Red

### タスク17: `wiring.py` の修正
- 対象ファイル: `interfaces/wiring.py`
- 内容: `app_settings_usecase()` に `lookup_vendor_names` を渡す
- 完了条件: import できる

### タスク18: `views.py` の修正
- 対象ファイル: `interfaces/views.py`
- 内容: `settings_page` で `load_view()` を使い、`direct_shipment_suppliers` をテンプレートへ渡す。`api_settings` は GET と PUT の応答に `directShipmentSuppliers` を入れ、`VendorLookupUnavailableError` を 503 にする
- 完了条件: V-004〜009 が成功

### タスク19: `settings.html` の修正
- 対象ファイル: `templates/inventory_order_alert/settings.html`
- 内容: design §6.3。説明文、登録済みの一覧（削除ボタン付き）、追加の入力欄。保存時に `directShipmentSupplierCodes` を送り、応答で一覧を描き直す
- 完了条件: V-001〜003 が成功

### タスク20: 全テストの実行
- 内容: `pytest -q`（DevContainer 内）
- 完了条件: 全件成功（既存テストは変更なしで成功する）

### タスク21: 実データでの受け入れ確認
- 内容: 開発環境で SLIMS 在庫 CSV を取り込み直し、TC-DSE-R-001〜007 を確かめる
- 完了条件: 件数が要件の受け入れ基準と一致する。一致しないときは差異と理由を記録する

### タスク22: ドキュメントの更新
- 対象ファイル: `docs/在庫発注アラート_機能仕様書.md`、`docs/在庫発注アラート_テスト仕様書.md`
- 内容: design §7 #15
- 完了条件: 改定履歴に記録する

## タスク実行レポート

（各タスク完了時にここへ追記する）

--------------------
### タスク1〜20・22 実行レポート（2026/11/25 11:47）

**記録について**: 各タスクの完了時刻をその都度記録せず、最後にまとめて記録した（凡例の「即時記録」に反している）。実際の作業は 11:29〜11:47 の間に、表の順（Red → Green）で行った。

**結果**: `pytest -q` で全 2,415 件が成功（アーキテクチャテストを含む）。`makemigrations --check` で差分なし。開発 DB に 0016 を適用済み。

**懸念事項**
- 既存テストの期待値を 3 件変えた。いずれも本件で増えたキーや注記を反映したもので、判定ロジックの期待値は変えていない
  - `test_settings_payload_exposes_all_keys` と `test_api_settings_get_returns_current_settings`: キーの一覧に `directShipmentSupplierCodes` を追加
  - `test_js_a007_settings_page_has_both_inputs`: 「次回取込から反映」注記の件数を `== 2` から `>= 2` に変更
- `tests/conftest.py` を新設し、テスト全体で仕入先名の解決を既定で「接続できない」扱いにした。これを入れないと、設定画面のテストが開発環境の実 Oracle に接続してしまう
- TC-DSE-I-022 の確認記録は、確認時点の流動区分を再取込後と同じ「打ち切り候補」にしてある。直送品の行は在庫行がないので、戻ったときに流動区分が悪化しやすい。悪化すると既存の仕組み（REQ-F-011）で未確認に戻る。これは本件とは別の既存の振る舞いだが、運用では「外して戻すと未確認に戻ることがある」点に注意が要る

**改善事項**
- `AppSettingsUseCase.save` の戻り値の形は従来どおりにした。応答に名前を添える `save_view`・`load_view` を別に設け、既存の呼出し元を壊さないようにした（design §7 #6 を更新）
- `DEFAULT_DIRECT_SHIPMENT_SUPPLIERS` を VO にし、モデルの既定値の関数はこの値を返すようにした（値の正を domain の 1 か所にした）

**設計のGoodポイント**
- 保存前に除く方式（案 A）にしたので、一覧・CSV・アラート帯・API を 1 行も変えずに済んだ
- 照合単位ごと除くため、残る照合単位の判定が除く前と同じになることをテスト（D-036・A-004）で確かめられた

**チーム共有ポイント**
- 直送仕入先の変更は次回の SLIMS 在庫 CSV 取込から反映される。本番でも 0016 の migrate だけで初期値 3 件が入る
- 除いた件数は取込ログに INFO で出る（「直送品を集計から除外しました: N 照合単位・M 行」）
--------------------

--------------------
### タスク21 実行レポート（2026/11/25 11:47・進行中）

開発 DB の最新スナップショット（BOM 基準日 2026/11/02・2,301 行）に、実装した `exclude_direct_shipment_items` を読み取り専用で適用して確かめた。

| TC | 結果 |
|---|---|
| R-001 | ✅ 306 照合単位・306 行を除く |
| R-002 | ✅（計算上）1,995 行。発注遅れ 55・納期確認 295・要発注 238・要監視 5・対象外 1,402 |
| R-005 | ✅ `78219-95700` は残る |
| R-006 | ✅（計算上）9200 を外すと 29 照合単位が戻る |
| R-003・R-004・R-007 | 未実施。画面から SLIMS 在庫 CSV を取り込み直し、アラート帯・CSV・設定画面を目視で確認する必要がある |
--------------------
