# 機能設計書: ASP 取り込み用データ作成

文書ID: DESIGN-ASP-IMPORT-DATA-2026-001
作成日: 2026/08/26
更新日: 2026/08/27
対応文書: [requirements.md](requirements.md)（REQ-ASP-IMPORT-DATA-2026-001）、[資産棚卸結果_機能仕様書.md](../../資産棚卸結果_機能仕様書.md)（REQ-ASSET-INVENTORY-2026-001）、[ubiquitous_language.md](../../ubiquitous_language.md)（UL-ASSET-INVENTORY-2026-001）、[strategic_design.md](../../../../../docs/strategic_design.md)（版 1.2）、ASP 取り込み用 CSV マッピング表（利用者提供・2026/08/26。メーカーコードの追加を含む）
アーキテクチャreference: django-clean-architecture version 1.0（updated 2026-04-11）

---

## 1. 設計の目的

要件定義書 REQ-ASP-IMPORT-DATA-2026-001 が求める「突合結果の変化点を ASP『資産／異動情報修正入力』へ
貼り付けられる CSV として出力する」機能を、資産棚卸結果コンテキストの既存レイヤー構成の上に実現する。

本設計で技術的に確立するのは次の 4 点である。

| # | 確立すること | 対応要件 |
|---|---|---|
| 1 | **貼り付けレイアウト（V-309）とチェック仕様（V-310）を domain 層の値オブジェクトとして表現する**。75 列の並び・領域長・チェック種別を 1 か所に閉じ込め、列位置の知識が use_cases / interfaces に漏れないようにする | REQ-F-003・REQ-F-004・REQ-F-007 |
| 2 | **取り込み用データの作成を突合結果スナップショット（V-308）だけを入力とする処理にする**。desknet's への突合用 API 呼び出しを発生させない | REQ-NF-003・REQ-F-009 |
| 3 | **値の整形と警告の生成を分離せず 1 度の走査で確定させる**。摘要の改行置換（D-08）とチェック仕様違反を同じ警告集合に集約する | REQ-F-006・REQ-F-007 |
| 4 | **ボタンの活性・非活性をサーバ側で判定する**。スナップショットが無い状態では押せないようにし、直接要求が届いた場合も desknet's を呼ばずに終える | REQ-F-009（D-09） |

> 本機能は既に一部が実装済みである（`domain/value_objects/asp_import.py`・`use_cases/export_asp_import.py`・
> `interfaces/views.py::export_asp_import` ほか）。本設計書は **要件定義書を正**として、既存実装との差分を
> §7 に明示する。

---

## 2. 対象コンテキスト

`docs/strategic_design.md`（版 1.2）における位置づけは以下のとおり。

| 項目 | 内容 |
|---|---|
| 境界づけられたコンテキスト | **E: 資産棚卸結果** |
| サブドメイン分類 | 支援サブドメイン |
| 上流／下流 | desknet's NEO（上流・**腐敗防止層**、参照のみ）／ **ASP**（下流・**順応者（ファイル連携・片方向）**） |
| 本機能が越えてはならない境界 | ASP への書き込み・取り込み結果の照合は本コンテキストの責務ではない（貼り付けは利用者の手作業。REQ-NF-005） |

**コンテキスト境界に関する設計上の帰結**:

- ASP は順応者であり、貼り付けレイアウト（75 列）を**こちらから変更できない**。したがってレイアウトは
  domain 層に**定数として写し取る**（外部から与えられる契約であり、本コンテキストのビジネスルールではない）。
- ASP へのネットワーク接続・認証は設計対象に含めない。出力の到達点は「利用者のダウンロードファイル」までである。
- 基幹 Oracle（core SYS-003）は本機能に一切関与しない。ASP（SYS-302）と基幹システムは別物である。

---

## 3. アーキテクチャ概要

reference（django-clean-architecture version 1.0）のレイヤー構成に従い、本機能は次のレイヤーを使用する。

```
interfaces ──▶ use_cases ──▶ domain ◀── infrastructure
   │              │            │              │
   │              │            │              └─ 本機能では新規追加なし
   │              │            │                 （desknet's ゲートウェイを呼ばない。DD-01）
   │              │            └─ value_objects/asp_import.py（貼り付けレイアウト・整形・警告）
   │              │               value_objects/reconcile_cache.py（突合結果スナップショット）
   │              └─ export_asp_import.py（ExportAspImport / AspImportResult）
   └─ views.py::export_asp_import / urls.py / templates / static/js
```

| レイヤー | 本機能で使うもの | Django 依存 |
|---|---|---|
| domain | `value_objects/asp_import.py`（新規分含む）、`value_objects/reconcile_cache.py`（既存・拡張）、`repositories/ports.py`（既存 `ReconcileRow` を参照） | **禁止**（純粋 Python のみ） |
| use_cases | `use_cases/export_asp_import.py` | **禁止** |
| infrastructure | **追加なし**（DD-01 によりゲートウェイ依存を持たない） | 可 |
| interfaces | `interfaces/views.py`・`interfaces/urls.py`・`interfaces/wiring.py`・`templates/asset_inventory/list.html`・`static/js/asset-inventory-list.js` | 可 |

**依存方向の遵守**:

- `use_cases/export_asp_import.py` は `domain/` のみを import する（Django・infrastructure を import しない）。
- `interfaces/views.py` は `interfaces/wiring.py` 経由でユースケースを取得する。use_cases / infrastructure / models を直 import しない。
- セッション（Django の `request.session`）は **`dict` 互換のオブジェクト**として use_cases / domain に渡す。
  型注釈は `dict[str, Any] | None` とし、Django の型に依存しない（既存 `reconcile_cache.py` の方針を踏襲）。

**DI 方針**: DI コンテナは使用しない。組み立ては `interfaces/wiring.py` のみで行う（`composition.py`・`services/` は作らない）。

### 3.1 主要な設計判断

| ID | 設計判断 | 理由 | 対応要件 |
|---|---|---|---|
| DD-01 | `ExportAspImport` は **突合結果スナップショット（V-308）のみを入力**とし、`ListAllRecordsFn`（desknet's ゲートウェイ）への依存を持たない | REQ-NF-003「突合結果を得るための desknet's API を呼び出さない」を**型の上で保証**する。依存が無ければ呼びようがない。REQ-F-009 の「直接 URL を指定された場合も呼び出さない」も自動的に満たす | REQ-NF-003・REQ-F-009 |
| DD-02 | 突合結果スナップショットに **拠点マスタ縮退フラグ（`site_warning`）** を持たせ、縮退した突合結果も保存する。ただし既存の `load_reconciled_data(use_snapshot=True)` 経路は縮退スナップショットを**採用しない** | REQ-F-009「拠点マスタのみの取得失敗では出力を中止しない」と、既存の §7.4.1「縮退結果はキャッシュしない（次回表示で再取得する）」を両立させる。一覧表示は常に `use_snapshot=False` で再取得するため、保存しても表示の鮮度は落ちない | REQ-F-009・機能仕様書 §7.4.1 |
| DD-03 | 摘要の改行置換は **整形結果と置換有無を同時に返す関数**で行い、呼び出し側が「置換したか」を判定し直さない | REQ-F-006 の整形と REQ-F-007 の警告が同じ事実（D-08）を二重に判定すると、両者がずれる余地が生まれる | REQ-F-006・REQ-F-007（D-08） |
| DD-04 | 警告を **種別付きの値オブジェクト（`AspImportWarning`）とそのファーストクラスコレクション（`AspImportWarnings`）** で表現する。文字列の組み立ては最後の 1 か所に限る | 「チェック仕様違反」と「改行置換」は意味が異なる（後者は違反ではない）。種別を保持すればテストも表示も種別単位で書ける。reference のファーストクラスコレクション規約にも従う | REQ-F-007 |
| DD-05 | ボタンの活性判定は **domain の `has_amendment_snapshot(session, management_id)`** で行い、`views` はその結果を `can_export_asp_import` としてテンプレートへ渡すだけにする。JavaScript 側では活性判定を行わない | 判定根拠（セッション上のスナップショットの有無）はサーバにしか無い。判定そのものを domain に置くことで、interfaces にビジネス判断が漏れるのを防ぐ | REQ-F-009（D-09） |
| DD-07 | **desknet's 由来の例外を捕捉する経路（`execute_safe`）を廃止**し、`AspImportStatus` による分岐だけにする | DD-01 で外部通信が無くなるため、捕捉すべき例外が存在しない。捕捉だけ残すと「呼んでいるかもしれない」と読める | REQ-NF-003 |
| DD-06 | 出力は**一括生成**（`StreamingHttpResponse` を使わない）。行数上限を設けない | D-10。対象は 1 棚卸の修正対象行のみで、REQ-NF-004（5 秒以内）を満たす規模。上限値は実測後に決める継続課題（SD-2） | REQ-NF-004（D-10） |
| DD-08 | **差異の判定は名称部品で行い、ASP へ出力するのはコード部品**とする。そのため `ASSET_FIELDS` / `INVENTORY_FIELDS` に `管理者コード`・`使用区分コード`・`メーカーコード` を追加し、`ReconcileRow` に `manager_code` / `usage_category_code` / `manufacturer_code` を持たせる | ASP のチェック仕様は 44・59・64 列目とも `M`（半角英数記号）であり、`管理者名称`・`使用区分`・`メーカー` の日本語名称をそのまま貼り付けると取り込みエラーになる。一方、画面の変化点判定（A-301）は利用者が読む名称で行う必要がある。判定と出力で参照する部品を分けることで両立させる。旧資産番号は判定・出力とも `旧資産番号コード` のため読み替え不要 | D-11・D-13・REQ-F-003・REQ-F-004 |
| DD-10 | **値を ASP の書式へ寄せる責務を `AspFieldCheck` に持たせる**。`adjusted(value) -> AdjustedValue` が「半角変換 → 領域長切り捨て」を順に適用し、変換・切り捨ての有無を同時に返す。`violations()` は**寄せたあとの値**に対して呼ぶ | D-14。列ごとの「何を許すか」（`checks`・`max_bytes`）を既に持つのは `AspFieldCheck` であり、「その書式へどう寄せるか」も同じ場所にあるのが自然。DD-03（整形と警告が同じ事実を二重に判定しない）と同じ理由で、寄せた事実は戻り値に含める。呼び出し側が「変換したか」を値の比較で判定し直す余地を残さない | REQ-F-006・REQ-F-007（D-14） |
| DD-11 | **`AdjustedValue.half_width_converted` は保持するが、警告は組み立てない**。半角変換の事実は戻り値に残し、`AspImportWarnings` へは載せない | D-15。半角化は書式合わせであり値の情報が失われないため、毎回通知すると本当に確認が要る指摘（違反・切り捨て）が埋もれる。一方でフィールドを消すと DD-10 の「寄せた事実を戻り値に含める」が崩れ、将来「変換した件数だけ出す」等に戻すときに再設計が要る。**判定（事実の保持）と通知（警告の組み立て）を分ける** | REQ-F-007（D-15） |
| DD-09 | 追加する 4 コード（`管理者コード` V-312 / `使用区分コード` V-313 / `旧資産番号コード` V-314 / `メーカーコード` V-315）に**専用の値オブジェクトを設けない**。`ASP_FIELD_CHECKS` の列定義（`M`・12 byte）と整形関数だけで扱う | 4 者はチェック仕様も整形規則も同一で、振る舞いはいずれも `AspFieldCheck` に委譲される。型を増やしても表現力が増えず、列定数・チェック仕様・型の三重管理になる。`DepartmentCode`（V-311）は既存資産のため据え置く | D-11・D-13 |

---

## 4. ドメインモデル

### 4.1 エンティティ

**本機能で新規に追加するエンティティはない。**

本機能が扱うのは既存の突合結果（`ReconcileRow`）から導かれる**派生的な出力**であり、識別子を持ち
ライフサイクルを通じて状態が変化するものは登場しない。

| 参照する既存の型 | 位置 | 本機能での役割 |
|---|---|---|
| `ReconcileRow` | `domain/repositories/ports.py` | 突合結果 1 行。資産番号・資産枝番・管理部門コード（`site_code`）・シリアルNo.（`serial_number`）・摘要（`summary`）・変化点（`field_comparisons`・`has_diff`）・突合状況（`match_status`）を保持する |
| `ReconcileCache` | `domain/value_objects/reconcile_cache.py` | 突合結果スナップショット（V-308）。`management_id` と `rows` を保持する |

### 4.2 バリューオブジェクト

すべて `domain/value_objects/asp_import.py` に配置する（Django 非依存・`@dataclass(frozen=True)`）。

#### (a) 貼り付けレイアウト — `AspPasteLayout`（V-309）

ASP『資産／異動情報修正入力』が受け付ける列の並びと総列数（75 列固定）を表す。

| 属性 / 定数 | 型 | 内容 |
|---|---|---|
| `ASP_COLUMN_COUNT` | `int` | `75`（固定） |
| `COLUMN_ASSET_NUMBER` / `COLUMN_BRANCH_NUMBER` / `COLUMN_DEPARTMENT_CODE` / `COLUMN_MODEL_NUMBER` / `COLUMN_SUMMARY` | `int` | `1` / `2` / `3` / `16` / `38`（1 始まり） |
| `COLUMN_MANAGER_CODE` / `COLUMN_USAGE_CATEGORY_CODE` / `COLUMN_OLD_ASSET_NUMBER` | `int` | `44` / `59` / `65`（1 始まり。D-11） |
| `COLUMN_MANUFACTURER_CODE` | `int` | `64`（1 始まり。抽出コード１８。D-13） |
| `blank_columns()` | `tuple[str, ...]` | 75 個の空文字を返す。ここに値を差し込んで 1 行を作る |

- **不変条件**: 出力される 1 行の列数は常に `ASP_COLUMN_COUNT` と一致する（値を入れない 66 列も区切り文字を出す。REQ-F-005）。
- 全 75 列の一覧は要件定義書 §9 付録を正とする。**設計側で列一覧を再掲しない**（二重管理を避けるため、コード上は上記 9 列の位置定数のみを持つ）。
- **6 列目（取得日付）の位置定数は持たない**。ASP 側に対応列はあるが本機能では常に空欄とするため（D-12）。定数を置くと「いずれ出す」と読めるため置かない。

#### (b) チェック仕様 — `AspFieldCheck`（V-310）

貼り付けレイアウトが各列に課す入力チェックの種別と領域長を表す。

| 属性 | 型 | 内容 |
|---|---|---|
| `position` | `int` | ASP 上の列位置（1 起点）。`1` / `2` / `3` / `16` / `38` / `44` / `59` / `64` / `65` |
| `label` | `str` | 表示名（`資産番号`・`資産枝番`・`管理部門コード`・`型番`・`摘要`・`管理者コード`・`使用区分コード`・`メーカーコード`・`旧資産番号コード`） |
| `checks` | `frozenset[str]` | `O`（必須入力）／`M`（半角英数記号）／`I`（整数）／`P`（全角可） |
| `max_bytes` | `int` | 領域長（byte）。`12` / `4` / `12` / `24` / `64` / `12` / `12` / `12` / `12` |
| `truncatable` | `bool` | 領域長超過時に末尾を切り捨てるか。`False` / `False` / `True` / `True` / `True` / `True` / `True` / `True` / `True`（D-14） |

- **判定メソッド**: `violations(value: str) -> tuple[str, ...]` — 与えられた値に対する違反理由を返す。
  理由文の主語は `{label}（{position} 列目）` とし、利用者が ASP 上のどのセルを見ればよいか分かるようにする（REQ-F-007）。
- `position` は `ASP_FIELD_CHECKS` のキーと重複するが、**`AspFieldCheck` 単体で理由文を組み立てられるようにする**ために属性としても持つ。
  辞書は `check.position` をキーに組み立てるため、キーと属性は構造的に一致する。
- **バイト数の数え方**: 領域長は byte 規定のため **cp932 換算**で数える（全角 2 byte）。cp932 で表現できない文字を含む場合は
  UTF-8 換算の byte 数で代替評価する（安全側＝多めに数える）。
- **寄せメソッド**: `adjusted(value: str) -> AdjustedValue` — D-14 に従い、値を ASP の書式へ寄せる（DD-10）。
  適用順は **(1) 半角変換（`M` を持つ列のみ） → (2) 領域長の切り捨て（`truncatable` が真の列のみ）**。
  空文字はどちらも適用せずそのまま返す。詳細な規則は §4.2(d) の `AdjustedValue` を参照する。
- **`truncatable`**: `bool`（既定 `True`）。領域長超過時に末尾を切り捨てるかどうか。
  **資産番号（1 列目）・資産枝番（2 列目）のみ `False`** とする。この 2 列は ASP 上で更新対象の資産を特定するキーであり、
  切り詰めると別の資産を書き換えてしまうため、超過しても値を変えずチェック違反として警告する（D-14）。
- 出力する 9 列分のチェック仕様は `ASP_FIELD_CHECKS: dict[int, AspFieldCheck]`（キー＝列位置）として保持する。
- 追加した 44・59・64・65 列目のチェックは要件 §9 付録どおり **`M`（半角英数記号）・12 byte** で共通。必須入力（`O`）ではない。

#### (c) 管理部門コード — `DepartmentCode`（V-311）

拠点を ASP 上で識別するコード。値は棚卸データの `site_code` から取り、前後の空白を除く。
独立した型を設けるのは**チェック仕様（`M`・12 byte）を型に結びつける**ためであり、
振る舞いは `AspFieldCheck` に委譲する。

`管理者コード`（V-312）・`使用区分コード`（V-313）・`旧資産番号コード`（V-314）・`メーカーコード`（V-315）は
チェック仕様・整形規則とも `DepartmentCode` と同一のため、**専用の型を設けない**（DD-09）。
値は突合結果の対応属性（`manager_code` / `usage_category_code` / `old_asset_number` / `manufacturer_code`）から取り、
前後の空白を除いて `ASP_FIELD_CHECKS` に照らす。

#### (d) 整形結果 — `NormalizedValue`

DD-03 に対応する。値の整形と「書き換えたか」を同時に返す。

| 属性 | 型 | 内容 |
|---|---|---|
| `value` | `str` | 整形後の値 |
| `newline_replaced` | `bool` | 改行（CR・LF・CRLF）を半角空白 1 つに置換したか（D-08） |

整形規則（REQ-F-006）:

| 対象 | 規則 |
|---|---|
| 資産番号・管理部門コード・シリアルNo.・管理者コード・使用区分コード・メーカーコード・旧資産番号コード | 前後の空白を除く。ゼロ埋め・桁合わせは行わない |
| 資産枝番 | 前後の空白を除いたうえで、**数字のみの場合に限り** 4 桁ゼロ埋め。空はそのまま空欄（チェック `O` 違反として警告）。数字以外を含む場合もそのまま出力し警告 |
| 摘要 | 前後の空白を除き、**CRLF → LF → CR の順で半角空白 1 つに置換**する（CRLF を 2 つの空白にしないため順序が重要）。置換したら `newline_replaced = True` |

##### 調整済み値 — `AdjustedValue`（DD-10）

上記の整形に続けて、値を ASP の書式へ寄せた結果を表す。`AspFieldCheck.adjusted()` が返す。

| 属性 | 型 | 内容 |
|---|---|---|
| `original` | `str` | 寄せる前の値（警告に「変換前」として出す） |
| `value` | `str` | 寄せたあとの値（CSV に出力し、`violations()` にかける） |
| `half_width_converted` | `bool` | 半角へ変換したか（`original != 変換後` のとき真） |
| `truncated` | `bool` | 領域長を超えたため末尾を切り捨てたか |

**(1) 半角変換の規則**（チェック `M` を持つ 7 列: 1・3・16・44・59・64・65 列目）

| 段 | 処理 | 例 |
|---|---|---|
| 1 | Unicode 正規化 **NFKC** | `ＡＢＣ－１２３` → `ABC-123`、`　`（U+3000）→ 半角空白、`①` → `1` |
| 2 | NFKC で変換されない**ダッシュ類・引用符**を個別に写像 | `‐‑‒–—―−` → `-`、`‘’` → `'`、`“”` → `"` |
| 3 | **長音記号** `ー`（U+30FC）・`ｰ`（U+FF70）を `-` へ写像。ただし**値に かな・カナ・漢字 が残っている場合は適用しない** | `DDGー380C` → `DDG-380C` ／ `モーター100` は**変換しない** |

- 段 2 が必要なのは、NFKC が U+2010〜U+2015・U+2212 のダッシュ類と U+2019 を変換しないため（実測で確認済み）。
- 段 3 を無条件に適用すると `モーター` が `モ-タ-` に壊れる。長音記号は「ハイフンの打ち間違い」と「カナ語の一部」の
  両方でありうるため、**同じ値の中に日本語文字が残っているかどうか**を手がかりに切り分ける（D-14）。
  判定に使う範囲は ひらがな `U+3041–U+309F` / カタカナ `U+30A1–U+30FB`・`U+30FD–U+30FF` / 漢字 `U+4E00–U+9FFF`。
  **長音記号 U+30FC 自身は判定範囲から除く**（長音だけの値を「日本語」と見なして変換を止めないため）。
  半角カナは段 1 の NFKC で全角カナになるため、この判定に自然に乗る。
- カナ語が残った値は変換されないまま `violations()` にかかり、従来どおり `M` 違反として警告される（利用者が手で直す）。
- チェック `P` の摘要（38 列目）と、チェック `M` を持たない資産枝番（2 列目）は**半角変換の対象外**。

**(2) 領域長切り捨ての規則**（`truncatable` が真の 7 列: 3・16・38・44・59・64・65 列目）

- 半角変換のあと、cp932 換算のバイト数が `max_bytes` を超える場合、**先頭から 1 文字ずつ積み上げ、
  加えると超える文字の手前で打ち切る**。これにより全角 1 文字（2 byte）が途中で分断されることがない
  （例: 上限 5 byte・`AB漢字` → `AB漢`。4 byte で止め、5 byte 目に半分だけ残さない）。
- 資産番号・資産枝番（`truncatable = False`）は切り捨てず、超過をチェック違反として警告する（D-14）。

#### (e) 取り込み用データの 1 行 — `AspImportRow`（V-306 の構成要素）

| 属性 | 型 | 内容 |
|---|---|---|
| `columns` | `tuple[str, ...]` | 75 列の値。長さは `ASP_COLUMN_COUNT` に一致する |
| `asset_label` | `str` | 警告表示に使う識別ラベル（`資産番号-資産枝番`。資産枝番が空なら資産番号のみ） |
| `warnings` | `AspImportWarnings` | この行に対する警告（違反・置換） |

#### (f) 修正対象行のコレクション — `AmendmentRows`（V-307）

`ReconcileRow` の**ファーストクラスコレクション**。reference の規約に従い `tuple[ReconcileRow, ...]` を
そのまま引き回さない。Entity ではなく突合結果の値の集まりであるため `domain/value_objects/` に置く。

| メソッド | 戻り値 | 内容 |
|---|---|---|
| `select_from(rows)`（クラスメソッド） | `AmendmentRows` | **棚卸済み（`MatchStatus.MATCHED`）かつ変化点あり（`has_diff`）** の行だけを抽出する（REQ-F-002） |
| `is_empty()` | `bool` | 0 件かどうか（REQ-F-008 の分岐に使う） |
| `count()` | `int` | 件数（応答ヘッダーの行数に使う） |
| `to_import_rows()` | `AspImportRows` | 各行を `AspImportRow` に変換する |

#### (g) 取り込み用データ — `AspImportRows`（V-306）

`AspImportRow` のファーストクラスコレクション。

| メソッド | 戻り値 | 内容 |
|---|---|---|
| `render_csv()` | `bytes` | ヘッダー行なし・75 列固定・CRLF・**UTF-8（BOM 付き）** の CSV を返す（REQ-F-005） |
| `warnings()` | `AspImportWarnings` | 全行の警告を連結して返す |

#### (h) 警告 — `AspImportWarning` / `AspImportWarnings`（DD-04）

| `AspImportWarning` の属性 | 型 | 内容 |
|---|---|---|
| `kind` | `AspWarningKind` | `CHECK_VIOLATION`（チェック仕様違反）／ `VALUE_TRUNCATED`（領域長超過のため末尾を切り捨てた・D-14）／ `NEWLINE_REPLACED`（摘要の改行置換）／ `SITE_UNAVAILABLE`（拠点マスタ縮退により管理部門コードを出力できなかった） |
| `asset_label` | `str` | 該当資産の識別ラベル |
| `detail` | `str` | 違反理由。**項目名と ASP 上の列位置を含む**（例: `資産枝番（2 列目）が空です`） |
| `value` | `str` | 違反した値、または**寄せる前**の値。空文字のときは警告文に値を出さない（`O` 違反・`NEWLINE_REPLACED`・`SITE_UNAVAILABLE`） |
| `adjusted_value` | `str` | **寄せたあと**の値（`VALUE_TRUNCATED` のみ）。空文字でなければ警告文に `→「…」` として続けて出す |

`AspImportWarnings`（ファーストクラスコレクション）:

| メソッド | 戻り値 | 内容 |
|---|---|---|
| `of_kind(kind)` | `AspImportWarnings` | 種別で絞り込む |
| `asset_labels()` | `tuple[str, ...]` | 該当資産番号を重複なく返す |
| `message()` | `str` | 画面表示用の警告文を組み立てる。警告が無ければ空文字 |

**警告文の構成**（REQ-F-007。種別ごとにブロックを作り、複数あれば改行で連結する）:

```
ASP のチェック仕様に反する値が {N} 件あります。値を直してから貼り付けてください。
・{detail} — {資産番号}「{値}」、{資産番号}「{値}」[ ほか {M} 件]
・{detail} — {資産番号}[ ほか {M} 件]
領域長を超えたため末尾を切り捨てた値が {N} 件あります。切れた内容を確認してください。
・{detail} — {資産番号}「{切り捨て前}」→「{切り捨て後}」[ ほか {M} 件]
摘要の改行を半角空白に置き換えた行が {N} 件あります（資産番号: {最大 10 件を「、」で連結}[ ほか {M} 件]）。内容を確認してください。
拠点マスタを取得できなかったため、管理部門コードは出力していません。拠点名の変化点は手作業で確認してください。
```

ブロックの順序は **違反 → 切り捨て → 改行置換 → 拠点マスタ縮退**（D-14・D-15）。
利用者が手で直す必要のあるもの（違反）を先頭に、値が欠けた可能性のある切り捨てをその次に置く。
**半角変換（REQ-F-006(a)）のブロックは持たない**（D-15・DD-11）。値の情報が失われないためである。
`VALUE_TRUNCATED` の `detail` は `{label}（{position} 列目）を {N} byte に切り詰めました` とし、
違反ブロックと同じく `detail` でグルーピングする。

出力例:

```
ASP のチェック仕様に反する値が 3 件あります。値を直してから貼り付けてください。
・型番（16 列目）に半角英数記号以外が含まれます — 3614-0000「ＡＢＣ－１２３」、3615-0000「ＸＹＺ－９」
・摘要（38 列目）が 64 byte を超えています — 4118-0003「保守契約は毎年 4 月に更新する。担当は総務…」
```

- チェック仕様違反の判定は**寄せたあとの値**に対して行う（DD-10）。半角変換・切り捨てで適合した値は違反ブロックに現れない。
- 半角変換と切り捨てが同じ値に重なった場合、切り捨て警告の `value`（寄せる前の値）は **半角変換前の値**（棚卸データそのまま）とする。利用者が画面で探せる形にするためである（D-15）。
- 見出し行の `{N}` は**該当資産の件数**（重複を除いた `asset_labels()` の数）。1 資産が複数の理由に該当する場合、明細行には理由ごとに現れる。
- 明細行は `detail`（違反理由）で**グルーピング**する。同じ直し方をする資産が 1 行に並び、利用者が対処の単位で読めるため（REQ-F-007）。
- `detail` は `AspFieldCheck` が組み立て、**項目名と列位置**を含む（例: `型番（16 列目）に半角英数記号以外が含まれます`）。列位置は `AspFieldCheck.position` から得る。
- 明細行の並び順は**列位置の昇順**とし、同一列内では検査の順（`O` → `M` → `I` → `N` → `D` → 領域長）に従う。出力のたびに順序が変わらないようにするため（REQ-NF「同一スナップショットからは同一内容」に準じる）。
- 値は `「」` で囲んで示す。**20 文字を超える場合は先頭 20 文字＋`…`** に丸める（画面が読めなくなるのを防ぐため）。値が空文字のときは `「」` を付けない（`O` 違反は「値が無いこと」自体が理由のため）。
- `SITE_UNAVAILABLE` は行単位ではなく**出力全体に対して 1 件**発生する（`AspImportRows` の生成時にスナップショットの `site_warning` から付与する）。

- 資産番号の列挙は**理由ごとに 10 件を上限**とし、超過分は「ほか N 件」に丸める（画面が読めなくなるのを防ぐため）。

`detail` を組み立てる `AspFieldCheck` の定義は §4.2(b) を参照する。

### 4.3 集約

| 集約 | 集約ルート | 境界 | 備考 |
|---|---|---|---|
| 突合結果スナップショット | `ReconcileCache`（V-308） | `management_id` + `rows`（+ `counts` / 各フィルタ選択肢 / `site_warning`） | 本機能から見て **読み取り専用**。ASP 取り込み用データの作成でスナップショットを更新しない |
| 取り込み用データ | `AspImportRows`（V-306） | `AspImportRow` の集合 | スナップショットから**導出される一時的な成果物**。永続化しない |

- 集約間は `management_id`（棚卸データ管理 E-301 の `data_id`）で参照する。
- 取り込み用データ集約は突合結果スナップショットを参照するが、**逆参照は持たない**（片方向）。

### 4.4 ドメインサービス

**新設しない。**

変化点（A-301 の 7 項目）から ASP の列への対応付けは、値オブジェクト内の対応表として持つ。
複数の集約にまたがる調整が発生しないため、ドメインサービスを設ける理由がない。

**変化点 → 列の対応表（REQ-F-003・REQ-F-004。UL A-301 が正）**:

| 変化点の項目名（画面表示名） | `ReconcileRow` の属性 | ASP の列 | 出力条件 |
|---|---|---|---|
| 拠点名 | `site_code` | 3 列目 管理部門コード | 拠点名に差異があるとき |
| **シリアルNo.** | `serial_number` | **16 列目 型番** | シリアルNo. に差異があるとき（D-07） |
| 摘要 | `summary` | 38 列目 摘要 | 摘要に差異があるとき |
| **型番** | `manager_code` | **44 列目 管理者コード** | 型番に差異があるとき（D-11・DD-08） |
| **使用区分** | `usage_category_code` | **59 列目 抽出コード１３（使用区分コード）** | 使用区分に差異があるとき（D-11・DD-08） |
| **旧資産番号** | `old_asset_number` | **65 列目 抽出コード１９（旧資産番号コード）** | 旧資産番号に差異があるとき（D-11） |
| **メーカー名** | `manufacturer_code` | **64 列目 抽出コード１８（メーカーコード）** | メーカー名に差異があるとき（D-13・DD-08） |
| （取得日付） | — | 6 列目（使わない） | 常に空欄。棚卸データ側を正としないため出力しない（D-12） |
| （常時） | `asset_number` / `branch_number` | 1・2 列目 | 差異の有無にかかわらず常に出力（チェック `O`） |

> 差異の判定は既存の変化点判定（A-301）の結果である `ReconcileRow.field_comparisons` の
> `label` / `is_diff` を読むだけとし、本機能で比較をやり直さない（判定ロジックの二重化を避ける）。

> **判定は名称・出力はコード**（DD-08）。44・59・64 列目は判定に使うラベル（`型番`・`使用区分`・`メーカー名`）と
> 出力に使う属性（`manager_code`・`usage_category_code`・`manufacturer_code`）が異なる。`is_diff` を読む対象は
> あくまで名称側のラベルであり、コード側で比較し直さない。3 列目（拠点名 → `site_code`）も同じ構図である。

---

## 5. データモデル

### 5.1 テーブル

**新設・変更ともになし**（REQ-NF-002）。PostgreSQL 側に業務用テーブルを追加しない。

### 5.2 セッション（突合結果スナップショット V-308）

Django セッション（`django_session` テーブル）に保持する既存の構造に **1 キーを追加**する（DD-02）。

| キー | 型 | 追加/既存 | 内容 |
|---|---|---|---|
| `asset_inventory_reconcile_cache.management_id` | `str` | 既存 | 選択中の棚卸の `data_id` |
| `asset_inventory_reconcile_cache.rows[]` | `list[dict]` | 既存 | 突合結果の各行（`asset_number` / `branch_number` / `site_code` / `serial_number` / `summary` / `has_diff` / `match_status` / `field_comparisons` ほか） |
| `asset_inventory_reconcile_cache.counts` | `dict` | 既存 | 突合件数 |
| `asset_inventory_reconcile_cache.site_options` / `asset_number_options` | `list[str]` | 既存 | フィルタ選択肢 |
| `asset_inventory_reconcile_cache.site_warning` | `bool` | **追加** | 拠点マスタの取得に失敗した縮退結果か（DD-02） |

**後方互換**: `site_warning` が無い既存セッションは `False` として読む（`payload.get("site_warning") or False`）。
移行処理は不要（セッションは失効してよいデータであり、キーが無くても従来どおり動く）。

### 5.3 データフロー

```
[一覧画面の表示]
  desknet's ──▶ 突合 ──▶ ReconcileCache ──▶ セッションへ保存（縮退時も保存。DD-02）
                              │
                              └──▶ 画面表示 + ボタンの活性判定（can_export_asp_import）

[取り込み用データの作成]
  セッション ──▶ ReconcileCache ──▶ AmendmentRows.select_from（棚卸済み × 変化点あり）
                                            │
                                            ├──▶ AspImportRows ──▶ CSV（75 列・CRLF・UTF-8 BOM）
                                            └──▶ AspImportWarnings ──▶ 画面メッセージ
  ※ この経路で desknet's API を呼ばない（DD-01）
```

---

## 6. API / インターフェース設計

### 6.1 エンドポイント

| 項目 | 値 |
|---|---|
| URL | `GET /api/asset-inventory/asp-import.csv`（既存・変更なし。kebab-case） |
| ルート名 | `asset_inventory:export_asp_import` |
| 認可 | `@login_required` + 総務メニューグループ（既存の資産棚卸結果と同一。REQ-NF-001） |
| クエリ | `managementId`（必須。選択中の棚卸） |

### 6.2 レスポンス

| 状況 | HTTP | `X-Asp-Import-Status` | 本体 | 付随ヘッダー |
|---|---|---|---|---|
| 出力あり | 200 | `ok` | CSV（`text/csv; charset=utf-8`） | `Content-Disposition: attachment; filename="asp_import_{YYYYMMDDhhmmss}.csv"` / `X-Asp-Import-Rows: {件数}` / 警告があれば `X-Asp-Import-Warning`（**URL エンコード**） |
| 出力対象 0 件（REQ-F-008） | 200 | `empty` | `取り込み対象の変更がありません。`（`text/plain`） | — |
| **スナップショットが無い／棚卸が未選択（REQ-F-009）** | 200 | **`unavailable`（追加）** | `棚卸を選び直してください。`（`text/plain`） | — |

- `X-Asp-Import-Warning` は HTTP ヘッダーが latin-1 しか通さないため **URL エンコードして送り、クライアントで `decodeURIComponent` する**（既存方針を踏襲）。
- **4xx / 5xx を返す経路は認証・認可のみ**である。DD-01 により外部通信が無いため、`503`（アクセスキー未取得）・`502`（desknet's 障害）は本エンドポイントでは発生しない（既存実装からは削除する。§7.1 #6）。
- **ステータスをヘッダーで返す理由**: 0 件・スナップショット無しの場合に「ダウンロードさせずに画面へメッセージを出す」ため、
  クライアントは本文を読む前に分岐する必要がある（リンク遷移ではなく `fetch` で受ける）。

### 6.3 画面（一覧画面 `asset_inventory/list.html`）

| 要素 | 仕様 |
|---|---|
| ボタン | 「取り込み用データの作成」。**既存の CSV 出力ボタンの隣**（REQ-F-001）。現状は `{% if has_list_data %}` の内側にあり棚卸未選択時は描画されないため、**ブロックの外へ移し常に描画する**（D-09 の「非活性」を成立させるため。CSV 出力リンクは従来どおり内側のまま） |
| 活性条件（D-09） | `can_export_asp_import` が真のときのみ活性。偽のときは `disabled` 属性を出力し、`title` に理由（`棚卸を選ぶと作成できます。`）を表示する（2026/08/26 修正。旧文言「棚卸を選択して突合結果を表示してください」は画面表示に用いない用語「突合結果」を含み、既存仕様 TC-AIV-API-003 と衝突するため tasks.md の文言に統一した） |
| `can_export_asp_import` の算出（views） | `突合結果スナップショットが存在し、その management_id が選択中の棚卸と一致する` こと。エラー表示中（`error_message` あり）は偽 |
| メッセージ領域 | 既存の `.aiv-asp-import-message`（`role="status" aria-live="polite"`）。`is-warning` / `is-error` の修飾クラスで色を変える |

**クライアント側の振る舞い（`static/js/asset-inventory-list.js`）**:

1. ボタン押下 → 押下中は `disabled` にし「取り込み用データを作成しています…」を表示する（多重押下の防止）
2. `fetch` で応答を受け、`X-Asp-Import-Status` で分岐する
   - `ok` → Blob をダウンロードし、警告があれば警告文、無ければ `{N} 件の取り込み用データを作成しました。` を表示
   - `empty` / `unavailable` → **ダウンロードせず**本文をメッセージ領域に表示（`unavailable` は `is-error`）
   - それ以外（4xx/5xx）→ 本文を `is-error` で表示
3. 完了後に `disabled` を**押下前の状態に戻す**。現状の実装は無条件に `disabled = false` とするため、サーバが非活性で描画したボタンを活性化してしまう。押下時の値を控えて復元する

**画面遷移は発生しない**（同一画面内でのダウンロードとメッセージ表示のみ）。

### 6.4 ユースケースのインターフェース（use_cases 層）

```
ExportAspImport
  __init__(self)                       # 依存なし（DD-01）
  execute(query, session) -> AspImportResult
```

`AspImportResult`（DTO。`use_cases/export_asp_import.py`）:

| 属性 | 型 | 内容 |
|---|---|---|
| `status` | `AspImportStatus` | `OK` / `EMPTY` / `UNAVAILABLE` |
| `content` | `bytes \| None` | CSV。`OK` 以外は `None` |
| `row_count` | `int` | 出力行数 |
| `message` | `str` | `EMPTY` / `UNAVAILABLE` のときの画面文言 |
| `warning_message` | `str` | 警告文（無ければ空文字） |

- **`access_key` を引数から外す**（DD-01。desknet's を呼ばないため不要）。
- **`execute_safe` を廃止する**（DD-07）。捕捉すべき外部由来の例外が無く、業務的な分岐は `status` で表現する。
- `wiring.py` の `export_asp_import_usecase()` は `ExportAspImport()` を返すだけになる（ゲートウェイを渡さない）。

---

## 7. 既存コードへの変更点

### 7.1 変更対象ファイル一覧

| # | ファイル | レイヤー | 変更概要 | 対応要件 |
|---|---|---|---|---|
| 1 | `domain/repositories/ports.py` | domain | **改修**。`_SHARED_RECORD_FIELDS` に `管理者コード`・`使用区分コード`・`メーカーコード` を追加し（`ASSET_FIELDS` / `INVENTORY_FIELDS` の双方に載る）、`ReconcileRow` に `manager_code: str = ""` / `usage_category_code: str = ""` / `manufacturer_code: str = ""` を追加する | D-11・D-13・DD-08 |
| 2 | `domain/value_objects/row_display.py` | domain | **改修**。`ReconcileRow` 構築時に棚卸データの `管理者コード`・`使用区分コード`・`メーカーコード` を新属性へ詰める（表示項目は変えない） | D-11・D-13・DD-08 |
| 3 | `domain/value_objects/asp_import.py` | domain | **改修**。`AspPasteLayout` / `AspFieldCheck` / `DepartmentCode` / `NormalizedValue` / `AspImportRow` / `AspImportRows` / `AmendmentRows` / `AspImportWarning(s)` を導入。摘要の改行置換（D-08）を追加。44・59・64・65 列目の位置定数・チェック仕様・差異ラベルを追加し、`AspImportRow` の生成で 4 列を差し込む（D-11・D-13）。既存の関数群（`select_amendment_rows` / `build_asp_import_columns` / `render_asp_import_csv` / `check_violations` / `build_check_warning_message`）は**コレクション／VO のメソッドへ移し、モジュール関数は削除する** | REQ-F-002〜007 |
| 4 | `domain/value_objects/reconcile_cache.py` | domain | **改修**。`ReconcileCache` に `site_warning: bool = False` を追加し、シリアライズ／デシリアライズに含める。`management_id` 一致でスナップショットを取り出す `load_amendment_snapshot(session, management_id) -> ReconcileCache \| None` を追加。`reconcile_row_to_dict` / `reconcile_row_from_dict` に `manager_code` / `usage_category_code` / `manufacturer_code` を追加する（セッション往復で失われないようにする） | REQ-NF-003・REQ-F-009・DD-02・D-11・D-13 |
| 5 | `domain/value_objects/reconcile_data.py` | domain | **改修**。縮退結果も `save_reconcile_cache` する（`site_warning=True` を立てて保存）。`use_snapshot=True` の経路では `site_warning=True` のスナップショットを**採用しない**（既存の CSV 出力の挙動を変えない） | DD-02 |
| 6 | `use_cases/export_asp_import.py` | use_cases | **改修**。`ListAllRecordsFn` 依存と `list_management_rows` / `load_reconciled_data` の呼び出しを**削除**し、スナップショット読み出しに置き換える。`AspImportResult` に `status` を追加。`access_key` 引数を削除 | REQ-NF-003・REQ-F-009 |
| 7 | `interfaces/wiring.py` | interfaces | **改修**。`export_asp_import_usecase()` から `_list_all_fn()` の受け渡しを削除 | DD-01 |
| 8 | `interfaces/views.py` | interfaces | **改修**。`export_asp_import` を `status` による分岐に変更し、`unavailable` を追加。`access_key` の解決を削除。`list_page` のコンテキストに `can_export_asp_import` を追加 | REQ-F-009 |
| 9 | `templates/asset_inventory/list.html` | interfaces | **改修**。ボタンを `{% if has_list_data %}` ブロックの外へ移し、`{% if not can_export_asp_import %}disabled title="…"{% endif %}` を付与 | REQ-F-009（D-09） |
| 10 | `static/js/asset-inventory-list.js` | interfaces | **改修**。`X-Asp-Import-Status` の分岐に `unavailable` を追加。完了時に `disabled` を押下前の状態へ戻す | REQ-F-009 |
| 10a | `static/css/app.css` | interfaces | **改修**。`.aiv-asp-import-message` に `white-space: pre-line` を追加する。警告文は複数行で組み立てられるが、`textContent` で `<p>` に流し込むため CSS が既定の `normal` のままだと改行が空白に潰れて 1 行に繋がる | REQ-F-007 |
| 11 | `tests/test_asp_import.py` ほか | tests | **改修・追加**。§4 の VO 単位のテスト、改行置換、スナップショット無しで desknet's を呼ばないことの検証を追加（詳細は test-design.md） | C-01〜C-21 |
| 12 | `docs/資産棚卸結果_機能仕様書.md` / `docs/資産棚卸結果_テスト仕様書.md` | docs | **改修**（Phase 5 完了時）。ASP 取り込み用データの作成を追記 | 要件 §6.2 |

**削除対象の明示**（CLAUDE.md「既存コードの削除を伴う変更は、削除対象を明示してから実行する」）:

| 削除するもの | 位置 | 移設先 |
|---|---|---|
| `select_amendment_rows()` | `asp_import.py` | `AmendmentRows.select_from()` |
| `build_asp_import_columns()` | `asp_import.py` | `AspImportRow` の生成処理 |
| `render_asp_import_csv()` | `asp_import.py` | `AspImportRows.render_csv()` |
| `check_violations()` | `asp_import.py` | `AspFieldCheck.violations()` |
| `build_check_warning_message()` | `asp_import.py` | `AspImportWarnings.message()` |
| `format_branch_number()` | `asp_import.py` | `NormalizedValue` を返す整形関数へ |
| `ExportAspImport.__init__(list_all)` の引数 | `export_asp_import.py` | 削除（依存なし） |
| `execute` の `access_key` 引数 | `export_asp_import.py` | 削除 |
| `execute_safe()` 全体 | `export_asp_import.py` | 削除（DD-07。`status` による分岐に置き換え） |
| `_resolve_access_key` の呼び出し（`export_asp_import` ビュー内） | `interfaces/views.py` | 削除（他のビューでは引き続き使用する） |

### 7.2 既存機能への影響

| 対象 | 影響 |
|---|---|
| 既存の CSV 出力（突合結果一覧） | **仕様変更なし**。DD-02 により縮退スナップショットは `use_snapshot=True` 経路で採用されないため、従来どおり再取得する |
| 一覧画面の表示 | **表示内容の変更なし**。`can_export_asp_import` をコンテキストに追加するのみ |
| 他コンテキスト（ポータル基盤・アクセス管理ほか） | **影響なし**（要件定義書 §4.2） |
| DB スキーマ | 変更なし。セッションの JSON にキーが増えるのみ（`site_warning` / `manager_code` / `usage_category_code` / `manufacturer_code`。いずれも既定値ありで後方互換） |
| desknet's からの取得項目 | `ASSET_FIELDS` / `INVENTORY_FIELDS` に 2 部品が増える。**取得件数・API 呼び出し回数は変わらない**。両アプリに当該部品が存在することは利用者確認済み（2026/08/26） |

---

## 8. エラーハンドリング方針

### 8.1 異常系の一覧

| # | 状況 | 検知箇所 | 振る舞い | 対応要件 |
|---|---|---|---|---|
| 1 | 棚卸が未選択（`managementId` が空） | use_cases | `UNAVAILABLE`。desknet's を呼ばない | REQ-F-009・C-16 |
| 2 | スナップショットが無い（セッション失効・別タブでの切り替え） | use_cases | `UNAVAILABLE`。desknet's を呼ばない | REQ-F-009・C-16 |
| 3 | スナップショットの `management_id` が要求と不一致 | use_cases | `UNAVAILABLE`（古い棚卸の結果を出さない） | REQ-F-009 |
| 4 | 修正対象行が 0 件 | use_cases | `EMPTY`。ダウンロードさせずメッセージ表示 | REQ-F-008・C-07 |
| 5 | 資産枝番が空・数字以外 | domain（`AspFieldCheck`） | **出力は継続**し、`CHECK_VIOLATION` として警告 | REQ-F-006・REQ-F-007 |
| 6 | 領域長超過・全角混入 | domain（`AspFieldCheck`） | まず `adjusted()` で寄せる（半角変換・切り捨て）。切り捨てた事実のみ `VALUE_TRUNCATED` として警告し（**半角変換は既定動作のため警告しない**・D-15）、**寄せてもなお適合しない場合のみ** `CHECK_VIOLATION` として警告 | REQ-F-006・REQ-F-007（D-14・D-15） |
| 6-2 | 長音記号を含むカナ語（`モーター100`） | domain（`AspFieldCheck`） | 語を壊さないため半角変換せず、`CHECK_VIOLATION` として警告（利用者が手で直す） | REQ-F-006（D-14） |
| 6-3 | 資産番号・資産枝番が領域長を超える | domain（`AspFieldCheck`） | **切り捨てない**（更新対象を特定するキーのため）。`CHECK_VIOLATION` として警告 | REQ-F-006（D-14） |
| 7 | 摘要に改行が含まれる | domain（整形） | 半角空白 1 つに置換して**出力を継続**し、`NEWLINE_REPLACED` として警告 | REQ-F-006・REQ-F-007・C-15 |
| 8 | cp932 で表現できない文字 | domain（バイト数計算） | UTF-8 換算で代替評価（安全側）。例外にしない | REQ-F-007 |
| 9 | 拠点マスタのみ取得失敗（縮退スナップショット） | domain | **出力を中止しない**。管理部門コードは空欄のまま出力し、`SITE_UNAVAILABLE` の警告を 1 件付与する | REQ-F-009・DD-02 |
| 10 | セッションの内容が壊れている（想定外の型・欠損キー） | domain | `load_amendment_snapshot` が `None` を返し `UNAVAILABLE`。例外を送出しない | REQ-F-009 |
| 11 | 未ログイン | interfaces（`@login_required`） | `/login` へリダイレクト | REQ-NF-001 |
| 12 | 認可の無いユーザー | interfaces | 既存の資産棚卸結果と同じ扱い（403） | REQ-NF-001 |
| 13 | 同時実行（複数利用者が同じ棚卸で作成） | — | 読み取りと出力のみのため競合しない。排他制御を行わない | REQ-NF-005 |

### 8.2 方針

- **出力を止める異常系は #1〜#4・#10 のみ**。値の不正（#5〜#9）は「警告して出力する」。ASP 側での取り込みエラーに
  利用者が事前に気づけるようにすることが目的であり、出力を止めると転記作業に戻ってしまうため。
- **例外の種類**: use_cases では `AspImportStatus` を返して分岐し、業務的な分岐に例外を使わない
  （`ValueError` で「棚卸が選択されていません」を表現しない）。DD-01 により外部通信が無いため、
  捕捉すべきネットワーク・認証由来の例外は存在しない（`execute_safe` を廃止する。DD-07）。
- **セッションの内容が壊れている場合**（想定外の型・欠損キー）は `load_amendment_snapshot` が `None` を返し、
  `UNAVAILABLE` として扱う。例外を送出して 500 にしない（利用者は棚卸を選び直せば回復できるため）。
- **メッセージは domain 層に定数として置く**（`EMPTY_MESSAGE` / `UNAVAILABLE_MESSAGE`）。interfaces で文言を組み立てない。

---

## 9. リスクと対策

| # | リスク | 影響 | 対策 |
|---|---|---|---|
| 1 | **貼り付けレイアウトの列位置を誤る**（1 始まり／0 始まりの取り違え、38 列目の数え方） | 誤った列に値が入り、ASP に誤ったデータが取り込まれる | 位置定数を 1 始まりで定義し、変換時に `-1` する箇所を VO 内の 1 か所に閉じる。§9 付録の 75 列と定数の一致をテストで検証（C-04〜C-08） |
| 2 | **ASP 側のレイアウト変更**（順応者のため一方的に変わりうる） | 出力が丸ごと使えなくなる | 列定数・チェック仕様を domain の 1 ファイルに集約し、変更時の影響範囲を局所化する。要件 §9 付録を SSOT として更新してから実装を直す |
| 3 | **スナップショットの失効**でボタンが押せない場面が増える | 利用者が「壊れた」と誤解する | 非活性時に `title` で理由を示し、`unavailable` 応答では「棚卸を選び直してください」と行動を示す（C-16） |
| 4 | **DD-02 の縮退スナップショット保存**が既存 CSV 出力の挙動を変える | 予期しない縮退データの出力 | `use_snapshot=True` 経路では `site_warning=True` のスナップショットを採用しない実装とし、既存 CSV 出力のテストで回帰を検証する |
| 5 | **摘要の改行置換に気づかない** | ASP 上の摘要が意図と異なる | 置換した行を必ず警告に含める（D-08・C-15）。警告文で「置き換えた」と明示する |
| 6 | **行数が想定を超える**（上限なし・D-10） | 応答が 5 秒を超える／貼り付けが重い | 一括生成のまま出す。実運用で件数を測定し、上限と分割運用を SD-2 の継続課題として決める |
| 7 | **cp932 換算のバイト数と ASP の実際の判定がずれる** | 警告の見落とし／過剰警告 | 表現できない文字は安全側（多め）に数える。実際の取り込みエラーが出た場合は要件 §9 付録の領域長定義から見直す |
| 8 | **資産枝番が空の行**をそのまま貼り付ける | ASP の必須入力違反で取り込みエラー | 警告に含め、業務フロー #6 で「貼り付け前に控える」ことを明記済み（要件 §3.3） |
| 9 | **`管理者コード`・`使用区分コード`・`メーカーコード` 部品が desknet's 側に無い**と `fields` 指定で W8000360 が出る | 一覧・突合が丸ごと取得できなくなる | 資産データ・棚卸データの双方に当該部品が存在することを利用者に確認済み（2026/08/26）。実装後に一覧表示で W8000360 が出ないことを確認する（機能仕様書 版 2.42 で `取得日付` に同種の事象があったため） |
| 10 | **判定と出力で参照する部品がずれる**（名称で判定・コードで出力。DD-08） | 差異があるのにコードが空で出る／差異が無いのに出る | コード側が空のときも差異があれば列を出力し、`M`・12 byte のチェック結果を警告に載せる。名称とコードの対応は desknet's 側のデータ整備に依存するため、警告で気づける形にする |

---

## 10. 要件トレーサビリティ

| 要件ID | 設計上の対応箇所 |
|---|---|
| REQ-F-001 | §6.3（ボタン配置） |
| REQ-F-002 | §4.2(f) `AmendmentRows.select_from` |
| REQ-F-003 | §4.2(a) `AspPasteLayout`、§4.4 対応表 |
| REQ-F-004 | §4.4 対応表、§4.2(e) `AspImportRow` |
| REQ-F-005 | §4.2(g) `AspImportRows.render_csv` |
| REQ-F-006 | §4.2(d) `NormalizedValue` / `AdjustedValue`、§3.1 DD-10 |
| REQ-F-007 | §4.2(b)(h)、§8.1 #5〜#9（#6-2・#6-3 を含む） |
| REQ-F-008 | §6.2（`empty`）、§8.1 #4 |
| REQ-F-009 | §3.1 DD-01・DD-05、§6.2（`unavailable`）、§6.3、§8.1 #1〜#3・#9 |
| REQ-NF-001 | §6.1（認可） |
| REQ-NF-002 | §5.1（テーブル新設なし） |
| REQ-NF-003 | §3.1 DD-01・DD-07、§5.3 データフロー、§6.2（4xx/5xx 経路の削除） |
| REQ-NF-004 | §3.1 DD-06 |
| REQ-NF-005 | §8.1 #13、§2（ASP へ書き込まない） |
| D-01〜D-07 | §4.2(a)、§4.4 対応表（**D-05 は D-13 により撤回**） |
| D-08 | §3.1 DD-03、§4.2(d)、§4.2(h) |
| D-09 | §3.1 DD-05、§6.3 |
| D-10 | §3.1 DD-06、§9 #6 |
| D-11 | §3.1 DD-08・DD-09、§4.2(a)(b)(c)(d)、§4.4 対応表、§7.1 #1〜#5 |
| D-12 | §4.2(a)（6 列目の位置定数を持たない）、§4.4 対応表 |
| D-13 | §3.1 DD-08・DD-09、§4.2(a)（`COLUMN_MANUFACTURER_CODE`）(b)(c)、§4.4 対応表、§7.1 #1〜#4、§9 #9 |
| D-14 | §3.1 DD-10、§4.2(b)（`truncatable`・`adjusted()`）(d) `AdjustedValue`、§4.2(h)（警告種別とブロック順）、§8.1 #6・#6-2・#6-3 |
| D-15 | §3.1 DD-11、§4.2(h)（警告種別・警告文の構成・ブロック順）、§8.1 #6 |
| C-01〜C-25 | test-design.md で網羅する（本書は設計の対応箇所のみを示す） |

---

## レビュー履歴

（design-review-l1 / design-review-l2-codex が追記する）

### 仕様変更 (2026/08/26 15:50)

**契機**: 利用者から ASP 取り込み用 CSV のマッピング表（75 行）が提供され、値を入れる列が **5 列 → 8 列** に拡張された。要件定義書（requirements.md）を先に改訂し（2026/08/26 15:09）、本設計書をそれに追随させた。

**変更内容**:

| # | 箇所 | 変更 |
|---|---|---|
| 1 | ヘッダー | 更新日 2026/08/26。対応文書にマッピング表を追記 |
| 2 | §3.1 | **DD-08**（判定は名称・出力はコード。`ASSET_FIELDS`/`INVENTORY_FIELDS` に 2 部品追加、`ReconcileRow` に 2 属性追加）と **DD-09**（追加 3 コードに専用 VO を設けない）を追加 |
| 3 | §4.2(a) | 位置定数に `COLUMN_MANAGER_CODE`(44) / `COLUMN_USAGE_CATEGORY_CODE`(59) / `COLUMN_OLD_ASSET_NUMBER`(65) を追加。空欄列 70 → 67。6 列目の位置定数を持たない旨（D-12）を明記 |
| 4 | §4.2(b) | `label` に 3 件、`max_bytes` に `12/12/12` を追加。「出力する 5 列分」→ 8 列分。追加 3 列は `M`・12 byte・`O` なしと明記 |
| 5 | §4.2(c) | 追加 3 コードは `DepartmentCode` と同一仕様のため専用型を設けない旨を追記（DD-09） |
| 6 | §4.2(d) | 整形規則の「前後の空白を除く」対象に 3 コードを追加 |
| 7 | §4.4 | 変化点 → 列の対応表を書き換え。型番→44 列目、使用区分→59 列目、旧資産番号→65 列目を追加。D-05 の「なし」はメーカー名のみに縮小。取得日付は常に空欄（D-12）。判定ラベルと出力属性が異なる点を注記 |
| 8 | §7.1 | `domain/repositories/ports.py`（#1）・`domain/value_objects/row_display.py`（#2）を追加し既存 10 行を #3〜#12 へ繰り下げ。`reconcile_cache.py` に 2 属性のシリアライズ追加を追記。テスト行の対応要件を C-01〜C-21 へ |
| 9 | §7.2 | セッション JSON に増えるキーを明記。desknet's 取得項目が 2 部品増える（API 呼び出し回数は不変）ことを追記 |
| 10 | §9 | リスク #9（W8000360）・#10（判定と出力で参照部品がずれる）を追加 |
| 11 | §10 | D-11・D-12 を追加。C-01〜C-17 → C-01〜C-21。D-05 の縮小を注記 |

**利用者確認済みの前提**: 棚卸データ app（408）に `管理者コード`・`使用区分コード` 部品が存在する（2026/08/26）。→ §9 #9 のリスクは解消。

**次のアクション**: test-design.md を本設計に追随させる（追加 3 列の出力・非出力・チェック違反、6 列目が常に空欄であることの TC 追加）。

### 仕様変更 (2026/08/26 16:38) — メーカーコードの追加

**契機**: 利用者より「メーカーコードを旧資産番号の前（抽出コード１８）に追加してください。desknet's にメーカーコードはあります」との指示。requirements.md を先に改訂し（2026/08/26 16:36・D-13）、本設計書をそれに追随させた。出力列は **8 列 → 9 列**、空欄列は 67 → **66 列**。

| # | 該当箇所 | 変更 |
|---|---------|------|
| 1 | ヘッダー | 対応文書のマッピング表に「メーカーコードの追加を含む」を補記 |
| 2 | §3.1 DD-08 | 追加部品に `メーカーコード`、`ReconcileRow` に `manufacturer_code` を追加。根拠を「44・59・64 列目とも `M`」に |
| 3 | §3.1 DD-09 | 専用 VO を設けないコードを 3 → **4**（`メーカーコード` V-315 を追加） |
| 4 | §4.2(a) | `COLUMN_MANUFACTURER_CODE`（64）を追加。空欄列 67 → 66、位置定数 8 → **9 列** |
| 5 | §4.2(b) | `label` に `メーカーコード`、`max_bytes` に `12` を追加。チェック仕様は 9 列分。`M`・12 byte の対象を 44・59・**64**・65 列目に |
| 6 | §4.2(c) | 専用型を設けない対象に `メーカーコード`（V-315）、値の取得元に `manufacturer_code` を追加 |
| 7 | §4.2(d) | 整形規則（前後空白の除去のみ）の対象に `メーカーコード` を追加 |
| 8 | §4.4 | 対応表の「メーカー名 / — / **なし** / 出力しない（D-05）」の行を「**メーカー名 / `manufacturer_code` / 64 列目 抽出コード１８（メーカーコード） / メーカー名に差異があるとき（D-13・DD-08）**」に**書き換え**。注記の対象列を 44・59・**64** に |
| 9 | §7.1 #1・#2・#3・#4 | `メーカーコード` / `manufacturer_code` を追加。asp_import.py は「4 列を差し込む」に |
| 10 | §7.2 | セッション JSON に増えるキーへ `manufacturer_code` を追加 |
| 11 | §9 リスク #9 | W8000360 の対象部品に `メーカーコード` を追加 |
| 12 | §10 | D-05 の記述を「D-13 により**撤回**」に。**D-13** の行を追加 |

**削除した記述**: §4.4 対応表の「| メーカー名 | — | **なし** | 出力しない（D-05）… |」1 行のみ（同じ位置に出力ありの行として置き換え）。他の箇所は追記または語句の置換で、既存の設計判断（DD-01〜DD-09）の削除は行っていない。

**利用者確認済みの前提**: 棚卸データ app（408）に `メーカーコード` 部品が存在する。

**次のアクション**: test-design.md → 機能仕様書 → ubiquitous_language.md を更新し、その後 tasks.md に仕様変更分のタスクを追記して Phase 5（実装）へ

### 仕様変更 (2026/08/27 10:55) — 半角への強制変換と領域長の切り捨て

**契機**: 実データでチェック仕様違反が 6 件発生した（5 件は 44 列目の全角長音記号 `ー`、1 件は 12 byte 超過）。
利用者より「強制的に半角に変換できる？」「超過した文字は切り捨てて」との指示。requirements.md を先に改訂し
（2026/08/27 10:53・**D-14**・C-23〜C-25）、本設計書をそれに追随させた。

| # | 該当箇所 | 変更 |
|---|---------|------|
| 1 | ヘッダー | 更新日 2026/08/27 |
| 2 | §3.1 | **DD-10**（値を ASP の書式へ寄せる責務を `AspFieldCheck.adjusted()` に持たせ、`violations()` は寄せたあとの値に対して呼ぶ）を追加 |
| 3 | §4.2(b) | 属性 `truncatable` を追加（資産番号・資産枝番のみ `False`）。`adjusted()` の適用順を明記 |
| 4 | §4.2(d) | `AdjustedValue` を追加。半角変換の 3 段（NFKC → ダッシュ・引用符の個別写像 → 長音記号／カナ語保護）と、cp932 境界を割らない切り捨て規則を定義 |
| 5 | §4.2(h) | 警告種別に `VALUE_TRUNCATED` / `HALF_WIDTH_CONVERTED` を追加。属性 `adjusted_value` を追加。警告文に「変換前 →「変換後」」のブロックを追加し、ブロック順を明記 |
| 6 | §8.1 | #6 の振る舞いを「寄せてから、なお適合しない場合のみ違反」に書き換え。#6-2（カナ語保護）・#6-3（キー列は切り捨てない）を追加 |
| 7 | §10 | REQ-F-006・REQ-F-007 の対応箇所を更新。**D-14** の行を追加。C-01〜C-21 → C-01〜C-25 |

**削除した記述**: なし（追加と語句の置換のみ。既存の設計判断 DD-01〜DD-09 に削除はない）。

**設計上の判断（利用者確認外）**: 切り捨ての対象から**資産番号（1 列目）・資産枝番（2 列目）を外した**。
この 2 列は ASP 上で更新対象の資産を特定するキーであり、切り詰めると *別の資産* を書き換えてしまうため。
該当時は従来どおり違反として警告する。利用者が「9 列すべて切り捨てる」を望む場合は `truncatable` を `True` にするだけで足りる。

**次のアクション**: test-design.md（TC-076〜083）→ 実装（`asp_import.py`）→ テスト → 機能仕様書（版 2.72）

### 仕様変更 (2026/08/27 14:35) — 半角変換の警告を出さない

**契機**: 利用者より「全角文字を半角変換はデフォルトのため、メッセージに出さなくてもよいです」との指示。
requirements.md を先に改訂し（2026/08/27 14:34・**D-15**・C-23）、本設計書をそれに追随させた。

| # | 該当箇所 | 変更 |
|---|---------|------|
| 1 | §3.1 | **DD-11**（`half_width_converted` は保持するが警告は組み立てない。判定と通知を分ける）を追加 |
| 2 | §4.2(h) | 警告種別 `HALF_WIDTH_CONVERTED` を**削除**。`adjusted_value` の対象を `VALUE_TRUNCATED` のみに。警告文の構成から半角変換ブロックを削除し、ブロック順を **違反 → 切り捨て → 改行置換 → 拠点マスタ縮退** の 4 種別に。半角変換と切り捨てが重なった場合の `value` の扱いを明記 |
| 3 | §8.1 | #6 の振る舞いから `HALF_WIDTH_CONVERTED` を削除 |
| 4 | §10 | **D-15** の行を追加 |

**削除した記述**: 警告種別 `HALF_WIDTH_CONVERTED`（§4.2(h)・§8.1）と、警告文の半角変換ブロック（§4.2(h)）。
`AdjustedValue.half_width_converted`（§4.2(d)）と `adjusted()` の 3 段変換規則（§4.2(d)）は**残す**。
DD-10 の定義であり、寄せた事実そのものは戻り値に保持し続けるため（DD-11）。

**次のアクション**: test-design.md（TC-101・TC-104 の改訂）→ 実装（`asp_import.py`）→ テスト → 機能仕様書（版 2.73）
