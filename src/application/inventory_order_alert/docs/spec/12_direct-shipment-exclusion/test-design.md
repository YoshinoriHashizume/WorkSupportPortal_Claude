# テスト設計書: 直送品を在庫発注アラートの対象から外す

文書ID: TEST-DIRECT-SHIPMENT-EXCLUSION-2026-001
作成日: 2026/11/25
更新日: 2026/11/25（実装に合わせて D-010・A-018 の入力を補正）
対応文書: [design.md](./design.md)（DESIGN-DIRECT-SHIPMENT-EXCLUSION-2026-001）、[requirements.md](./requirements.md)（REQ-DIRECT-SHIPMENT-EXCLUSION-2026-001）
テスト戦略reference: test-strategy version 1.1
テストフレームワークreference: django-pytest version 1.0

---

## 1. テスト戦略

### 1.1 テスト対象のスコープ

| 対象 | 内容 |
|---|---|
| 対象 | 直送仕入先（V-240）の値の検証・保存・仕入先名の解決、直送品（T-212）の判定と除外、取込の後処理への組み込み、設定画面・設定 API |
| 回帰で確かめる | 直送品でない照合単位の需要予測・流動区分・対応区分が変わらないこと（REQ-DSE-NF-003）。**既存テストを全件そのまま通す** |
| 対象外 | 一覧・CSV・アラート帯・サマリ API・詳細ダイアログの読み取り処理（design §6.5 で変更しない。既存テストで担保する）。基幹（実 Oracle）への接続そのもの（偽の接続で代替する） |

### 1.2 テストレイヤーの方針

| レイヤー | テスト種別 | テスト方針 | DB依存 |
|---|---|---|---|
| Domain | 単体 | `DirectShipmentSuppliers` の生成・不正値・等価性、`is_direct_shipment`・`exclude_direct_shipment_items` の判定、設定の JSON 変換 | 不要 |
| Application | 単体 | `ImportStock`・`AppSettingsUseCase` の流れ。取込ポート・設定の読込・保存・仕入先名の解決は偽物（スタブ）に差し替える。ドメインモデルは実物を使う | 不要 |
| Infrastructure | 結合 | 設定の保存・読込（PostgreSQL）、既定値、壊れた保存値、仕入先マスタ参照（偽の Oracle 接続）、取込から保存までの流れ（Oracle の集計は偽物） | 必要（参照は不要） |
| Interfaces | 結合 | 設定画面・設定 API の HTTP 応答、権限。仕入先名の解決は wiring の参照先を差し替える | 必要 |

### 1.3 テスト優先順位

1. Domain（TC-DSE-D）: 直送品の判定条件が本件の核心
2. Application（TC-DSE-A）: 除く位置（後処理の最初）と、設定を読む時点
3. Infrastructure（TC-DSE-I）: 初期値・保存・確認記録が残ること
4. Interfaces（TC-DSE-V）: 設定画面・API の応答
5. 実データでの受け入れ確認（TC-DSE-R）: 開発環境のスナップショットで件数を確かめる

### 1.4 TDD方針

CLAUDE.md に従い Phase 5 は TDD で進める。タスクごとに **Red（本書のテストケースを書いて失敗させる）→ Green（最小の実装で通す）→ Refactor** の順に回し、Domain → Application → Infrastructure → Interfaces の順に積み上げる。

## 2. テストケース一覧

### 2.1 Domain層テスト（`tests/test_direct_shipment.py`）

#### バリューオブジェクト: DirectShipmentSuppliers

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-DSE-D-001 | 前後の空白を除き昇順に並べて生成できる | `parse(["9250", " 9100 ", "9200"])` | `codes == ("9100", "9200", "9250")` | F-001 | 高 |
| TC-DSE-D-002 | 0 件で生成でき、空と判定される | `parse([])` | `is_empty is True`、`codes == ()` | F-001 | 高 |
| TC-DSE-D-003 | 空のコードは拒否する | `parse(["9100", ""])`／`parse(["  "])` | `ValueError`「直送仕入先に空の仕入先コードは登録できません。」 | F-001 | 高 |
| TC-DSE-D-004 | 重複したコードは拒否する（空白を除いた後で比べる） | `parse(["9100", " 9100"])` | `ValueError`「…重複しています: 9100」 | F-001 | 高 |
| TC-DSE-D-005 | 20 文字のコードは受け付け、21 文字は拒否する | `"A" * 20`／`"A" * 21` | 前者は生成、後者は `ValueError`「仕入先コードは 20 文字以内で…」 | F-001 | 中 |
| TC-DSE-D-006 | 保存値の不正な要素を捨てて読む | `from_stored(["9100", "", 1, None, "9100", " 9250 "])` | `codes == ("9100", "9250")`。例外を出さない | F-001 | 中 |
| TC-DSE-D-007 | 保存値が配列でなければ 0 件として読む | `from_stored("9100")`／`from_stored(None)`／`from_stored({})` | `is_empty is True`。例外を出さない（除かない＝表示する側に倒す） | F-001 | 中 |
| TC-DSE-D-008 | 新しく加わったコードだけを返す | 新 `("9100", "9250")`、旧 `("9100", "9200")` | `added_since(旧) == ("9250",)` | F-001 | 高 |
| TC-DSE-D-009 | 同じコードの集合は等しい・生成後に変更できない | `parse(["9200","9100"]) == parse(["9100","9200"])`、`codes` への代入 | 等しい。代入は `FrozenInstanceError` | F-001 | 低 |
| TC-DSE-D-010 | 既定値は 3 件 | `DEFAULT_DIRECT_SHIPMENT_SUPPLIERS.codes` | `("9100", "9200", "9250")` | F-001 | 高 |

#### ドメインサービス: is_direct_shipment

照合単位 1 つ分の行。既定の直送仕入先は `9100`・`9250`。

| # | テストケース | 入力（照合単位の行） | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-DSE-D-020 | 仕入先がすべて直送仕入先で SLIMS 在庫数がすべて空なら直送品 | 2 行とも `level1_vend_cd="9100"`、`stock_qty=""` | True | F-002 | 高 |
| TC-DSE-D-021 | SLIMS 在庫数が None でも空とみなす | `stock_qty=None` | True | F-002 | 中 |
| TC-DSE-D-022 | SLIMS 在庫数が数量 0 の得意先品番があれば直送品にしない | 1 行が `stock_qty=0`（int）、もう 1 行が `Decimal("0")`、他は `""` | False（両方とも） | F-002 | 高 |
| TC-DSE-D-023 | SLIMS 在庫数がある得意先品番があれば直送品にしない | 1 行が `stock_qty=120` | False | F-002 | 高 |
| TC-DSE-D-024 | 直送仕入先とそうでない仕入先が混在すれば直送品にしない | `9100` と `9146` | False | F-002 | 高 |
| TC-DSE-D-025 | 仕入先が空の行を含めば直送品にしない | `9100` と `""` | False | F-002 | 高 |
| TC-DSE-D-026 | 仕入先コードの前後の空白は除いて比べる | `level1_vend_cd=" 9100 "` | True | F-002 | 中 |
| TC-DSE-D-027 | 直送仕入先が 0 件なら直送品にしない | 直送仕入先 `()` | False | F-001・F-002 | 高 |
| TC-DSE-D-028 | 行が 0 件なら直送品にしない | `[]` | False | F-002 | 低 |

#### ドメインサービス: exclude_direct_shipment_items

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-DSE-D-030 | 直送品の照合単位の行だけを除き、残りは並び順のまま返す | 行 [N1（9146・在庫あり）, D1（9100・空・得意先 A）, D2（9100・空・得意先 B・D1 と同じ得意先品番）, N2（9133・空）] | `kept_rows == [N1, N2]`、`excluded_row_count == 2`、`excluded_unit_count == 1` | F-002・F-003 | 高 |
| TC-DSE-D-031 | 仕入先品番を共有して 1 つの照合単位になる複数の得意先品番は、まとめて除く | 得意先品番 X・Y が同じ（仕入先品番, 9100）を共有、どちらも空 | X・Y の行がすべて除かれる | F-002 | 高 |
| TC-DSE-D-032 | 同じ照合単位の得意先品番の 1 つに SLIMS 在庫数があれば、単位ごと残す | 同上で Y だけ `stock_qty=10` | X・Y とも残る | F-002 | 高 |
| TC-DSE-D-033 | 得意先品番が空の行は、その行だけで判定する | `item_cd=""` の行 2 つ（9100・空／9146・空） | 前者は除き、後者は残す | F-002 | 中 |
| TC-DSE-D-034 | 直送仕入先が 0 件なら入力をそのまま返す | 直送仕入先 `()`、TC-D-030 の行 | `kept_rows` が入力と同じ内容・順序、件数 0 | F-001・NF-003 | 高 |
| TC-DSE-D-035 | 入力の行と一覧を書き換えない | TC-D-030 の行 | 呼出し後も入力の list の長さ・各 dict が変わっていない | NF-002 | 中 |
| TC-DSE-D-036 | 直送品を除いても、残る照合単位の需要予測・対応区分は変わらない | 直送単位と通常単位（内示・発注残あり）を含む行。除外あり／なしで `attach_demand_forecast` → `attach_response_class` を通す | 通常単位の `stockout_date`・`order_deadline`・`response_class`・`demand_forecast_stock_total`・`reconciliation_unit_key` が一致 | NF-003 | 高 |

#### 設定の JSON 変換（`app_settings.py`。`tests/test_direct_shipment.py` に置く）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-DSE-D-040 | 既定の AppSettings は既定の直送仕入先を持つ | `AppSettings()` | `direct_shipment_suppliers == DEFAULT_DIRECT_SHIPMENT_SUPPLIERS` | F-001 | 高 |
| TC-DSE-D-041 | 設定の JSON 表現に直送仕入先のコードが出る | `settings_payload(AppSettings())` | `payload["directShipmentSupplierCodes"] == ["9100", "9200", "9250"]` | F-001 | 高 |
| TC-DSE-D-042 | 直送仕入先を指定しなければ現在値を引き継ぐ | `parse_settings_payload({"warningDays": 100}, current=…(9100))` | 直送仕入先が `("9100",)` のまま | F-001 | 高 |
| TC-DSE-D-043 | 直送仕入先を配列全体で置き換える | `{"directShipmentSupplierCodes": ["9250"]}` | `("9250",)` | F-001 | 高 |
| TC-DSE-D-044 | 空の配列で 0 件にできる | `{"directShipmentSupplierCodes": []}` | `is_empty is True` | F-001 | 中 |
| TC-DSE-D-045 | 配列でない・文字列でない要素は拒否する | `"9100"`／`[9100]`／`[None]` | `ValueError`「直送仕入先は仕入先コードの配列で指定してください。」 | F-001 | 高 |

### 2.2 Application層テスト

#### ImportStock（`tests/test_import_stock_usecase.py` に追加）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-DSE-A-001 | 取込の後処理で直送品の行を除いてから対応区分を付ける | 偽の取込ポートで `enrich_rows` を取り出し、直送行（9100・空）と通常行を渡す。設定の直送仕入先 `("9100",)` | 戻り値は通常行だけ。通常行に `response_class`・`reconciliation_unit_key` が付く | F-002・F-003 | 高 |
| TC-DSE-A-002 | 設定は取込の開始時に 1 回だけ読み、後処理はその値を使う | 設定の読込スタブ: 1 回目 `("9100",)`、2 回目以降 `()`。呼出し順を記録する | 読込は 1 回で、取込ポートを呼ぶ前。後処理で直送行が除かれる（1 回目の値） | F-002 | 高 |
| TC-DSE-A-003 | 設定の読込を渡さなければ既定の直送仕入先を使う | `ImportStock(fake_import)`、9100 の空行 | その行は除かれる | F-001 | 中 |
| TC-DSE-A-004 | 直送仕入先が 0 件なら従来と同じ行が残る | 直送仕入先 `()`、9100 の空行を含む | すべての行が残り、各行の対応区分が本機能の導入前と同じ | NF-003 | 高 |
| TC-DSE-A-005 | 既存の取込ユースケースのテストが変更なしで通る | 既存の `test_import_stock_usecase.py` の全テスト | 全件成功 | NF-003 | 高 |

#### AppSettingsUseCase（`tests/test_direct_shipment_settings.py`）

`lookup_vendor_names` は偽物にし、渡されたコードを記録する。

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-DSE-A-010 | 新しいコードだけを仕入先マスタで確かめて保存する | 現在 `("9100","9200")`、要求 `["9100","9200","9250"]`、解決 `{"9250": "丸栄豊田（福岡）"}` | 解決は `["9250"]` だけで呼ばれる。保存に `("9100","9200","9250")` が渡る | F-001 | 高 |
| TC-DSE-A-011 | 仕入先マスタにないコードは保存しない | 要求に `"9999"`、解決 `{}` | `ValueError`「仕入先マスタに存在しない仕入先コードです: 9999」。保存は呼ばれない | F-001 | 高 |
| TC-DSE-A-012 | 基幹に接続できなければ保存しない | 新しいコードあり、解決が `VendorLookupUnavailableError` | 同じ例外が上がる。保存は呼ばれない | F-001 | 高 |
| TC-DSE-A-013 | コードを外すだけなら仕入先マスタに問い合わせない | 現在 `("9100","9200")`、要求 `["9100"]` | 解決は呼ばれない。保存に `("9100",)` が渡る | F-001 | 高 |
| TC-DSE-A-014 | 直送仕入先を指定しない保存は、基幹が止まっていても成功する | 要求 `{"warningDays": 100}`、解決は呼ばれると例外 | 保存が成功し、直送仕入先は現在値のまま | F-001 | 高 |
| TC-DSE-A-015 | 登録済みで仕入先マスタから消えたコードは確かめず残す | 現在 `("9100","8888")`、要求 `["9100","8888"]`、解決 `{}` | 解決は呼ばれない（新しいコードなし）。保存が成功する | F-001 | 中 |
| TC-DSE-A-016 | 表示用に仕入先名を解決し、見つからないものを区別する | 登録 `("9100","8888")`、解決 `{"9100": "丸栄豊田"}` | `[VendorName("8888","", "not_found"), VendorName("9100","丸栄豊田","found")]` | F-001 | 高 |
| TC-DSE-A-017 | 基幹に接続できなくても表示用データを返す | 解決が `VendorLookupUnavailableError` | 例外を出さず、すべて `status="unavailable"` | F-001 | 高 |
| TC-DSE-A-018 | 保存の応答に保存後のコードと仕入先名が入る | TC-A-010 の保存（`save_view`） | 応答の `settings.directShipmentSupplierCodes` と `directShipmentSuppliers`（名前つき） | F-001 | 中 |

### 2.3 Infrastructure層テスト

#### 設定の保存（`tests/test_direct_shipment_storage.py`・`@pytest.mark.django_db`）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-DSE-I-001 | 設定行を新しく作ると既定の直送仕入先が入る | 設定行のない状態で `load_app_settings()` | `("9100","9200","9250")` | F-001 | 高 |
| TC-DSE-I-002 | 既定値の関数とマイグレーションが既定の 3 件を指す | `InventoryOrderAlertSettings._meta.get_field("direct_shipment_supplier_codes").default()`、`0016` の `AddField` の既定値 | `["9100","9200","9250"]`。マイグレーションも同じ関数を参照 | F-001 | 高 |
| TC-DSE-I-003 | 直送仕入先を保存すると読み戻せ、変更者と日時が残る | `save_app_settings(..., direct_shipment_suppliers=parse(["9250"]), updated_by=admin)` | 読込が `("9250",)`。`updated_by == admin`、`updated_at` が更新される | F-001・NF-004 | 高 |
| TC-DSE-I-004 | 直送仕入先を渡さない保存では値を変えない | `save_app_settings(warning_days=100, ...)`（直送仕入先なし） | 直送仕入先は保存前のまま | F-001 | 中 |
| TC-DSE-I-005 | DB の保存値が壊れていても読める | 列に `"abc"`／`[1, "", "9100"]` を直接書き込む | 例外なし。前者は 0 件、後者は `("9100",)` | F-001 | 中 |

#### 仕入先マスタ参照（`tests/test_vendor_lookup.py`。DB 不要）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-DSE-I-010 | 指定したコードの仕入先名を返す | 偽の接続が `[("9100","丸栄豊田")]` を返す。`lookup_vendor_names(["9100","9999"])` | `{"9100": "丸栄豊田"}`。SQL は `SELECT` で始まり `M_VEND_CTRL` を参照、コードはバインド変数で渡す | F-001・NF-001 | 高 |
| TC-DSE-I-011 | コードが 0 件なら基幹に接続しない | `lookup_vendor_names([])` | `{}`。接続は開かれない | F-001 | 中 |
| TC-DSE-I-012 | 基幹の未設定・問い合わせ失敗・接続失敗は「接続できない」に包む | `oracle_connection` が `OracleNotConfiguredError`／`OracleQueryError`／`ConnectionError` を出す | いずれも `VendorLookupUnavailableError` | F-001 | 高 |
| TC-DSE-I-013 | 開発用モックではすべて実在扱いにする | `use_mock()` が真 | `{"9100": "9100", "9999": "9999"}`。接続は開かれない | F-001 | 低 |

#### 取込から保存まで（`tests/test_direct_shipment_storage.py`・`@pytest.mark.django_db`）

`run_summary_aggregation` の `oracle_connection` と `build_list_rows` を偽物にし、直送行 1・通常行 1 を返させる。後処理は `ImportStock` の `enrich_rows` を使う。

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-DSE-I-020 | スナップショットに直送品の行が保存されず、件数にも入らない | 上記 | `snapshot.rows` は通常行 1 件のみ。`total_count == 1` | F-003・F-004 | 高 |
| TC-DSE-I-021 | 直送品になった得意先品番の確認記録は消えない | 直送行と同じ（得意先コード, 得意先品番）の確認記録（確認中・メモ 1 件）を事前に作る | 取込後も確認記録は確認中のまま、メモも残る | F-006 | 高 |
| TC-DSE-I-022 | 直送仕入先から外して再取込すると、行が戻り確認記録が引き継がれる | I-021 の後、直送仕入先を `()` にして再取込 | スナップショットに直送だった行が戻り、表示時の確認状態が確認中 | F-005・F-006 | 高 |
| TC-DSE-I-023 | 取込の後処理は基幹への問い合わせを増やさない | I-020 の取込で偽の接続の `cursor()` 呼出し回数を数える | 直送仕入先あり／なしで回数が同じ | NF-001 | 中 |

### 2.4 Interfaces層テスト（`tests/test_settings_page_views.py` に追加・`@pytest.mark.django_db`）

仕入先名の解決は `interfaces.wiring` の参照先を `monkeypatch` で差し替える。

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 |
|---|---|---|---|---|---|
| TC-DSE-V-001 | 設定画面に直送仕入先の欄が、コード・仕入先名・次回取込の注記つきで出る | 管理者、解決 `{"9100":"丸栄豊田","9200":"テクノス工場","9250":"丸栄豊田（福岡）"}` | 200。HTML に 3 件のコードと名前、「次回の SLIMS 在庫 CSV 取込から反映」 | F-001・F-005 | 高 |
| TC-DSE-V-002 | 基幹に接続できなくても設定画面は開き、名前を取得できない旨を出す | 解決が `VendorLookupUnavailableError` | 200。「（仕入先名を取得できません）」 | F-001 | 高 |
| TC-DSE-V-003 | 仕入先マスタにないコードは見つからない旨を出す | 登録 `("8888",)`、解決 `{}` | 「（仕入先マスタに見つかりません）」 | F-001 | 中 |
| TC-DSE-V-004 | 設定 API の GET に直送仕入先のコードと名前が入る | GET | `settings.directShipmentSupplierCodes` と `directShipmentSuppliers` | F-001 | 高 |
| TC-DSE-V-005 | 設定 API の PUT で直送仕入先を保存できる | PUT `{"directShipmentSupplierCodes": ["9100","9250"]}` | 200。再 GET で `["9100","9250"]` | F-001 | 高 |
| TC-DSE-V-006 | 重複・空・配列でない指定は 400 | PUT `["9100","9100"]`／`[""]`／`"9100"` | 400 と §8 のメッセージ。保存されない | F-001 | 高 |
| TC-DSE-V-007 | 仕入先マスタにないコードは 400 | PUT `["9999"]`、解決 `{}` | 400「仕入先マスタに存在しない仕入先コードです: 9999」 | F-001 | 高 |
| TC-DSE-V-008 | 基幹に接続できず新しいコードを確かめられなければ 503 で保存しない | PUT `["9100","9999"]`、解決が `VendorLookupUnavailableError` | 503「基幹に接続できないため…」。再 GET で値が変わっていない | F-001 | 高 |
| TC-DSE-V-009 | 管理者以外は設定画面・設定 API を使えない | 一般ユーザーで GET 画面／GET API／PUT API | 403。値は変わらない | NF-004 | 高 |
| TC-DSE-V-010 | 本機能より前のスナップショットは全行を表示する | 9100・SLIMS 在庫数が空の行を含むスナップショットを直接作り、一覧画面を開く | その行も一覧データに含まれ、例外が出ない | F-005 | 高 |
| TC-DSE-V-011 | アーキテクチャテストが通る | `config/tests/test_clean_architecture.py` | 全件成功（views は wiring 経由のみ。domain・use_cases に django なし） | NF-002 | 高 |

### 2.5 実データでの受け入れ確認（TC-DSE-R。開発環境・手動）

開発環境のスナップショット（BOM 基準日 2026/11/02）と同じ SLIMS 在庫 CSV を取り込み直して確かめる。本番では件数が異なる。

| # | 確認内容 | 期待結果 | 対応（要件の受け入れ基準） |
|---|---|---|---|
| TC-DSE-R-001 | 直送品として除かれた件数（取込ログ INFO） | 306 照合単位・306 行 | #3 |
| TC-DSE-R-002 | 一覧の件数サマリ | 全 1,995 行。発注遅れ 55・納期確認 295・要発注 238・要監視 5・対象外 1,402 | #4 |
| TC-DSE-R-003 | アラート帯の件数 | 一覧の件数サマリと一致 | #5 |
| TC-DSE-R-004 | CSV の行数と列 | 1,995 行。列の構成は導入前と同じ | #6 |
| TC-DSE-R-005 | `78219-95700` | 一覧に出て、通常どおり判定されている | #7 |
| TC-DSE-R-006 | 設定から `9200` を外して再取込 | テクノス工場の 29 単位が一覧・CSV に戻る | #8 |
| TC-DSE-R-007 | 設定画面で追加・削除・保存 | 名前が並ぶ。存在しないコードは保存できない | #1・#2 |

## 3. テストデータ

### 3.1 正常系テストデータ

| 名前 | 内容 |
|---|---|
| 直送行 D1 | `item_cd="15D126-0020"`、`cust_code="308"`、`level1_item_cd="15D126-0020-9100"`、`level1_vend_cd="9100"`、`level1_vend_name="丸栄豊田"`、`stock_qty=""` |
| 直送行 D2 | D1 と同じ `item_cd`・仕入先品番で `cust_code="191"`（同じ照合単位の別得意先） |
| 通常行 N1 | `item_cd="062432-0680"`、`level1_vend_cd="9146"`、`stock_qty=11165`、内示 `unconfirmed_order_daily` に数日分 |
| 通常行 N2 | `item_cd="079351-0810"`、`level1_vend_cd="9133"`、`stock_qty=""`（直送仕入先でないので残る） |
| 例外行 E1 | `item_cd="78219-95700"`、`level1_vend_cd="9100"`、`stock_qty=40`（直送仕入先だが SLIMS 在庫数あり） |
| 仕入先名 | `{"9100": "丸栄豊田", "9200": "テクノス工場", "9250": "丸栄豊田（福岡）"}` |

行は既存のテストと同じく、`build_list_rows` が返す dict の形で作る（必要なキーのみ。不足キーは後処理の既定値に任せる）。

### 3.2 異常系テストデータ

| 名前 | 内容 |
|---|---|
| 不正な直送仕入先の指定 | `""`、`"  "`、`["9100","9100"]`、`[" 9100","9100"]`、`"A"*21`、`"9100"`（配列でない）、`[9100]`、`[None]` |
| 壊れた保存値 | `"abc"`、`None`、`{}`、`[1, "", None, "9100"]` |
| 基幹の例外 | `OracleNotConfiguredError`、`OracleQueryError`、`ConnectionError` |
| 仕入先マスタにないコード | `"9999"`（新規）、`"8888"`（登録済みで消えた想定） |

## 4. 境界値・異常系のカバレッジ

### 4.1 境界値テスト

| 対象 | 境界値 | テストケース |
|---|---|---|
| 直送仕入先の件数 | 0 件／1 件／3 件 | D-002・D-027・D-034・D-044／D-043／D-010・I-001 |
| 仕入先コードの長さ | 0・20・21 文字 | D-003・D-005 |
| SLIMS 在庫数 | 空（`""`・None）／0（int・Decimal）／正 | D-020・D-021／D-022／D-023 |
| 照合単位の行数 | 0 行／1 行／複数の得意先・得意先品番 | D-028／D-033／D-030・D-031 |

### 4.2 異常系テスト

| 対象 | 異常ケース | 期待される振る舞い |
|---|---|---|
| 設定 API | 重複・空・配列でない・長すぎ | 400・保存しない（D-003〜D-005・D-045・V-006） |
| 設定 API | 仕入先マスタにない新しいコード | 400・保存しない（A-011・V-007） |
| 設定 API | 基幹に接続できない（新しいコードあり） | 503・保存しない（A-012・V-008） |
| 設定 API | 基幹に接続できない（新しいコードなし） | 保存できる（A-013・A-014） |
| 設定画面 | 基幹に接続できない | 画面は開き、名前を取得できない旨（A-017・V-002） |
| 保存値 | 壊れている | 例外なく読み、除かない側に倒す（D-006・D-007・I-005） |
| 権限 | 管理者以外 | 403（V-009） |

### 4.3 エッジケース

| ケース | テストケース |
|---|---|
| 取込の途中で設定が変わる（同時実行） | A-002（設定は開始時に 1 回だけ読む） |
| 直送仕入先と通常の仕入先が混在する照合単位 | D-024 |
| 直送仕入先の品番に SLIMS 在庫数がある | D-023・D-032・R-005 |
| 直送品の確認記録 | I-021・I-022 |
| 旧スナップショット | V-010 |
| 直送品でない照合単位への影響 | D-036・A-004・A-005（回帰） |

## 5. テスト環境

### 5.1 テスト実行コマンド

DevContainer（`web-app-worksupportportal`）内の `/django_app/src` で実行する。

```bash
# 本件のテストのみ
pytest application/inventory_order_alert/tests/test_direct_shipment.py \
       application/inventory_order_alert/tests/test_direct_shipment_settings.py \
       application/inventory_order_alert/tests/test_direct_shipment_storage.py \
       application/inventory_order_alert/tests/test_vendor_lookup.py -q

# 在庫発注アラートの全テスト（回帰。NF-003）
pytest application/inventory_order_alert/tests -q

# コミット前（全アプリ・アーキテクチャテストを含む）
pytest -q
```

### 5.2 テストデータの準備方法

- Domain・Application: テスト内で dict の行を組み立てる小さな関数（`_row(**overrides)`）を各テストファイルに置く。外部ファイルは使わない
- 仕入先名の解決・設定の読込と保存: 呼出しを記録するスタブ関数で差し替える
- Infrastructure・Interfaces: `pytest-django` の `db`・`client`・`admin_user`・`django_user_model` を使う。基幹は `monkeypatch` で `oracle_connection`・`build_list_rows`・wiring の `lookup_vendor_names` を差し替える
- 実データ確認（TC-DSE-R）: 開発環境の SLIMS 在庫 CSV を画面から取り込み、件数は本件の調査で使った集計スクリプトで確かめる
