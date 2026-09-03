# 判断ログ: 出荷推移グラフ（自律実行分）

作成日: 2026/09/01
対応: [requirements.md](./requirements.md) / [design.md](./design.md) / [test-design.md](./test-design.md) / [tasks.md](./tasks.md)

ユーザーから「今日は帰るので、要件定義から実装まで一気にやってみて。確認点は自分で保管して明日確認できるように」との指示を受け、
対話による承認を都度得ずに SDD の各フェーズを自己判断で進めた。**明日、以下を上から順に確認してください。**
いずれも「間違っている」というより「複数の妥当な選択肢のうち1つを選んだ」判断であり、変更が必要ならすぐ直せる想定です。

## 実行サマリー

- **ブランチ**: `feature/ioa-shipment-history-chart`（`develop` から分岐し、実装完了後に `develop` へマージ済み。**`origin` への push は未実施**）
- **成果物**: requirements.md / design.md / test-design.md / tasks.md（本ディレクトリ）、実装コード一式（下記）
- **テスト**: `pytest` リポジトリ全体 1656件 Green（うち本機能の新規テスト約40件）。`manage.py check` 問題なし。マイグレーション不要（`makemigrations --check` で差分なし）
- **変更ファイル**（新規）: `domain/value_objects/shipment_trend.py`、`tests/test_shipment_trend_vo.py`、`tests/test_shipment_trend_query.py`、`tests/test_shipment_trend_edge_cases.py`
- **変更ファイル**（既存改修）: `infrastructure/oracle/summary_queries.py`、`templates/inventory_order_alert/list.html`、`static/js/inventory-order-alert-list-client.js`、`static/js/inventory-order-alert-list.js`、`static/css/app.css`、`docs/在庫発注アラート_機能仕様書.md`、`docs/ubiquitous_language.md`、および関連テストファイル数点
- **Oracle への影響**: **なし**。新規クエリを追加せず、既存の `fetch_all_shipments()` の取得結果を月次に束ね直しただけ

### 追記（2026/09/03、ユーザー指示「入荷も含めて」への対応）

- **ブランチ**: `feature/ioa-shipment-history-chart-incoming`（`develop` から分岐。tasks.md ステージ6 タスク22〜33 実施）
- **テスト**: `pytest` リポジトリ全体 1667件 Green（新規テスト11件追加）。`manage.py check` 問題なし。マイグレーション不要
- **変更ファイル**（新規）: `tests/test_incoming_trend_query.py`
- **変更ファイル**（既存改修）: `infrastructure/oracle/summary_queries.py`（`fetch_incoming_receipts()` 新設、`build_summary_rows()` に `incoming_trend` 付与）、`static/js/inventory-order-alert-list-client.js`（`getIncomingTrend` 追加）、`static/js/inventory-order-alert-list.js`（`renderShipmentTrendChart` を2系列描画に拡張）、`templates/inventory_order_alert/list.html`（見出しを「入出荷推移」に変更）、`static/css/app.css`（入荷系列・凡例のスタイル追加）、`docs/在庫発注アラート_機能仕様書.md`（§4.1.6・改訂履歴4.9）、`docs/ubiquitous_language.md`（V-217追加）
- **Oracle への影響**: **あり（新規クエリ1件）**。`fetch_incoming_receipts()` を取込ごとに1回、直近24か月に絞って発行（詳細は下記「項目3」参照）
- **push**: 本追記分も develop へのローカルコミットのみ。**origin への push は未実施**（本セッションの一貫方針どおり、明示指示待ち）

### 追記（2026/09/03、ユーザー指示「累積でグラフを見たい」への対応）

自律実行分（項目1〜5）とは異なり、本追記はユーザーと対話しながら実施した。負値の表示方針（マイナスのままか0でクランプするか）は AskUserQuestion で確認済み（「マイナスのまま表示する」を選択）。それ以外の実装判断は下記のとおり。

- **算出方式**: 現在の在庫数（SLIMS/MARI）を起点に、入出荷推移から「当月末推定 = 翌月末推定 + 翌月出荷 − 翌月入荷」で過去へ逆算する**参考値**（V-218 推定在庫推移）。実測の在庫履歴ではない旨をユビキタス言語集・要件定義書・機能仕様書に明記した。
- **算出場所の判断**: サーバー側（domain層）ではなく**クライアント（JS）側**で算出する設計にした。出荷推移・入荷推移・SLIMS/MARI在庫数はいずれも既にクライアントへ配信済みのデータであり、既存の `sortValue` 等の派生値計算がクライアント側で行われている既存パターンとも整合するため。この判断により、**新規 Oracle 問い合わせ・配信ペイロード増加ゼロ**で実現できた。
- **色の割当て（未確認）**: SLIMS起点=インディゴ系、MARI起点=緑系とした（出荷=青・入荷=橙と混同しないよう別系統の色にした）。デザイン上の好みで変更可能。
- **数値計算の検証方法**: JS用のテストランナーがないため、自動テストはソース文字列アサーションにとどまる。数値計算の正しさは Node で一時スクリプトを実行し手動検証した（tasks.md ステージ7実行レポート参照）。恒久的な自動テストとしては残っていない点は今後の課題として認識しておく。
- **ブランチ**: `develop` 上で直接実施（ステージ7、tasks.md タスク34〜42）。`origin` への push は未実施（明示指示待ち）
- **テスト**: `pytest` リポジトリ全体 1673件 Green。`manage.py check` 問題なし。マイグレーション不要
- **変更ファイル**（既存改修）: `static/js/inventory-order-alert-list.js`（`parseAnchorQty`・`buildAnchoredStockTrend`・`renderAnchoredStockChart` を新設）、`templates/inventory_order_alert/list.html`（「推定在庫推移（参考値）」区分を追加）、`static/css/app.css`（新系列・ゼロ基準線のスタイル追加）、`docs/在庫発注アラート_機能仕様書.md`（§4.1.6・改訂履歴4.10）、`docs/ubiquitous_language.md`（V-218追加）、`tests/test_inventory_order_alert_list_js.py`（新規テスト6件）

### 追記（2026/09/03、ユーザー指示「入出荷のグラフはいらない」への対応・ステージ8）

ユーザーから「左に台数と入出荷のグラフはいらない」との指示を受けた。曖昧だったため AskUserQuestion で
「詳細ダイアログの『入出荷推移』区分（出荷=青・入荷=橙の2系列グラフ）を区分ごと削除する、という理解であっていますか？」
と確認し、「はい、入出荷推移区分を丸ごと削除」の回答を得てから着手した。

- **撤去した範囲の判断**: 出荷推移（V-216）・入荷推移（V-217）の**算出処理**（Oracle集計・`shipment_trend`/`incoming_trend`の付与）は撤去せず維持した。これらは推定在庫推移（V-218、直前の追記で実装済み）の算出材料として必須のため。撤去したのは**専用グラフとして描画・表示していた部分のみ**（`renderShipmentTrendChart()` 関数本体、`ioa-detail-shipment-trend-section` テンプレート区分、対応CSS）。
- **命名債務の解消**: 直前の追記（項目3）で「許容した」としていた命名債務のうち、CSS/JSクラス名（`.ioa-shipment-trend-svg` 等）は `renderAnchoredStockChart()` が流用していたため、削除ではなく `.ioa-anchored-stock-trend-*` へ付け替えた。一方 `build_monthly_shipment_trend()` / `group_shipments_by_pair()`（Python側、出荷・入荷共通で使う集計関数）は表示撤去と無関係のため変更していない（引き続き design.md R-6 の債務として残る）。
- **仕様書の記述方針**: CLAUDE.mdの「仕様が正しい。コードを修正すること」「削除対象を明示してから実行する」の原則に従い、requirements.md / design.md / test-design.md / 機能仕様書 / ubiquitous_language.md のいずれも元の記述を削除せず、「［撤去済み］」「（削除）」等の注記を付けて履歴を残した。
- **ブランチ**: `develop` 上で直接実施（ステージ8、tasks.md タスク43〜49）。`origin` への push は未実施（明示指示待ち）
- **テスト**: `pytest` アプリ内 656件・リポジトリ全体 1671件 Green。`manage.py check` 問題なし。マイグレーション不要
- **変更ファイル**（既存改修）: `templates/inventory_order_alert/list.html`（「入出荷推移」区分を削除）、`static/js/inventory-order-alert-list.js`（`renderShipmentTrendChart()` 削除、`renderAnchoredStockChart()` のクラス参照を付け替え）、`static/css/app.css`（`.ioa-shipment-trend-*` 削除、`.ioa-anchored-stock-trend-*` 追加）、`docs/在庫発注アラート_機能仕様書.md`（§4.1.6・改訂履歴4.11）、`docs/ubiquitous_language.md`（V-216/V-217定義改訂）、`tests/test_inventory_order_alert_views.py`・`tests/test_inventory_order_alert_list_js.py`（撤去確認テストへ置き換え）

### 追記（2026/09/03、実画面フィードバック3件への対応・ステージ9）

推定在庫推移グラフを実際にブラウザで確認したユーザーから3件の指摘を受けた。事前に変更対象ファイル・影響範囲を提示し承認を得てから着手した。

1. **「点線は何？」**: ゼロ基準線（推定在庫0の目印）である旨を回答。コード変更なし。
2. **「右の年月がかけている」**: 月ラベルが `text-anchor: middle` 一律だったため、末尾ラベルがSVG右端からはみ出して見切れていた。先頭は`start`、末尾は`end`にtext-anchorを個別設定して解消。
3. **「左にメモリが欲しい」**: Y軸の数量目盛りが存在しなかったため、最大値・最小値（0がその間にあれば0も）をカンマ区切りで表示するように追加。表示スペース確保のため`paddingLeft`を32→40に拡張。

- **ブランチ**: `develop` 上で直接実施（ステージ9、tasks.md タスク50〜55）。`origin` への push は未実施（明示指示待ち）
- **テスト**: `pytest` アプリ内 658件・リポジトリ全体 1673件 Green。`manage.py check` 問題なし。マイグレーション不要
- **変更ファイル**（既存改修）: `static/js/inventory-order-alert-list.js`（`renderAnchoredStockChart()` の月ラベルtext-anchor調整・Y軸目盛り追加）、`static/css/app.css`（`.ioa-anchored-stock-trend-y-axis-label` 追加）、`docs/spec/04_shipment-history-chart/design.md`（§6.6追記）、`tests/test_inventory_order_alert_list_js.py`（新規テスト2件: TC-SHC-X-016, X-017）
- Oracle・配信ペイロードへの影響: なし（表示のみの変更）

### 追記（2026/09/03、「まだ見切れてる」への再対応・ステージ10）

ステージ9で月ラベルの見切れを修正したはずだったが、ユーザーから「まだ見切れてる」と再指摘を受けた。あわせてExcelグラフの画像を提示され、Y軸目盛りを等間隔の複数目盛り線にしたい旨が伝わった。

- **見切れが直っていなかった根本原因**: `label.setAttribute("text-anchor", "end")` で設定していたが、SVGではCSSクラス（`.ioa-anchored-stock-trend-axis-label { text-anchor: middle; }`）の方が優先度が高く、setAttributeでの上書きが無視されていた。**`label.style.textAnchor = "end"`（インラインstyle）に変更**して解消した。
- **Y軸目盛りの方式**: AskUserQuestionで「最大値・最小値のみ（現状維持）」と「等間隔の複数目盛り線（推奨）」を提示し、後者を選択いただいた。`GRID_LINE_COUNT = 4`（値域を4分割=5本の目盛り線）で実装し、Excelのデフォルトに近い見た目にした。
- **ゼロ基準線の扱い**: グリッド線導入に伴い、ゼロ基準線（破線）は「マイナス域が実際にある場合のみ」描画するよう条件を追加した。全点0以上の行では最下段のグリッド線が0を兼ねるため、重複を避けた。
- **ブランチ**: `develop` 上で直接実施（ステージ10、tasks.md タスク56〜61）。`origin` への push は未実施（明示指示待ち）
- **テスト**: `pytest` アプリ内 659件・リポジトリ全体 1674件 Green。`manage.py check` 問題なし。マイグレーション不要
- **変更ファイル**（既存改修）: `static/js/inventory-order-alert-list.js`（text-anchorのstyle上書き化、等間隔グリッド線描画への置き換え）、`static/css/app.css`（`.ioa-anchored-stock-trend-grid-line` 追加）、`docs/spec/04_shipment-history-chart/design.md`（§6.6再改訂）、`tests/test_inventory_order_alert_list_js.py`（TC-SHC-X-016改訂、TC-SHC-X-018新設）
- **教訓**: SVG手組み実装で `setAttribute` によるpresentation attributeの上書きはCSSクラス指定に負けることがある。確実に上書きしたい場合は `element.style.xxx`（インラインstyle）を使うこと。

---

## 要確認・要判断（優先度順）

### 1. 「在庫変動」を「出荷推移」に読み替えたこと 【最重要】

**元の依頼は「在庫変動のグラフ」だったが、実装したのは「出荷数量の月次推移グラフ」。**

- 理由: SLIMS 在庫数は取込のたびに洗い替えられ、MARI 在庫数も現在値のみで、在庫数そのものの時系列データが存在しない（既存コードの設計上の制約）。
- 直前の会話でユーザー自身が「出荷回数のデータでできない？」と提案し、それに対して私が「できる。出荷推移の方が判定根拠を可視化できる分むしろ良い」と回答し、実装方針として合意していた。
- **確認したいこと**: この読み替えで意図通りか。もし「それでも在庫数の推移が見たい」ということであれば、別途「取込ごとの集計スナップショットから在庫数を拾う」方式（不定期・まばらな点になる）か、「新しく時系列テーブルを作り今後真面目に積む」方式を改めて検討する。

### 2. 対象期間を「直近24か月」に固定したこと 【実測値により重要度が上がった】

- 判定期間（V-211）は死蔵判定軸で最大 **5年（60か月）** まである。24か月では、5年判定で「在庫死蔵品」になった行の判定根拠を、グラフの表示期間内で確認できない場合がある。
- 24か月にした理由: グラフの点数・配信データ量を抑えるための暫定値。明確な根拠に基づく値ではない。
- **実測結果（タスク17）**: 24か月ぶんの出荷推移で **1行あたり配信データ量が +794バイト**（見積りの約500バイトから乖離）。既存の1行あたりデータ量（実測約4,000バイト）に対し約2割増。**60か月に伸ばすと単純比例で約2,000バイト/行**になる見込みで、5,000行規模の一覧では合計 約10MBの増加になる。
- **確認したいこと**: 24か月のままでよいか（判定根拠を見せきれない可能性を許容する）、60か月まで伸ばすか（配信量が明確に増える）、あるいは判定軸に応じて可変にするか。

### 3. 入荷実績（入荷推移）をグラフに含めなかったこと 【解決済み・2026/09/03】

- ~~流動区分の判定は「入荷の有無」と「出荷の有無」の両方で決まるが、今回のグラフは**出荷のみ**を表示する。~~
- **2026/09/03、ユーザー指示「入荷も含めて」により対応済み**。入荷推移（V-217）を第2系列として追加し、区分見出しも「出荷推移」から「**入出荷推移**」に変更した（design.md §3.3・§4.3・§6.1〜§6.5、tasks.md ステージ6、機能仕様書 改訂履歴 4.9）。
- 追加時に生じた新規判断（対話で確認済みではなく、design.md 作成時の自己判断のため、念のため記録）:
  - **数量フィールドの選択**: `T_PAST_INSPC_ACPT` には `ACPT_QTY`（受入数量）と `INSPC_ACPT_QTY`（検収数量）の2つの数量列がある。「検収済み＝正式に受け入れた数量」がより意味のある指標と判断し **`INSPC_ACPT_QTY`** を採用（ubiquitous_language.md V-217 に明記）。
  - **突合キーの違い**: 出荷推移は「得意先×得意先品番」で突合するが、入荷推移は「BOM階層1構成子×仕入先」で突合する（既存の最終入荷日解決ロジックと同じ軸）。突合先が解決できない行（BOM未解決等）は入荷推移が全月0になる。
  - **新規 Oracle クエリの追加**: 出荷推移はゼロ追加クエリで実現できたが、入荷推移は個々の検収明細（月次集計に必要な数量つき）を取る手段が既存になく、`fetch_incoming_receipts()` を新設した。既存の `fetch_last_incoming_by_item_vend()`（`MAX(ACPT_DATE)` の集約のみ、範囲指定なし）を安易に真似ず、**`WHERE ACPT_DATE >= :window_start` で直近24か月に絞った**（REQ-SHC-NF-008）。取込ごとに1回のみ発行。
  - **命名債務（意図的に許容）**: `build_monthly_shipment_trend()`（domain関数）と `group_shipments_by_pair()`（infrastructure関数）を、名前を変えずに入荷推移でも汎用再利用した。「出荷」という名前が残ったまま入荷にも使う点は将来の可読性を損なうが、既にテスト済み・コミット済みのコードへの改名リスクとレビュー範囲拡大を避けるため許容した（design.md R-6）。同様に JS の `renderShipmentTrendChart` 関数名、CSS/HTML の `ioa-detail-shipment-trend-*` クラス名も維持した。
  - **配信ペイロード増分**: 入荷推移単独 +793バイト/行、出荷+入荷合計 +1,587バイト/行（実測、design.md §6.2）。項目2（対象期間24か月固定）の判断により重要度が増す（60か月化すると合計で約4,000バイト/行になる見込み）。

### 4. グラフの描画方式（自前 SVG、外部ライブラリ不使用）

- 出荷トレンドアプリ（`shipment_trend`）が既に自前 SVG 描画を採用しているため、視覚的な一貫性のためこれに合わせた。ただしコンテキスト境界のルール上、コードは共有せず独自実装した。
- 大きな懸念はないが、デザインの好み次第で変えられる点として記載。

### 5. 未push（develop へのコミットのみ）

- 実装後、develop ブランチへローカルコミットまでは行うが、**origin への push・master への反映は行わない**（このセッションの一貫した方針：pushは都度「push して」の明示指示を受けてから実行）。
- **確認したいこと**: 内容を確認後、「push して」と言っていただければ develop へ反映する。

---

## 自己承認したレビュー内容（参考・変更不要なら読み飛ばして良い）

- 要件定義書 L1/L2/L3 相当の自己レビュー: 用語（V-216 出荷推移を新設）・スコープ・異常系（出荷実績なし、既存スナップショット互換）を確認。NG 相当の指摘なし。
- 設計書レビュー: Clean Architecture のレイヤー配置、コンテキスト境界（`shipment_trend` への直接importをしない）を確認。
- 詳細は各文書末尾の「レビュー履歴」セクションを参照。
