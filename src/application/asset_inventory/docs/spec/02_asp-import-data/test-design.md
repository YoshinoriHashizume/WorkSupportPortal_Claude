# テスト設計書: ASP 取り込み用データ作成

文書ID: TEST-ASP-IMPORT-DATA-2026-001
作成日: 2026/08/26
更新日: 2026/08/27
対応文書: `application/asset_inventory/docs/spec/02_asp-import-data/design.md`（DESIGN-ASP-IMPORT-DATA-2026-001）／ `requirements.md`（REQ-ASP-IMPORT-DATA-2026-001）
テスト戦略reference: test-strategy version 1.1（updated 2026-04-25）
テストフレームワークreference: django-pytest version 1.0（updated 2026-04-11）

---

## 1. テスト戦略

### 1.1 テスト対象のスコープ

**テスト対象**（機能設計書 §7.1 の変更対象ファイル）:

| 対象 | 位置 | テスト種別 |
|---|---|---|
| ASP 取り込み用データのバリューオブジェクト群 | `domain/value_objects/asp_import.py` | 単体（Domain） |
| 突合結果スナップショットの `site_warning` とスナップショット読み出し | `domain/value_objects/reconcile_cache.py` | 単体（Domain） |
| 突合結果行の追加コード部品（`manager_code` / `usage_category_code` / `manufacturer_code`）の取得・保持・セッション往復 | `domain/repositories/ports.py` / `domain/value_objects/row_display.py` / `domain/value_objects/reconcile_cache.py` | 単体（Domain） |
| 縮退結果の保存・不採用（DD-02） | `domain/value_objects/reconcile_data.py` | 単体（Domain） |
| 取り込み用データ作成ユースケース | `use_cases/export_asp_import.py` | 単体（Application・リポジトリはモック） |
| 出力エンドポイントとボタンの活性判定 | `interfaces/views.py` / `templates/asset_inventory/list.html` | 結合（Interfaces・Django テストクライアント） |

**テスト対象外**:

| 対象 | 理由 |
|---|---|
| `infrastructure/` 配下 | 本機能で**変更しない**（DD-01 により desknet's ゲートウェイに依存しないため、新規の外部通信が無い）。既存の `test_desknet_client.py` の範囲を変えない |
| PostgreSQL のテーブル | 新設・変更ともになし（REQ-NF-002） |
| `static/js/asset-inventory-list.js` の挙動 | 本プロジェクトに JS の自動テスト基盤が無いため、**手動確認**とする（§4.4） |
| ASP 本体への貼り付け結果（C-11） | 外部システムのため**受け入れ確認**（利用者による実機確認）とする |
| desknet's / Oracle の実接続 | 既存方針どおりモック既定 |

### 1.2 テストレイヤーの方針

| レイヤー | テスト種別 | テスト方針 | DB依存 |
|---|---|---|---|
| Domain | 単体テスト | Django・DB に依存しない純粋な関数／VO のテスト。**モックを使わない**（実際の値オブジェクトを組み立てて検証する）。`ReconcileRow` はテストヘルパー `_row()` で組み立てる | なし |
| Application（use_cases） | 単体テスト | ユースケースを直接インスタンス化し、**セッションは `dict` で代用**する。desknet's ゲートウェイは**渡さない**（DD-01。渡す口が無いことをもって REQ-NF-003 を保証する）。ドメインモデルはモック化しない | なし |
| Infrastructure | — | 本機能では対象外（変更なし） | — |
| Interfaces | 結合テスト | Django テストクライアントで URL を叩き、ステータス・ヘッダー・本文・テンプレート描画を検証する。desknet's 呼び出しは `monkeypatch` で差し替え、**呼び出し回数 0** を検証する | あり（セッション・認証） |

### 1.3 テスト優先順位

1. **Domain 層（最優先）** — 出力仕様（75 列固定・列位置・整形・チェック仕様）はすべてここに集約されている。ここが正しければ上位層の分岐は少ない
2. **Application 層** — 「desknet's を呼ばない」「スナップショットが無ければ出力しない」という本機能の中核制約（REQ-NF-003・REQ-F-009）を担保する
3. **Interfaces 層** — ステータスヘッダーによる分岐とボタンの活性判定（D-09）を担保する
4. **手動確認 / 受け入れ確認** — 画面表示（C-01）・実機貼り付け（C-11）・JS の活性復元

### 1.4 TDD 方針

CLAUDE.md §2「Phase 5 では TDD を採用する」に従い、以下のサイクルで実装する。

```
Red   : 本書のテストケースを 1 件ずつ失敗するテストとして書く
Green : そのテストを通す最小の実装を書く
Refactor : 重複を除去する（テストは変更しない）
```

**厳守事項**（test-strategy.md）:

- テストを書く前に実装を書かない
- 1 サイクルで扱うテストは 1 件
- Red を必ず確認してから Green に進む（`assert True` のような常に通るテストを書かない）
- Refactor 中にテストの期待値を書き換えない
- **既存テストの改修・削除は、対応する設計判断（DD-01〜DD-07）を明示してから行う**（§2.5）

**着手順**: Domain（§2.1）→ Application（§2.2）→ Interfaces（§2.4）。
Domain のうち `NormalizedValue`（§2.1(e)）と `AspFieldCheck`（§2.1(d)）を先に完成させ、
それらを使う `AspImportRow` / `AspImportRows` を後から組み立てる（依存の浅い順）。

---

## 2. テストケース一覧

**凡例** — 状態: `既存` = 現行テストをそのまま使う／`改修` = 現行テストを設計変更に合わせて直す／`新規` = 追加／`削除` = 設計変更により不要
**優先度** — 高: 出力仕様・中核制約／中: 分岐・境界／低: 補助的な検証
**枝番** — 既存テストの連番を保ったまま関連ケースを差し込むため `010b` のような枝番を使う（既存の `TC_AIV_UC_008b` と同じ運用）

**テスト関数名の規約**（django-pytest reference §命名 + 既存テストの TC-ID 体系を継承）:

```
test_{TC-ID をアンダースコア区切りにしたもの}_{何を}_{条件}_{期待結果}
例: test_TC_AIV_ASP_050_summary_crlf_is_replaced_with_space
```

すべてのテスト関数に docstring（「〜こと（対応 REQ-ID）。」）を付ける。

### 2.1 Domain 層テスト

#### (a) ファーストクラスコレクション: `AmendmentRows`（V-307）

配置: `tests/test_asp_import.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 | 状態 |
|---|---|---|---|---|---|---|
| TC-AIV-ASP-001 | 棚卸済みかつ変化点のある行だけが修正対象行になる | 差異あり行 1 / 一致行 1 | 抽出 1 件（差異あり行の資産番号） | REQ-F-002・C-02 | 高 | 既存 |
| TC-AIV-ASP-002 | 拠点変更の行も修正対象行に含まれる | `RowTone.MATCH_MOVED` の行 | 抽出 1 件 | REQ-F-002 | 高 | 既存 |
| TC-AIV-ASP-003 | メーカー名だけに差異がある行も修正対象行に含まれる | メーカー名のみ差異の行 | 抽出 1 件 | REQ-F-002・C-14（D-13） | 高 | 既存 |
| TC-AIV-ASP-004 | 未棚卸・台帳外の行は修正対象行に含まれない | `MatchStatus.ASSET_ONLY` 1 / `INVENTORY_ONLY` 1 | 抽出 0 件 | REQ-F-002・C-02 | 高 | 新規 |
| TC-AIV-ASP-005 | 変化点のない棚卸済み行は修正対象行に含まれない | `has_diff=False` の棚卸済み行 1 | 抽出 0 件 | REQ-F-002・C-02 | 高 | 新規 |
| TC-AIV-ASP-006 | 修正対象行が 0 件のとき `is_empty()` が真・`count()` が 0 | 一致行のみ 3 件 | `is_empty() is True` / `count() == 0` | REQ-F-008・C-07 | 高 | 新規 |
| TC-AIV-ASP-007 | 修正対象行が 1 件のとき `is_empty()` が偽・`count()` が 1 | 差異あり行 1 | `is_empty() is False` / `count() == 1` | REQ-F-002 | 中 | 新規 |
| TC-AIV-ASP-008 | 修正対象行が多数でも全件抽出され、入力順が保たれる | 差異あり行 1,000 件（資産番号連番） | `count() == 1000` かつ資産番号の並びが入力順と一致 | REQ-NF-004（D-10 上限なし） | 中 | 新規 |
| TC-AIV-ASP-009 | `to_import_rows()` は修正対象行と同数の取り込み用データを返す | 差異あり行 3 | `AspImportRows` の行数 3 | REQ-F-003 | 中 | 新規 |

#### (b) バリューオブジェクト: `AspPasteLayout`（V-309） / `AspImportRow`（V-306 の構成要素）

配置: `tests/test_asp_import.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 | 状態 |
|---|---|---|---|---|---|---|
| TC-AIV-ASP-010 | 取り込み用データの 1 行は常に 75 列である | 差異あり行 1（差異項目の有無を変えて 3 パターン） | `len(row.columns) == 75`（`ASP_COLUMN_COUNT` と一致） | REQ-F-003・C-03 | 高 | 既存 |
| TC-AIV-ASP-011 | 資産番号・資産枝番は差異の有無にかかわらず常に出力される | 摘要のみ差異の行 | 1 列目・2 列目に値が入る | REQ-F-004・C-04 | 高 | 既存 |
| TC-AIV-ASP-012 | 資産枝番は 4 桁ゼロ埋めで出力される | 資産枝番 `1` | 2 列目が `0001` | REQ-F-006・C-04 | 高 | 既存 |
| TC-AIV-ASP-013 | 管理部門コードは拠点名に差異のある行だけ出力される | 拠点名差異あり行／なし行 | 差異あり行のみ 3 列目に `site_code`、なし行は空欄 | REQ-F-003・C-05 | 高 | 既存 |
| TC-AIV-ASP-014 | 16 列目にはシリアルNo. の値が出力される | シリアルNo. 差異あり行 | 16 列目が `serial_number` の値 | REQ-F-003（D-07）・C-06 | 高 | 既存 |
| TC-AIV-ASP-015 | 画面「型番」の差異は 16 列目ではなく 44 列目に出力される | 型番のみ差異の行 | 16 列目が空欄・44 列目が `manager_code` の値 | REQ-F-004（D-07・D-11）・C-18 | 高 | 改修 |
| TC-AIV-ASP-016 | 摘要は差異のある行だけ 38 列目に出力される | 摘要差異あり行／なし行 | 差異あり行のみ 38 列目に値、なし行は空欄 | REQ-F-003・C-12 | 高 | 既存 |
| TC-AIV-ASP-017 | 値を入れない 66 列はすべて空欄である | 全 7 項目に差異のある行 | 1・2・3・16・38・44・59・64・65 列目以外がすべて `""` | REQ-F-003・C-13 | 高 | 改修 |
| TC-AIV-ASP-018 | 出力値は前後の空白を除いて出力される | 資産番号 `" 5262 "` / 摘要 `" テキスト "` | 1 列目 `5262` / 38 列目 `テキスト` | REQ-F-006 | 中 | 既存 |
| TC-AIV-ASP-019 | `asset_label` は資産番号と資産枝番を連結した識別ラベルになる | 資産番号 `5262` / 資産枝番 `1` | `5262-0001` | REQ-F-007 | 中 | 新規 |
| TC-AIV-ASP-019b | 資産枝番が空のとき `asset_label` は資産番号のみになる | 資産番号 `5262` / 資産枝番 `""` | `5262` | REQ-F-007 | 低 | 新規 |
| TC-AIV-ASP-010b | `blank_columns()` は 75 個の空文字を返す | なし | 長さ 75・全要素 `""` | REQ-F-003・C-03 | 中 | 新規 |
| TC-AIV-ASP-080 | 44 列目には型番に差異のある行だけ管理者コードが出力される | 型番差異あり行／なし行 | 差異あり行のみ 44 列目に `manager_code`、なし行は空欄 | REQ-F-003（D-11）・C-18 | 高 | 新規 |
| TC-AIV-ASP-081 | 59 列目には使用区分に差異のある行だけ使用区分コードが出力される | 使用区分差異あり行／なし行 | 差異あり行のみ 59 列目に `usage_category_code`、なし行は空欄 | REQ-F-003（D-11）・C-19 | 高 | 新規 |
| TC-AIV-ASP-082 | 64 列目にはメーカー名に差異のある行だけメーカーコードが出力される | メーカー名差異あり行／なし行 | 差異あり行のみ 64 列目に `manufacturer_code`、なし行は空欄 | REQ-F-003（D-13）・C-22 | 高 | 新規 |
| TC-AIV-ASP-083 | 65 列目には旧資産番号に差異のある行だけ旧資産番号コードが出力される | 旧資産番号差異あり行／なし行 | 差異あり行のみ 65 列目に `old_asset_number`、なし行は空欄 | REQ-F-003（D-11）・C-20 | 高 | 新規 |
| TC-AIV-ASP-084 | 6 列目（取得日付）は差異の有無にかかわらず全行で空欄である | 全 7 項目に差異のある行 | 6 列目が `""` | REQ-F-003（D-12）・C-21 | 中 | 新規 |
| TC-AIV-ASP-085 | メーカー名のみに差異がある行は 3 列だけに値が入る | メーカー名のみ差異の行 | 1・2・64 列目に値が入り、他はすべて `""` | REQ-F-004（D-13）・C-14 | 高 | 新規 |

#### (c) ファーストクラスコレクション: `AspImportRows`（V-306。CSV 描画）

配置: `tests/test_asp_import.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 | 状態 |
|---|---|---|---|---|---|---|
| TC-AIV-ASP-020 | CSV はヘッダー行を持たず、BOM 付き UTF-8・CRLF で出力される | 差異あり行 2 | 先頭が `\xef\xbb\xbf` / 行区切りが `\r\n` / 1 行目が資産番号で始まる | REQ-F-005・C-03 | 高 | 既存 |
| TC-AIV-ASP-021 | CSV の各行は区切り文字を 74 個持つ | 差異あり行 2 | 各行の `,`（引用外）が 74 個 | REQ-F-005・C-03 | 高 | 既存 |
| TC-AIV-ASP-022 | カンマを含む値はダブルクォートで囲まれる | 摘要 `A,B` | 38 列目が `"A,B"` | REQ-F-005 | 高 | 既存 |
| TC-AIV-ASP-023 | 修正対象行が 0 件のとき CSV は空バイト列になる | 0 件 | `b""` | REQ-F-008・C-07 | 高 | 既存 |
| TC-AIV-ASP-024 | ダブルクォートを含む値は `""` にエスケープして囲まれる | 摘要 `A"B` | 38 列目が `"A""B"` | REQ-F-005 | 中 | 新規 |
| TC-AIV-ASP-025 | `warnings()` は全行の警告を連結して返す | 違反のある行 2・無い行 1 | 警告件数 2・該当資産番号 2 件 | REQ-F-007・C-10 | 中 | 新規 |
| TC-AIV-ASP-026 | 同一の入力から繰り返し CSV を描画しても内容が変わらない | 差異あり行 3 で `render_csv()` を 2 回 | 2 回の `bytes` が完全一致 | REQ-NF-005・C-17 | 中 | 新規 |
| TC-AIV-ASP-027 | 拠点マスタ縮退のスナップショットから作った取り込み用データは管理部門コードが空欄になる | 拠点名差異あり行 + `site_warning=True` | 3 列目が空欄・`SITE_UNAVAILABLE` の警告 1 件 | REQ-F-009・DD-02 | 高 | 新規 |

#### (d) バリューオブジェクト: `AspFieldCheck`（V-310。チェック仕様）

配置: `tests/test_asp_import.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 | 状態 |
|---|---|---|---|---|---|---|
| TC-AIV-ASP-030 | チェック仕様に反しない行では警告が出ない | 全項目が規定内の行 | 警告 0 件 | REQ-F-007 | 高 | 既存 |
| TC-AIV-ASP-031 | 摘要が領域長を超えると警告になる | 摘要 65 byte 相当 | `CHECK_VIOLATION` 1 件（`P` 違反） | REQ-F-007・C-10 | 高 | 既存 |
| TC-AIV-ASP-032 | 型番の全角は半角へ変換されて出力され、警告にならない | シリアルNo. `ＳＮ１００`（`from_reconcile_row` 経由） | 16 列目が `SN100`・`message()` が空文字 | REQ-F-006・C-23（D-15） | 高 | **改修** |
| TC-AIV-ASP-033 | 資産枝番が数字以外を含むと警告になる | 資産枝番 `1A` | `CHECK_VIOLATION` 1 件（`I` 違反）・値はゼロ埋めせずそのまま出力 | REQ-F-006・REQ-F-007 | 高 | 既存 |
| TC-AIV-ASP-034 | 資産番号が空だと必須入力違反の警告になる | 資産番号 `""` | `CHECK_VIOLATION` 1 件（`O` 違反） | REQ-F-007 | 高 | 既存 |
| TC-AIV-ASP-037 | 資産枝番が空だと必須入力違反の警告になり、値は空欄のまま出力される | 資産枝番 `""` | 2 列目が `""`・`O` 違反 1 件 | REQ-F-006・REQ-F-007 | 高 | 新規 |
| TC-AIV-ASP-038 | 摘要が領域長ちょうど（64 byte）なら警告が出ない | 全角 32 文字（cp932 で 64 byte） | 警告 0 件 | REQ-F-007 | 高 | 新規 |
| TC-AIV-ASP-039 | 管理部門コードは 12 byte ちょうどで警告なし・13 byte で警告になる | 半角 12 文字 / 13 文字 | 前者 0 件・後者 `M` 違反 1 件 | REQ-F-007 | 中 | 新規 |
| TC-AIV-ASP-040 | 型番は 24 byte ちょうどで警告なし・25 byte で警告になる | 半角 24 文字 / 25 文字 | 前者 0 件・後者 `M` 違反 1 件 | REQ-F-007 | 中 | 新規 |
| TC-AIV-ASP-041 | 資産番号が 12 byte を超えると警告になる | 半角 13 文字 | `M` 違反 1 件 | REQ-F-007 | 中 | 新規 |
| TC-AIV-ASP-042 | cp932 で表現できない文字を含む値でも例外を送出せず評価される | 摘要に `𠮟`（cp932 非対応）を含む値 | 例外が発生せず、UTF-8 換算のバイト数で判定される | REQ-F-007（設計 §8.1 #8） | 中 | 新規 |
| TC-AIV-ASP-044 | 追加 4 列（44・59・64・65 列目）は 12 byte ちょうどで警告なし・13 byte で警告になる | 各列に半角 12 文字 / 13 文字 | 前者 0 件・後者 `M` 違反 1 件（列ごと） | REQ-F-007・C-18〜C-20・C-22 | 中 | 新規 |
| TC-AIV-ASP-045 | 追加 4 列に全角が混入すると警告になる | 各列に `ＡＢＣ` | 列ごとに `CHECK_VIOLATION` 1 件（`M` 違反） | REQ-F-007・C-10 | 中 | 新規 |
| TC-AIV-ASP-046 | 違反理由に項目名と ASP 上の列位置が含まれる | 型番に全角を含む値 | 理由が `型番（16 列目）` で始まる | REQ-F-007 | 高 | 新規 |
| TC-AIV-ASP-047 | `ASP_FIELD_CHECKS` のキーと `AspFieldCheck.position` が一致する | `ASP_FIELD_CHECKS` 全件 | すべての要素で `key == check.position` | REQ-F-007（設計 §4.2(b)） | 中 | 新規 |
| TC-AIV-ASP-043 | 1 つの値に複数の違反があるとき、すべての違反理由が返る | 資産枝番 `ＡＢＣＤＥ`（全角・数字以外・領域長超過） | `violations()` が 2 件以上を返す | REQ-F-007 | 中 | 新規 |

> **`violations()` は「寄せたあと」の値を受け取る**（D-14・DD-10）。本表の TC は `AspFieldCheck.violations()` を
> **直接呼ぶ**ため、半角変換・切り捨ての影響を受けない。`AspImportRow.from_reconcile_row()` 経由で
> 全角値・超過値を `AspImportRow.from_reconcile_row()` 経由で与える TC は、寄せた結果 `CHECK_VIOLATION` が
> 出なくなる。該当するのは **TC-AIV-ASP-032 の 1 件のみ**で、D-15 に合わせて期待結果を
> 「半角へ変換されて出力され、警告にならない」に改修した（§2.5 参照）。
> **半角変換は警告を出さない**（D-15）ため、変換だけで適合した値は `message()` に一切現れない。

#### (d2) バリューオブジェクト: `AdjustedValue`（調整済み値。D-14・DD-10）

配置: `tests/test_asp_import.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 | 状態 |
|---|---|---|---|---|---|---|
| TC-AIV-ASP-086 | 全角英数字・全角ハイフンは半角へ変換される | 44 列目 `ＡＢＣ－１２３` | `value == "ABC-123"` / `half_width_converted is True` / 違反 0 件 | REQ-F-006・C-23 | 高 | 新規 |
| TC-AIV-ASP-087 | NFKC で変換されないダッシュ類が半角ハイフンへ変換される | `AB‐1` `AB‑1` `AB‒1` `AB–1` `AB—1` `AB―1` `AB−1` | いずれも `value == "AB-1"` / 違反 0 件 | REQ-F-006・C-23 | 高 | 新規 |
| TC-AIV-ASP-088 | 全角引用符が半角へ変換される | `A’B` / `A“B”` | `A'B` / `A"B"` | REQ-F-006・C-23 | 中 | 新規 |
| TC-AIV-ASP-089 | 全角長音記号が半角ハイフンへ変換される（実データの 5 件） | 44 列目 `DDGー380C` / `ZSー302R` / `GMEーR1500` | `DDG-380C` / `ZS-302R` / `GME-R1500` / 違反 0 件 | REQ-F-006・C-23 | 高 | 新規 |
| TC-AIV-ASP-090 | かな・カナ・漢字を含む値の長音記号は変換されない | `モーター100` / `ﾓｰﾀｰ100` / `巻ーA` | 長音が `-` にならず、`CHECK_VIOLATION`（`M` 違反）1 件が残る | REQ-F-006・C-24 | 高 | 新規 |
| TC-AIV-ASP-091 | 長音記号だけを含み日本語文字を含まない値は変換される | `ーAB123` | `-AB123` / 違反 0 件（長音記号自身を日本語判定に含めない） | REQ-F-006・C-24 | 高 | 新規 |
| TC-AIV-ASP-092 | 全角空白は半角空白へ変換される | `AB　1`（U+3000） | `AB 1` / 違反 0 件 | REQ-F-006・C-23 | 中 | 新規 |
| TC-AIV-ASP-093 | 半角のみの値は変換されたことにならない | `ABC-123` | `half_width_converted is False` / 警告 0 件 | REQ-F-006 | 高 | 新規 |
| TC-AIV-ASP-094 | 摘要（チェック `P`）は半角変換されない | 摘要 `全角の摘要ＡＢＣ` | 値がそのまま出力され `half_width_converted is False` | REQ-F-006・C-23 | 高 | 新規 |
| TC-AIV-ASP-095 | 領域長を超える値は末尾が切り捨てられる（実データの 1 件） | 44 列目 `RGSHL4-60-50-L-S`（16 byte） | `value == "RGSHL4-60-50"`（12 byte）/ `truncated is True` / 違反 0 件 | REQ-F-006・C-25 | 高 | 新規 |
| TC-AIV-ASP-096 | 切り捨ては全角 1 文字を分断しない | 摘要 全角 32 文字 + `あ`（66 byte） | 全角 32 文字（64 byte）で止まり、`value` が cp932 で復号できる | REQ-F-006・C-25 | 高 | 新規 |
| TC-AIV-ASP-097 | 領域長ちょうどの値は切り捨てられない | 44 列目 半角 12 文字 | `truncated is False` / 警告 0 件 | REQ-F-006 | 中 | 新規 |
| TC-AIV-ASP-098 | 資産番号・資産枝番は領域長を超えても切り捨てられない | 資産番号 半角 13 文字 / 資産枝番 `12345` | 値がそのまま出力され `truncated is False`・`CHECK_VIOLATION` が残る | REQ-F-006・C-25 | 高 | 新規 |
| TC-AIV-ASP-099 | 半角変換のあとに切り捨てが適用される | 44 列目 全角英字 13 文字（26 byte） | 半角 13 文字へ変換後、12 文字に切り捨てられる（`half_width_converted` と `truncated` がともに真） | REQ-F-006・C-23・C-25 | 高 | 新規 |
| TC-AIV-ASP-100 | 空文字は変換も切り捨てもされない | `""` | `value == ""` / 両フラグ `False` | REQ-F-006 | 中 | 新規 |

#### (e) バリューオブジェクト: `NormalizedValue`（整形結果）

配置: `tests/test_asp_import.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 | 状態 |
|---|---|---|---|---|---|---|
| TC-AIV-ASP-050 | 摘要の CRLF は半角空白 1 つに置換される | `"前\r\n後"` | `value == "前 後"` / `newline_replaced is True` | REQ-F-006（D-08）・C-15 | 高 | 新規 |
| TC-AIV-ASP-051 | 摘要の LF は半角空白 1 つに置換される | `"前\n後"` | `value == "前 後"` / `newline_replaced is True` | REQ-F-006・C-15 | 高 | 新規 |
| TC-AIV-ASP-052 | 摘要の CR は半角空白 1 つに置換される | `"前\r後"` | `value == "前 後"` / `newline_replaced is True` | REQ-F-006・C-15 | 高 | 新規 |
| TC-AIV-ASP-053 | 改行を含まない摘要は置換されたことにならない | `"前後"` | `value == "前後"` / `newline_replaced is False` | REQ-F-006 | 中 | 新規 |
| TC-AIV-ASP-054 | 連続する CRLF は空白 2 つになり、1 つの CRLF が空白 2 つにならない | `"A\r\n\r\nB"` | `value == "A  B"`（空白 2 つ）／`"A\r\nB"` は `"A B"` | REQ-F-006（設計 §4.2(d)） | 高 | 新規 |
| TC-AIV-ASP-055 | 資産枝番は数字のみのとき 4 桁ゼロ埋めになる | `"1"` / `"12"` / `"1234"` | `0001` / `0012` / `1234` | REQ-F-006・C-04 | 高 | 新規 |
| TC-AIV-ASP-056 | 資産枝番が空ならゼロ埋めせず空欄のままになる | `""` | `""`（`0000` にしない） | REQ-F-006 | 高 | 新規 |
| TC-AIV-ASP-057 | 資産枝番が数字以外を含むならゼロ埋めせずそのまま返る | `"A1"` | `"A1"` | REQ-F-006 | 中 | 新規 |
| TC-AIV-ASP-058 | 資産枝番が 5 桁の数字ならゼロ埋めせずそのまま返る | `"12345"` | `"12345"`（切り詰めない。領域長違反は `AspFieldCheck` が報告する） | REQ-F-006 | 中 | 新規 |
| TC-AIV-ASP-059 | 資産番号・管理部門コード・シリアルNo.・管理者コード・使用区分コード・メーカーコード・旧資産番号コードは前後の空白を除いて返る | `"  5262  "` | `"5262"`（ゼロ埋め・桁合わせをしない） | REQ-F-006 | 中 | 改修 |

#### (f) ファーストクラスコレクション: `AspImportWarnings` / `AspImportWarning`（警告）

配置: `tests/test_asp_import.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 | 状態 |
|---|---|---|---|---|---|---|
| TC-AIV-ASP-035 | 警告文に違反件数が含まれる | 違反のある行 2 | 警告文に `2 件` を含む | REQ-F-007・C-10 | 高 | 既存 |
| TC-AIV-ASP-036 | 0 件時のメッセージが定数として定義されている | なし | `EMPTY_MESSAGE == "取り込み対象の変更がありません。"` | REQ-F-008・C-07 | 中 | 既存 |
| TC-AIV-ASP-060 | `of_kind()` は指定した種別の警告だけを返す | `CHECK_VIOLATION` 2 / `NEWLINE_REPLACED` 1 | `of_kind(NEWLINE_REPLACED)` が 1 件 | REQ-F-007 | 中 | 新規 |
| TC-AIV-ASP-061 | `asset_labels()` は同じ資産の重複を除いて返す | 同一資産に違反 2 件 | ラベル 1 件 | REQ-F-007 | 中 | 新規 |
| TC-AIV-ASP-062 | 資産番号の列挙は理由ごとに 10 件を上限とし、超過分は「ほか N 件」に丸められる | 同一理由の違反のある行 12 件 | 警告文に資産番号 10 件と `ほか 2 件` を含む | REQ-F-007（設計 §4.2(h)） | 中 | 改修 |
| TC-AIV-ASP-063 | チェック仕様違反と改行置換の両方があるとき 2 文が改行で連結される | 違反 1 件・置換 1 件 | 警告文が 2 行で、それぞれの文言を含む | REQ-F-007・C-15 | 高 | 新規 |
| TC-AIV-ASP-064 | 警告が無いとき警告文は空文字になる | 警告 0 件 | `message() == ""` | REQ-F-007 | 中 | 新規 |
| TC-AIV-ASP-065 | 拠点マスタ縮退の警告は出力全体に 1 件だけ付与される | `site_warning=True` の行 5 件 | `of_kind(SITE_UNAVAILABLE)` が 1 件 | REQ-F-009・DD-02 | 高 | 新規 |
| TC-AIV-ASP-066 | 突合結果が無いときのメッセージが定数として定義されている | なし | `UNAVAILABLE_MESSAGE == "棚卸を選び直してください。"` | REQ-F-009・C-16 | 中 | 新規 |
| TC-AIV-ASP-067 | 警告文の明細行は違反理由ごとにまとめられる | 型番に全角の行 2・摘要が領域長超過の行 1 | 明細行が 2 行で、型番の行に資産番号 2 件が並ぶ | REQ-F-007 | 高 | 新規 |
| TC-AIV-ASP-068 | 警告文の明細行に該当値が「」付きで示される | 型番 `ＡＢＣ－１２３` の行 1 | 明細行に `「ＡＢＣ－１２３」` を含む | REQ-F-007 | 高 | 新規 |
| TC-AIV-ASP-069 | 20 文字を超える値は先頭 20 文字＋`…` に丸められる | 摘要 全角 40 文字の行 1 | 明細行に先頭 20 文字と `…` を含み、21 文字目以降は含まない | REQ-F-007 | 中 | 新規 |
| TC-AIV-ASP-073 | 値が空の違反（`O`）では「」を付けない | 資産枝番 `""` の行 1 | 明細行に `「」` を含まない | REQ-F-007 | 中 | 新規 |
| TC-AIV-ASP-074 | 明細行は列位置の昇順に並ぶ | 摘要（38 列目）と型番（16 列目）の違反 | 型番の明細行が摘要の明細行より前にある | REQ-F-007 | 中 | 新規 |
| TC-AIV-ASP-075 | 1 つの資産が複数の理由に該当しても見出しの件数は 1 件になる | 同一資産で型番と摘要の両方が違反 | 見出し行が `1 件`・明細行が 2 行 | REQ-F-007 | 高 | 新規 |
| TC-AIV-ASP-101 | 半角変換しただけの行は警告にならない | 44 列目 `DDGー380C` の行 1 | `warnings` が 0 件・`message()` が空文字（`CHECK_VIOLATION` も 0 件） | REQ-F-007・C-23（D-15） | 高 | 新規 |
| TC-AIV-ASP-102 | 切り捨てた行は `VALUE_TRUNCATED` の警告になる | 44 列目 `RGSHL4-60-50-L-S` の行 1 | `of_kind(VALUE_TRUNCATED)` が 1 件・`CHECK_VIOLATION` が 0 件 | REQ-F-007・C-25 | 高 | 新規 |
| TC-AIV-ASP-103 | 警告文に寄せる前と寄せたあとの値が「」付きで並ぶ | 44 列目 `RGSHL4-60-50-L-S` の行 1 | 明細行に `「RGSHL4-60-50-L-S」→「RGSHL4-60-50」` を含む | REQ-F-007・C-25 | 高 | 新規 |
| TC-AIV-ASP-104 | 警告ブロックは 違反 → 切り捨て → 改行置換 → 拠点マスタ縮退 の順に並ぶ | 4 種別すべてを含む警告 | `message()` の行順が定義どおり | REQ-F-007（D-14・D-15） | 高 | 新規 |

#### (g) バリューオブジェクト: `DepartmentCode`（V-311）

配置: `tests/test_asp_import.py`

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 | 状態 |
|---|---|---|---|---|---|---|
| TC-AIV-ASP-070 | 管理部門コードは棚卸データの値から前後の空白を除いて生成される | `" 001 "` | `value == "001"` | REQ-F-003・REQ-F-006 | 中 | 新規 |
| TC-AIV-ASP-071 | 管理部門コードは 12 byte を超えると違反として報告される | 半角 13 文字 | `M` 違反 1 件（`AspFieldCheck` に委譲） | REQ-F-007 | 中 | 新規 |
| TC-AIV-ASP-072 | 管理部門コードが空でも例外にならず空欄として扱われる | `""` | `value == ""`・違反なし（`O` 対象外の列） | REQ-F-003 | 低 | 新規 |

#### (h) 突合結果スナップショット: `ReconcileCache`（V-308） / `reconcile_data`

配置: `tests/test_reconcile_cache.py`（既存の `TC_AIV_DOM_07x` 系を継承）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 | 状態 |
|---|---|---|---|---|---|---|
| TC-AIV-DOM-07G | `site_warning` を含めてセッションと往復できる | `site_warning=True` のスナップショット | 保存 → 読み出しで `site_warning is True` | DD-02 | 高 | 新規 |
| TC-AIV-DOM-07H | `site_warning` キーの無い既存セッションは偽として読める | `site_warning` を持たない dict | `site_warning is False`・例外なし（後方互換） | DD-02（設計 §5.2） | 高 | 新規 |
| TC-AIV-DOM-07I | `load_amendment_snapshot` は棚卸が一致するときスナップショットを返す | `management_id="M1"` のセッション / 要求 `M1` | `ReconcileCache` を返す | REQ-NF-003 | 高 | 新規 |
| TC-AIV-DOM-07J | `load_amendment_snapshot` は棚卸が一致しないとき `None` を返す | `management_id="M1"` のセッション / 要求 `M2` | `None` | REQ-F-009（設計 §8.1 #3） | 高 | 新規 |
| TC-AIV-DOM-07K | `load_amendment_snapshot` はセッションが壊れていても例外を送出しない | `rows` が文字列／キー欠損の dict | `None` を返す（例外なし） | REQ-F-009（設計 §8.1 #10） | 高 | 新規 |
| TC-AIV-DOM-07L | 拠点マスタ縮退の突合結果も `site_warning=True` で保存される | 拠点マスタ取得失敗 | セッションにスナップショットが保存され `site_warning is True` | DD-02 | 高 | 新規 |
| TC-AIV-DOM-07M | 追加コード部品 3 件がセッションと往復できる | `manager_code` / `usage_category_code` / `manufacturer_code` を持つ突合結果行 | 保存 → 読み出しで 3 件とも値が保たれる | REQ-F-003（D-11・D-13）・DD-08 | 高 | 新規 |
| TC-AIV-DOM-07N | 追加コード部品を持たない旧形式のセッションが空文字として読める | 3 件のキーを持たない dict | 3 件とも `""`・例外なし（後方互換） | REQ-F-003（D-11・D-13） | 中 | 新規 |

#### (i) 突合結果行の追加コード部品: `ReconcileRow` / `ASSET_FIELDS`・`INVENTORY_FIELDS`

配置: `tests/test_asset_fields.py`（部品一覧） / `tests/test_row_display.py`（突合結果行への取り込み）

「判定は名称・出力はコード」（DD-08）を成立させるには、desknet's から 3 件のコード部品を取得し、
突合結果行に保持し続ける必要がある。その 3 点（取得・保持・往復）のうち取得と保持を本節で検証する
（往復は TC-AIV-DOM-07M・07N）。

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 | 状態 |
|---|---|---|---|---|---|---|
| TC-AIV-DOM-060 | 資産データ・棚卸データの部品一覧に追加コード 3 件が含まれる | `ASSET_FIELDS` / `INVENTORY_FIELDS` | 双方に `管理者コード`・`使用区分コード`・`メーカーコード` が含まれる | REQ-F-003（D-11・D-13）・DD-08 | 高 | 新規 |
| TC-AIV-DOM-061 | 突合結果行に棚卸データの追加コード 3 件が詰められる | 3 件を持つ棚卸データの行 | `manager_code` / `usage_category_code` / `manufacturer_code` が棚卸データの値になる | REQ-F-003（D-11・D-13）・DD-08 | 高 | 新規 |
| TC-AIV-DOM-062 | 追加コードを持たない記録でも例外にならず空欄になる | 3 件のキーが無い棚卸データの行 | 3 件とも `""`（ASP では「変更なし」として扱われる） | REQ-F-003（D-01） | 中 | 新規 |

### 2.2 Application 層テスト

配置: `tests/test_usecase_export_asp_import.py`
共通方針: `ExportAspImport()` を**引数なしで**生成する（DD-01）。セッションは `dict` で代用する。

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 | 状態 |
|---|---|---|---|---|---|---|
| TC-AIV-UC-040 | 修正対象行だけが取り込み用データに出力される | 差異あり 1 / 一致 1 / 未棚卸 1 のスナップショット | `status == OK` / `row_count == 1` / CSV 1 行 | REQ-F-002・C-02 | 高 | 改修 |
| TC-AIV-UC-041 | 画面のフィルタを絞り込んでも出力行数が変わらない | 拠点フィルタ指定あり / なしの 2 回実行 | 2 回の `row_count` と CSV が一致 | REQ-F-002・C-08 | 高 | 改修 |
| TC-AIV-UC-042 | 修正対象行が 0 件のとき CSV を返さずメッセージを返す | 一致行のみのスナップショット | `status == EMPTY` / `content is None` / `message == EMPTY_MESSAGE` | REQ-F-008・C-07 | 高 | 改修 |
| TC-AIV-UC-043 | 突合結果スナップショットだけを読み、desknet's API を呼び出さない | 有効なスナップショット + 呼び出し回数を数えるモック | CSV が返り、モックの呼び出し回数が **0** | REQ-NF-003・C-09 | 高 | 改修 |
| TC-AIV-UC-044 | 棚卸が未選択のときは出力せず選び直しを促す | `managementId` 空 | `status == UNAVAILABLE` / `content is None` / `message == UNAVAILABLE_MESSAGE` | REQ-F-009・C-16 | 高 | 改修 |
| ~~TC-AIV-UC-045~~ | ~~desknet's API エラー時に安全に失敗する~~ | — | **削除**（DD-07。`execute_safe` 廃止・外部通信が無くなるため発生しえない） | — | — | 削除 |
| TC-AIV-UC-046 | 拠点マスタ縮退のスナップショットでも出力を中止しない | `site_warning=True` のスナップショット | `status == OK` / CSV が返る / 警告文に拠点マスタの旨を含む | REQ-F-009・DD-02 | 高 | 改修 |
| TC-AIV-UC-047 | チェック仕様違反があっても CSV を出力し、警告を返す | 摘要が領域長超過の行 | `status == OK` / `content` が非空 / `warning_message` が非空 | REQ-F-007・C-10 | 高 | 改修 |
| TC-AIV-UC-048 | 突合結果スナップショットが無いときは出力せず desknet's も呼ばない | セッションが空 + 呼び出し回数を数えるモック | `status == UNAVAILABLE` / モックの呼び出し回数 **0** | REQ-F-009・REQ-NF-003・C-16 | 高 | 新規 |
| TC-AIV-UC-049 | スナップショットの棚卸が要求と異なるときは出力しない | セッション `M1` / 要求 `M2` | `status == UNAVAILABLE`（`M1` の結果を出さない） | REQ-F-009（設計 §8.1 #3） | 高 | 新規 |
| TC-AIV-UC-050 | ユースケースは desknet's ゲートウェイを受け取らずに生成・実行できる | `ExportAspImport()` | 生成・実行が成功する（引数を要求しない） | REQ-NF-003・DD-01 | 高 | 新規 |
| TC-AIV-UC-051 | 同じスナップショットから繰り返し作成しても出力内容が変わらない | 同一セッションで 2 回実行 | 2 回の `content` と `row_count` が一致 | REQ-NF-005・C-17 | 中 | 新規 |
| TC-AIV-UC-052 | 出力行数が修正対象行数と一致する | 差異あり行 3 のスナップショット | `row_count == 3` かつ CSV の行数 3 | REQ-F-002 | 中 | 新規 |
| TC-AIV-UC-053 | セッションの内容が壊れていても例外を送出せず選び直しを促す | `rows` が想定外の型のセッション | `status == UNAVAILABLE`・例外なし | REQ-F-009（設計 §8.1 #10） | 高 | 新規 |
| TC-AIV-UC-054 | 摘要に改行を含む行は置換して出力し、警告に該当資産番号を含める | 摘要に `\r\n` を含む差異あり行 | CSV の 38 列目に改行が無い / 警告文に該当資産番号 | REQ-F-006・C-15 | 高 | 新規 |
| TC-AIV-UC-032 | 拠点マスタ縮退のスナップショットは一覧表示・CSV 出力では採用されず再取得される | `site_warning=True` のセッションで一覧表示 | desknet's から再取得され、既存 CSV 出力の内容が変わらない | DD-02 | 高 | **改修**（現行は「キャッシュしない」を検証。`tests/test_usecase_list_page.py`） |

### 2.3 Infrastructure 層テスト

**本機能でのテスト対象なし。**

`infrastructure/` 配下は変更しない（機能設計書 §7.1 に該当ファイルが無い）。
DD-01 により本機能は desknet's ゲートウェイに依存しないため、新規の外部通信テストは発生しない。
既存の `tests/test_desknet_client.py` は変更しない。

### 2.4 Interfaces 層テスト

配置: `tests/test_asset_inventory_views.py`（既存の `TC_AIV_API_0NN` 系を継承）

| # | テストケース | 入力 | 期待結果 | 対応REQ-ID | 優先度 | 状態 |
|---|---|---|---|---|---|---|
| TC-AIV-API-011 | 未ログインで取り込み用データを要求するとログイン画面へリダイレクトされる | 未ログインで `GET /api/asset-inventory/asp-import.csv` | 302 → `/login` | REQ-NF-001 | 高 | 既存 |
| TC-AIV-API-012 | 総務メニューグループのユーザーは取り込み用データをダウンロードできる | 有効なスナップショット | 200 / `X-Asp-Import-Status: ok` / `Content-Type: text/csv` | REQ-F-001・REQ-NF-001 | 高 | 改修 |
| TC-AIV-API-013 | 出力対象が 0 件のときダウンロードされずメッセージが返る | 一致行のみのスナップショット | 200 / `X-Asp-Import-Status: empty` / 本文が `取り込み対象の変更がありません。` | REQ-F-008・C-07 | 高 | 既存 |
| TC-AIV-API-014 | 警告はヘッダーに URL エンコードして返る | 違反のある行 | `X-Asp-Import-Warning` が URL エンコード済みで、デコードすると警告文と一致 | REQ-F-007・C-10 | 高 | 既存 |
| ~~TC-AIV-API-015~~ | ~~desknet's のエラー時に 502 を返す~~ | — | **削除**（設計 §6.2。DD-01 により発生しえない） | — | — | 削除 |
| TC-AIV-API-015b | 突合結果スナップショットが無いときは `unavailable` を返しダウンロードさせない | セッションが空 | 200 / `X-Asp-Import-Status: unavailable` / 本文が `棚卸を選び直してください。` | REQ-F-009・C-16 | 高 | 新規 |
| TC-AIV-API-016 | 突合結果が表示されているとき作成ボタンが活性で描画される | 棚卸選択済みで一覧表示 | ボタンが描画され `disabled` が付かない | REQ-F-001・C-01 | 高 | 改修 |
| TC-AIV-API-017 | 棚卸が未選択でも作成ボタンは描画され、非活性になる | 棚卸未選択で一覧表示 | ボタンが描画され `disabled` が付き、`title` に理由が入る | REQ-F-009（D-09）・C-16 | 高 | 新規 |
| TC-AIV-API-018 | 突合結果の取得に失敗して一覧がエラー表示のとき作成ボタンが非活性になる | 資産マスタ取得失敗 | ボタンに `disabled` が付く | REQ-F-009 | 中 | 新規 |
| TC-AIV-API-019 | 非活性のまま直接要求が到達しても desknet's API を呼び出さない | セッション空で直接 URL 要求 + 呼び出し回数を数えるモック | `unavailable` かつモックの呼び出し回数 **0** | REQ-NF-003・C-16 | 高 | 新規 |
| TC-AIV-API-020 | 総務メニューグループを持たないユーザーは利用できない | 生産部門のみのユーザー | 403（既存の資産棚卸結果と同じ扱い） | REQ-NF-001 | 高 | 新規 |
| TC-AIV-API-021 | 出力行数がヘッダーに返る | 差異あり行 3 | `X-Asp-Import-Rows == "3"` | REQ-F-001 | 中 | 新規 |
| TC-AIV-API-022 | ダウンロードファイル名が `asp_import_{日時}.csv` になる | 差異あり行 1 | `Content-Disposition` が `attachment; filename="asp_import_YYYYMMDDhhmmss.csv"` の形式 | REQ-F-001 | 低 | 新規 |
| TC-AIV-API-023 | 既存の突合結果 CSV 出力の仕様が変わらない | 既存 CSV 出力を要求 | 既存テスト（TC-AIV-API-004）と同じ結果 | REQ-F-001（設計 §7.2） | 高 | 既存（回帰） |

### 2.5 既存テストの改修・削除一覧

> **2026/08/27 追記（D-14・D-15 で修正）**: 寄せ（半角変換・切り捨て）の導入による既存 TC の改修は
> **TC-AIV-ASP-032 の 1 件**（`from_reconcile_row()` 経由で全角値を与える唯一の既存 TC）。削除は無い。
> 全角値・領域長超過値を扱う他の既存 TC（TC-AIV-ASP-040〜045 ほか）はいずれも
> `AspFieldCheck.violations()` を**直接呼ぶ**実装であり、`violations()` の意味は変えないためである
> （`from_reconcile_row()` 経由で全角値を流し込む既存 TC は無い）。
> なお `VALUE_BRANCH_FULLWIDTH`（資産枝番）はチェック `M` を持たないため寄せても変換されず、
> 仮に `from_reconcile_row()` を通しても `I`・領域長の違反として残る。

CLAUDE.md「既存コードの削除を伴う変更は、削除対象を明示してから実行する」に対応する。

| 対象テスト | ファイル | 措置 | 理由（設計判断） |
|---|---|---|---|
| `test_TC_AIV_UC_045_safe_on_api_error` | `tests/test_usecase_export_asp_import.py` | **削除** | DD-07。`execute_safe()` を廃止し、外部通信由来の例外が発生しえないため |
| `test_TC_AIV_API_015_asp_import_error_returns_502` | `tests/test_asset_inventory_views.py` | **削除** | 設計 §6.2。502 を返す経路が無くなるため（`unavailable` の TC-AIV-API-015b に置き換える） |
| `test_TC_AIV_UC_032_site_master_failure_is_not_cached` | `tests/test_usecase_list_page.py` | **改修** | DD-02。「キャッシュしない」→「`site_warning=True` で保存するが `use_snapshot=True` の経路では採用せず再取得する」に期待結果を変える |
| `test_TC_AIV_UC_040`〜`044` / `046` / `047` | `tests/test_usecase_export_asp_import.py` | **改修** | DD-01（`access_key` 引数の削除）・`AspImportResult.status` の導入に伴う呼び出し方と期待結果の変更 |
| `test_TC_AIV_API_012` / `016` | `tests/test_asset_inventory_views.py` | **改修** | `unavailable` の追加と、ボタンを `{% if has_list_data %}` の外へ移す変更（D-09）に伴う期待結果の変更 |
| `test_TC_AIV_ASP_015` / `017` | `tests/test_asp_import.py` | **改修** | D-11・D-13。型番の差異は 44 列目へ出力する（16 列目は空欄のまま）／空欄列が 70 列から 66 列に減る |
| `ROW_UNMAPPED_ONLY` を使うテスト | `tests/test_asp_import.py` | **削除・置換** | D-13 により「ASP に対応列のない差異」が消滅したため、`ROW_MANUFACTURER_ONLY` と `ROW_CODE_ONLY` に置き換える |
| `DIFF_ASSETS` / `DIFF_INVENTORY` フィクスチャ | `tests/test_usecase_export_asp_import.py` | **改修** | D-11・D-13。棚卸データに `管理者コード`・`使用区分コード`・`メーカーコード` を加え、44・59・64・65 列目の期待値を検証する |
| `tests/test_asp_import.py` のモジュール関数 import | `tests/test_asp_import.py` | **改修** | `select_amendment_rows` / `build_asp_import_columns` / `render_asp_import_csv` / `check_violations` / `build_check_warning_message` / `format_branch_number` の削除に伴い、VO・コレクションのメソッド呼び出しへ書き換える（設計 §7.1 削除対象） |


### 2.6 要件トレーサビリティ

| REQ-ID | 要件の要旨 | 対応テストケース |
|---|---|---|
| REQ-F-001 | 一覧画面に取り込み用データの作成ボタンを設ける | TC-AIV-API-012・021・022 / M-01・M-02 |
| REQ-F-002 | 修正対象行（棚卸済みかつ変化点あり）だけを出力する | TC-AIV-ASP-001〜009 / TC-AIV-UC-040・041・052 |
| REQ-F-003 | 貼り付けレイアウト（75 列・1/2/3/16/38/44/59/64/65 列目）どおりに出力する | TC-AIV-ASP-010〜017・070・072・080〜084 / TC-AIV-DOM-07M・07N・060〜062 |
| REQ-F-004 | 資産番号・資産枝番は常に出力し、差異のある項目だけ対応列に出力する | TC-AIV-ASP-011・015・003・085 |
| REQ-F-005 | ヘッダーなし・BOM 付き UTF-8・CRLF の CSV で出力する | TC-AIV-ASP-020〜024 |
| REQ-F-006 | 値を ASP の書式へ整形し、ASP の書式へ寄せる（トリム・ゼロ埋め・改行置換・半角変換・領域長切り捨て） | TC-AIV-ASP-018・050〜059・086〜100 / TC-AIV-UC-054 |
| REQ-F-007 | チェック仕様違反と、寄せた事実を警告として知らせ、出力は継続する | TC-AIV-ASP-030〜047・035・060〜069・073〜075・101〜104 / TC-AIV-UC-047 / TC-AIV-API-014 |
| REQ-F-008 | 修正対象行が 0 件のときはダウンロードさせずメッセージを出す | TC-AIV-ASP-023・036 / TC-AIV-UC-042 / TC-AIV-API-013 |
| REQ-F-009 | 突合結果が無いときは非活性にし、要求されても出力しない | TC-AIV-ASP-027・065・066 / TC-AIV-DOM-07I〜07L / TC-AIV-UC-044・048・049・053 / TC-AIV-API-015b・017・018・019 |
| REQ-NF-001 | 総務メニューグループのユーザーのみ利用できる | TC-AIV-API-011・020 |
| REQ-NF-002 | テーブルの新設・変更を行わない | **テストケースなし**（変更が無いことをもって満たす。§1.1 テスト対象外に記載） |
| REQ-NF-003 | 作成時に desknet's API を呼び出さない | TC-AIV-UC-043・048・050 / TC-AIV-API-019 / TC-AIV-DOM-07I |
| REQ-NF-004 | 大量の修正対象行でも出力できる（行数上限を設けない） | TC-AIV-ASP-008 |
| REQ-NF-005 | ASP へ自動書き込みせず、繰り返し作成しても内容が変わらない | TC-AIV-ASP-026 / TC-AIV-UC-051 |

**設計判断（DD）のトレーサビリティ**:

| DD | 内容 | 対応テストケース |
|---|---|---|
| DD-01 | ユースケースは突合結果スナップショットのみを入力とする | TC-AIV-UC-050・043 |
| DD-02 | 縮退結果も `site_warning` 付きで保存し、一覧表示では採用しない | TC-AIV-DOM-07G・07H・07L / TC-AIV-UC-032・046 / TC-AIV-ASP-027・065 |
| DD-03 | `NormalizedValue` で整形結果と置換有無を返す | TC-AIV-ASP-050〜059 |
| DD-04 | 警告に種別を持たせ、コレクションで文面を組み立てる | TC-AIV-ASP-060〜069・073〜075 |
| DD-05 | 活性判定はサーバー側で行い、画面は受け取った値で描画する | TC-AIV-API-016・017・018 / M-03 |
| DD-06 | 一括生成・行数上限なし | TC-AIV-ASP-008 |
| DD-07 | `execute_safe` を廃止する | TC-AIV-UC-045（削除）/ TC-AIV-API-015（削除） |
| DD-10 | `AspFieldCheck.adjusted()` が半角変換 → 切り捨てを順に適用し、`violations()` は寄せたあとの値に対して呼ぶ | TC-AIV-ASP-086〜104 |

---

## 3. テストデータ

### 3.1 正常系テストデータ

既存のテストヘルパー（`tests/test_asp_import.py` の `_row()` / `_comparisons()`）を継承して使う。
`_comparisons()` は「差異のある項目名」をキーワード引数で指定でき、変化点判定（A-301）の結果を模擬する。

| データ名 | 内容 | 用途 |
|---|---|---|
| `ROW_ALL_DIFF` | 資産番号 `5262` / 資産枝番 `1` / `site_code` `002` / シリアルNo. `SN-100` / 摘要 `摘要テキスト` / `manager_code` `MGR1` / `usage_category_code` `U1` / `manufacturer_code` `MK1` / `old_asset_number` `OLD1`、変化点判定 7 項目すべてに差異あり | 9 列すべてに値が入る行（TC-AIV-ASP-010・017・080〜084） |
| `ROW_SUMMARY_ONLY` | 摘要のみ差異あり | 38 列目だけに値が入る行（TC-AIV-ASP-016） |
| `ROW_MANUFACTURER_ONLY` | メーカー名のみ差異あり（`manufacturer_code` `MK1`） | 資産番号・資産枝番と 64 列目の 3 列だけの行（C-14・D-13。TC-AIV-ASP-003・085） |
| `ROW_CODE_ONLY` | 型番・使用区分・旧資産番号のみ差異あり（`manager_code` / `usage_category_code` / `old_asset_number`） | 44・59・65 列目に値が入り 16 列目は空欄の行（C-18〜C-20。TC-AIV-ASP-015・080・081・083） |
| `ROW_CLEAN` | `RowTone.MATCH_CLEAN` / `has_diff=False` / 差異なし | 出力対象外（TC-AIV-ASP-005） |
| `ROW_ASSET_ONLY` / `ROW_INVENTORY_ONLY` | `MatchStatus.ASSET_ONLY` / `INVENTORY_ONLY` | 未棚卸・台帳外（TC-AIV-ASP-004） |
| `ROW_MOVED` | `RowTone.MATCH_MOVED`（拠点変更） | 出力対象（TC-AIV-ASP-002） |
| `SNAPSHOT_OK` | `management_id="M1"` / 上記の行を束ねた `ReconcileCache` / `site_warning=False` | Application 層の既定入力 |
| `SNAPSHOT_DEGRADED` | `SNAPSHOT_OK` + `site_warning=True` | DD-02 の検証（TC-AIV-UC-046・ASP-027） |

Application 層・Interfaces 層のセッションは、既存の `tests/test_usecase_list_page.py` の
`_mock_list_all` / `_counting_mock_list_all` / `_list_all_site_master_down` を再利用して組み立てる。

### 3.2 異常系テストデータ

| データ名 | 内容 | 用途 |
|---|---|---|
| `VALUE_BRANCH_EMPTY` | 資産枝番 `""` | `O` 違反（TC-AIV-ASP-037・056） |
| `VALUE_BRANCH_ALPHA` | 資産枝番 `"1A"` | `I` 違反・ゼロ埋めしない（TC-AIV-ASP-033・057） |
| `VALUE_BRANCH_5DIGIT` | 資産枝番 `"12345"` | 領域長超過（TC-AIV-ASP-058） |
| `VALUE_ASSET_EMPTY` | 資産番号 `""` | `O` 違反（TC-AIV-ASP-034） |
| `VALUE_DEPT_13` | 管理部門コード 半角 13 文字 | `M` 違反（TC-AIV-ASP-039・071） |
| `VALUE_SERIAL_FULLWIDTH` | シリアルNo. `"ＡＢＣ"` | `M` 違反（`violations()` を直接呼ぶ TC 用） |
| `VALUE_SUMMARY_64` / `VALUE_SUMMARY_65` | 摘要 全角 32 文字（64 byte）／ 全角 32 文字 + 半角 1 文字（65 byte） | 領域長の境界（TC-AIV-ASP-038・031） |
| `VALUE_SUMMARY_CRLF` / `_LF` / `_CR` / `_CRLF2` | 摘要 `"前\r\n後"` / `"前\n後"` / `"前\r後"` / `"A\r\n\r\nB"` | 改行置換（TC-AIV-ASP-050〜054） |
| `VALUE_SUMMARY_CP932_NG` | 摘要に `𠮟`（cp932 非対応） | バイト数計算の代替評価（TC-AIV-ASP-042） |
| `VALUE_SUMMARY_COMMA` / `_QUOTE` | 摘要 `"A,B"` / `"A\"B"` | CSV の囲み・エスケープ（TC-AIV-ASP-022・024） |
| `SESSION_EMPTY` | `{}` | スナップショット無し（TC-AIV-UC-048） |
| `SESSION_OTHER_MANAGEMENT` | `management_id="M1"` のスナップショットに `M2` を要求 | 棚卸の不一致（TC-AIV-UC-049） |
| `SESSION_BROKEN` | `rows` が文字列／必須キー欠損 | セッション破損（TC-AIV-DOM-07K・TC-AIV-UC-053） |
| `SESSION_NO_SITE_WARNING_KEY` | `site_warning` キーを持たない旧形式 | 後方互換（TC-AIV-DOM-07H） |
| `ROWS_1000` | 差異あり行 1,000 件 | 大量データ（TC-AIV-ASP-008） |
| `ROWS_VIOLATION_12` | 違反のある行 12 件 | 資産番号列挙の上限（TC-AIV-ASP-062） |
| `VALUE_MANAGER_PROLONGED` | 管理者コード `"DDGー380C"`（U+30FC） | 長音記号の半角変換（TC-AIV-ASP-089・101） |
| `VALUE_MANAGER_DASHES` | `"AB‐1"`〜`"AB−1"` の 7 種 | ダッシュ類の写像（TC-AIV-ASP-087） |
| `VALUE_MANAGER_KANA` | 管理者コード `"モーター100"` / `"ﾓｰﾀｰ100"` | カナ語保護（TC-AIV-ASP-090） |
| `VALUE_MANAGER_PROLONGED_ONLY` | 管理者コード `"ーAB123"` | 日本語を含まない長音（TC-AIV-ASP-091） |
| `VALUE_MANAGER_16` | 管理者コード `"RGSHL4-60-50-L-S"`（16 byte） | 領域長切り捨て（TC-AIV-ASP-095・102） |
| `VALUE_SUMMARY_66` | 摘要 全角 32 文字 + `あ`（66 byte） | 全角を分断しない切り捨て（TC-AIV-ASP-096） |
| `VALUE_ASSET_13` | 資産番号 半角 13 文字 | キー列は切り捨てない（TC-AIV-ASP-098・041） |

---

## 4. 境界値・異常系のカバレッジ

### 4.1 境界値テスト

| 対象 | 境界値 | テストケース |
|---|---|---|
| 修正対象行の件数 | 0 件 / 1 件 / 多数（1,000 件） | TC-AIV-ASP-006 / 007 / 008 |
| 列数 | 75 列ちょうど（区切り 74 個） | TC-AIV-ASP-010 / 021 |
| 値を入れる列位置 | 1・2・3・16・38・44・59・64・65 列目とそれ以外の 66 列 | TC-AIV-ASP-011〜017・080〜085 |
| 資産番号の領域長 | 12 byte / 13 byte | TC-AIV-ASP-041 |
| 資産枝番の桁 | 空 / 1 桁 / 4 桁 / 5 桁 / 数字以外 | TC-AIV-ASP-055〜058・037 |
| 管理部門コードの領域長 | 12 byte / 13 byte | TC-AIV-ASP-039 |
| 追加 4 列（44・59・64・65 列目）の領域長 | 12 byte / 13 byte | TC-AIV-ASP-044 |
| 型番（16 列目）の領域長 | 24 byte / 25 byte | TC-AIV-ASP-040 |
| 摘要の領域長 | 64 byte / 65 byte | TC-AIV-ASP-038 / 031 |
| 改行の連続 | 1 つの CRLF / 連続 CRLF | TC-AIV-ASP-050 / 054 |
| 警告の資産番号列挙 | 10 件 / 11 件以上（理由ごと） | TC-AIV-ASP-062 |
| 警告文の値の丸め | 20 文字 / 21 文字以上 / 空文字 | TC-AIV-ASP-069・073 |
| 警告の件数 | 0 件 / 1 件 / 複数種別 | TC-AIV-ASP-064 / 035 / 063 / 104 |
| 半角変換の適用有無 | 半角のみ / 全角混在 / 空文字 | TC-AIV-ASP-093 / 086 / 100 |
| 長音記号の扱い | 日本語なし（変換する） / 日本語あり（変換しない） | TC-AIV-ASP-091 / 090 |
| 切り捨ての境界 | 領域長ちょうど / 1 byte 超過 / 全角を分断する位置 | TC-AIV-ASP-097 / 095 / 096 |
| 切り捨ての対象列 | `truncatable=True`（44 列目） / `False`（1・2 列目） | TC-AIV-ASP-095 / 098 |

### 4.2 異常系テスト

機能設計書 §8.1 の異常系一覧に 1 対 1 で対応させる。

| # | 対象（設計 §8.1） | 異常ケース | 期待される振る舞い | テストケース |
|---|---|---|---|---|
| 1 | 棚卸が未選択 | `managementId` が空 | `UNAVAILABLE`。desknet's を呼ばない | TC-AIV-UC-044・API-019 |
| 2 | スナップショットが無い | セッション失効・別タブでの切り替え | `UNAVAILABLE`。desknet's を呼ばない | TC-AIV-UC-048・API-015b |
| 3 | 棚卸の不一致 | セッション `M1` / 要求 `M2` | `UNAVAILABLE` | TC-AIV-UC-049・DOM-07J |
| 4 | 修正対象行が 0 件 | 一致行のみ | `EMPTY`。ダウンロードさせない | TC-AIV-UC-042・API-013・ASP-023 |
| 5 | 資産枝番が空・数字以外 | `""` / `"1A"` | 出力を継続し `CHECK_VIOLATION` の警告 | TC-AIV-ASP-037・033 |
| 6 | 領域長超過・全角混入 | 13 byte / `ＡＢＣ` | 寄せてから、なお適合しない場合のみ `CHECK_VIOLATION`。切り捨てた事実のみ `VALUE_TRUNCATED`（半角変換は警告しない・D-15） | TC-AIV-ASP-039〜041・032・086・095・101・102 |
| 6-2 | 長音記号を含むカナ語 | `モーター100` | 変換せず `CHECK_VIOLATION` | TC-AIV-ASP-090 |
| 6-3 | 資産番号・資産枝番が領域長超過 | 半角 13 文字 / `12345` | 切り捨てず `CHECK_VIOLATION` | TC-AIV-ASP-098 |
| 7 | 摘要に改行 | `"前\r\n後"` | 半角空白 1 つに置換して出力を継続し `NEWLINE_REPLACED` の警告 | TC-AIV-ASP-050〜054・UC-054 |
| 8 | cp932 で表現できない文字 | `𠮟` を含む摘要 | UTF-8 換算で代替評価。例外にしない | TC-AIV-ASP-042 |
| 9 | 拠点マスタのみ取得失敗 | `site_warning=True` | 出力を中止せず、管理部門コードは空欄・`SITE_UNAVAILABLE` の警告 1 件 | TC-AIV-ASP-027・065・UC-046 |
| 10 | セッションの内容が壊れている | `rows` が想定外の型・キー欠損 | `None` を返し `UNAVAILABLE`。例外を送出しない | TC-AIV-DOM-07K・UC-053 |
| 11 | 未ログイン | 未認証で要求 | `/login` へリダイレクト | TC-AIV-API-011 |
| 12 | 認可の無いユーザー | 生産部門のみのユーザー | 403 | TC-AIV-API-020 |
| 13 | 同時実行 | 同じ棚卸で複数回・複数利用者が作成 | 競合しない（出力内容が変わらない） | TC-AIV-UC-051・ASP-026 |

### 4.3 エッジケース

| ケース | 扱い | テストケース |
|---|---|---|
| 大量データ（1,000 行） | 上限を設けず全件出力する（D-10）。件数と並び順が保たれること | TC-AIV-ASP-008 |
| 繰り返し実行の冪等性 | 同一スナップショットからの出力が毎回同一（C-17） | TC-AIV-UC-051・ASP-026 |
| 画面フィルタとの独立性 | フィルタ状態に依存しない（C-08） | TC-AIV-UC-041 |
| 旧形式セッションとの後方互換 | `site_warning` キーが無くても動く | TC-AIV-DOM-07H |
| 既存機能への回帰 | 既存の突合結果 CSV 出力の仕様が変わらない | TC-AIV-API-023・UC-032 |

### 4.4 自動テスト対象外（手動確認・受け入れ確認）

| # | 確認項目 | 方法 | 対応REQ-ID |
|---|---|---|---|
| M-01 | 一覧画面のツールバーで、CSV 出力ボタンの隣に「取り込み用データの作成」ボタンが表示される | 画面確認 | REQ-F-001・C-01 |
| M-02 | 押下中にボタンが非活性になり「取り込み用データを作成しています…」が表示される | 画面確認 | REQ-F-001 |
| M-03 | 完了後、**押下前の活性状態に戻る**（非活性で描画されたボタンが活性化されない） | 画面確認（設計 §6.3 の JS 変更点） | REQ-F-009（D-09） |
| M-04 | `unavailable` のときダウンロードされず、メッセージが `is-error` で表示される | 画面確認 | REQ-F-009・C-16 |
| M-05 | 出力した CSV を ASP『資産／異動情報修正入力』のシートへ貼り付け、9 列（1・2・3・16・38・44・59・64・65 列目）の列位置がずれない | 受け入れ確認（利用者による実機確認） | REQ-F-003・C-11 |
| M-06 | 貼り付け後、摘要のセル内改行・行ずれが起きない | 受け入れ確認 | REQ-F-006・C-15 |

---

## 5. テスト環境

### 5.1 テスト実行コマンド

| コマンド | 範囲 | 本機能での用途 |
|---|---|---|
| `make test-fast` | `domain` + `use_cases`（DB 不要） | **TDD サイクル中の既定**。§2.1・§2.2 のテストはこれで回る |
| `make test-all` | 全テスト（DB あり） | §2.4 の Interfaces 層を含む全体確認。コミット前に実行する |
| `make test-cov` | 全テスト + カバレッジ | Phase 5 完了時の確認 |

個別実行の例:

```
pytest application/asset_inventory/tests/test_asp_import.py -k TC_AIV_ASP_050
```

### 5.2 テスト配置

**既存の資産棚卸結果アプリのテストはフラット構成**（`application/asset_inventory/tests/*.py`）である。
本機能でもこれを踏襲し、レイヤー別ディレクトリを新設しない（既存 30 ファイルの移動を伴う変更は本機能のスコープ外）。

| レイヤー | ファイル |
|---|---|
| Domain（ASP） | `tests/test_asp_import.py` |
| Domain（スナップショット） | `tests/test_reconcile_cache.py` |
| Domain（追加コード部品） | `tests/test_asset_fields.py` / `tests/test_row_display.py` |
| Application | `tests/test_usecase_export_asp_import.py` / `tests/test_usecase_list_page.py`（TC-AIV-UC-032 の改修） |
| Interfaces | `tests/test_asset_inventory_views.py` |

### 5.3 テストデータの準備方法

| 対象 | 方法 |
|---|---|
| `ReconcileRow` | 既存のヘルパー関数 `_row()` / `_comparisons()`（`tests/test_asp_import.py`）を使う。fixture 化せず、テストごとに必要な差異だけを指定する |
| 突合結果スナップショット | `ReconcileCache` を直接組み立て、`dict` のセッションへ保存する。DB を使わない |
| desknet's の応答 | 既存の `_mock_list_all` / `_counting_mock_list_all` / `_list_all_site_master_down`（`tests/test_usecase_list_page.py`）を再利用する。**呼び出し回数の検証には `_counting_mock_list_all` を使う**（C-09・C-16） |
| 認証済みユーザー | 既存の `general_affairs_user` / `production_only_user` fixture を使う（`conftest.py`） |
| Oracle 接続 | 既存方針どおりモック既定。本機能では使用しない |

---

## レビュー履歴

（test-design-review-l1 / Codex クロスレビュー（L4）の結果をここに追記する）

### 仕様変更 (2026/08/26 16:43) — 追加 4 列（44・59・64・65 列目）の反映

**契機**: 利用者提供の ASP 貼り付けレイアウト（2026/08/26）で 44・59・65 列目の対応が判明（**D-11**）、続いて「メーカーコードを旧資産番号の前（抽出コード１８）に追加してください。desknet's にメーカーコードはあります」との指示により 64 列目の対応が判明した（**D-13**）。本書は D-11 が未反映だったため、**D-11 と D-13 をまとめて反映**した。

**変更内容**:

| # | 箇所 | 変更 |
|---|---|---|
| 1 | ヘッダー | 更新日を 2026/08/26 に設定 |
| 2 | §1.1 テスト対象 | 追加コード部品（`manager_code` / `usage_category_code` / `manufacturer_code`）の取得・保持・セッション往復を `ports.py` / `row_display.py` / `reconcile_cache.py` の単体テスト対象として追加 |
| 3 | §2.1(a) TC-AIV-ASP-003 | 「ASP に対応列のない差異だけの行」→「メーカー名だけに差異がある行」に改題（D-13 により対応列が存在するため） |
| 4 | §2.1(b) TC-AIV-ASP-015 | 「16 列目に出力されない」→「16 列目ではなく 44 列目に出力される」。対応 REQ を REQ-F-004（**D-07・D-11**）・**C-18** に変更（D-05 参照を除去） |
| 5 | §2.1(b) TC-AIV-ASP-017 | 空欄列を **70 列 → 66 列**、値の入る列を `1・2・3・16・38・44・59・64・65` に改訂 |
| 6 | §2.1(b) 新規 TC | **TC-AIV-ASP-080〜085** を追加（44 列目 C-18 / 59 列目 C-19 / **64 列目 C-22** / 65 列目 C-20 / 6 列目常時空欄 C-21 / メーカー名のみ差異の行は 3 列 C-14） |
| 7 | §2.1(d) 新規 TC | **TC-AIV-ASP-044・045** を追加（追加 4 列の `M`・12 byte 境界と全角混入） |
| 8 | §2.1(e) TC-AIV-ASP-059 | トリム対象に管理者コード・使用区分コード・メーカーコード・旧資産番号コードを追加 |
| 9 | §2.5 改修・削除一覧 | `test_TC_AIV_ASP_015` / `017` の改修、`ROW_UNMAPPED_ONLY` を使うテストの置換、`DIFF_ASSETS` / `DIFF_INVENTORY` フィクスチャの改修を追加 |
| 10 | §2.6 トレーサビリティ | REQ-F-003 に 44/59/64/65 列目と TC-080〜084、REQ-F-004 に TC-085、REQ-F-007 に TC-045 を追加。REQ-F-004 の要旨から「対応列のない差異は出力しない」を削除 |
| 11 | §3.1 テストデータ | `ROW_ALL_DIFF` を 9 列すべてに値が入る行に拡張。**`ROW_UNMAPPED_ONLY` を削除**し `ROW_MANUFACTURER_ONLY`・`ROW_CODE_ONLY` に置換 |
| 12 | §4.1 境界値 | 値を入れる列位置を 9 列 / 66 列に改訂。追加 4 列の領域長（12/13 byte）の行を追加 |
| 13 | §4.4 手動確認 | M-05 の確認対象を 9 列（1・2・3・16・38・44・59・64・65 列目）に明記 |

**削除した記述**: §3.1 の `ROW_UNMAPPED_ONLY`（1 行）のみ。ほかは既存行の改訂または追記であり、削除はない。

**再実施が必要な受け入れ確認**: M-05・M-06（C-11。ASP『資産／異動情報修正入力』への実機貼り付け確認）。出力列が 5 列 → 9 列に増えたため、利用者による再確認が必要。

### 追補 (2026/08/26 17:02) — 追加コード部品の Domain テストケースの明記

**契機**: 上記の仕様変更で §1.1 テスト対象に「追加コード部品の取得・保持・セッション往復」を加えたが、§2.1 のテストケース表に対応する行が無く、Phase 5（実装）で書くべきテストが特定できない状態だった。

| # | 箇所 | 変更 |
|---|---|---|
| 1 | §2.1(h) 新規 TC | **TC-AIV-DOM-07M・07N** を追加（追加コード部品 3 件のセッション往復と、旧形式セッションの後方互換） |
| 2 | §2.1(i) 新設 | **TC-AIV-DOM-060〜062** を追加（部品一覧への 3 件の追加、突合結果行への取り込み、コード未設定の記録での空欄） |
| 3 | §2.6 トレーサビリティ | REQ-F-003 に TC-AIV-DOM-07M・07N・060〜062 を追加 |
| 4 | §5.2 テスト配置 | Domain（追加コード部品）の行を追加（`tests/test_asset_fields.py` / `tests/test_row_display.py`） |

**削除した記述**: なし（すべて追記）。


### 仕様変更 (2026/08/27 11:00) — 半角への強制変換と領域長の切り捨て

**契機**: requirements.md（D-14・C-23〜C-25）と design.md（DD-10・`AdjustedValue`）の改訂に追随。

| # | 該当箇所 | 変更 |
|---|---------|------|
| 1 | ヘッダー | 更新日 2026/08/27 |
| 2 | §2.1(d) | `violations()` を直接呼ぶ TC は影響を受けない旨と、`from_reconcile_row` 経由の TC は改修が要る旨を注記 |
| 3 | §2.1(d2) | **新設**。`AdjustedValue` の TC-AIV-ASP-086〜100（15 件）を追加 |
| 4 | §2.1(f) | TC-AIV-ASP-101〜104（警告種別・寄せ前後の表示・ブロック順）を追加 |
| 5 | §2.5 | 既存 TC の改修・削除が無いこと（`violations()` を直接呼ぶため）を明記 |
| 6 | §2.6 | REQ-F-006・REQ-F-007 の対応 TC を更新。**DD-10** の行を追加 |
| 7 | §3.2 | 異常系テストデータを 7 件追加 |
| 8 | §4.1 | 境界値を 4 行追加（変換の適用有無・長音記号・切り捨ての境界と対象列） |
| 9 | §4.2 | #6 の期待を書き換え、#6-2・#6-3 を追加 |

**採番の補足**: tasks.md の当初計画では TC-076〜083 としていたが、**TC-AIV-ASP-080〜085 が既に使用済み**のため
**086〜104** に採り直した（076〜079 は欠番のまま残す）。

**削除した TC**: なし（追加のみ。既存 TC の改修も無し）。

### 仕様変更 (2026/08/27 14:40) — 半角変換の警告を出さない（D-15）

requirements.md（D-15・C-23）と design.md（DD-11）の改訂に追随し、以下の 3 件を改訂した。

| # | 該当箇所 | 変更 |
|---|---------|------|
| 1 | TC-AIV-ASP-101 | 期待結果を**反転**。「`HALF_WIDTH_CONVERTED` が 1 件」→「警告が 0 件・`message()` が空文字」 |
| 2 | TC-AIV-ASP-103 | 入力を `DDGー380C`（半角変換）→ `RGSHL4-60-50-L-S`（切り捨て）に差し替え。半角変換は警告を持たなくなったため、寄せ前後の表示は切り捨てで検証する |
| 3 | TC-AIV-ASP-104 | ブロック順を 5 種別 → **4 種別**（違反 → 切り捨て → 改行置換 → 拠点マスタ縮退）に |
| 4 | TC-AIV-ASP-032 | **既存 TC の改修**。`from_reconcile_row()` 経由で全角値を与える唯一の既存 TC であり、半角変換の警告が消えたことで `message()` が空になる。期待結果を「16 列目が `SN100`・`message()` が空文字」に改め、§2.5 の「既存 TC の改修は無い」という注記も訂正した |

**削除した TC**: なし（TC-AIV-ASP-086〜100 の `AdjustedValue` 系はすべて残す。
`half_width_converted` フィールド自体は DD-11 により保持されるため）。
