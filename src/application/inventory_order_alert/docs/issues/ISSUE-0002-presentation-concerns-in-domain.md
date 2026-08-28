---
文書ID: ISSUE-IOA-IMP-2026-002
種別: 改善
ステータス: Triaged
優先度: 低
起票者: Hashizume
起票日: 2026/08/25 13:55
更新日: 2026/08/25 13:55
クローズ日:
対象コンテキスト: inventory_order_alert（横断課題。主担当として本アプリに起票）
対象機能: 一覧表示・CSV 出力の表示整形
対応文書: なし
外部リンク:
---

# 表示の関心事が `domain/` に混入している

## 現状の課題

2026/08/25 の DDD 設計レビューで検出した指摘 **D-6** を扱う。

`domain/value_objects/` に、業務ルールではなく **表示の都合** を持つモジュールが並んでいる。

| コンテキスト | 該当モジュール |
|---|---|
| 在庫発注アラート | `format_display.py` / `row_display.py` / `table_display.py` / `user_display.py` / `export_csv.py` |
| 資産棚卸結果 | `plate_display.py` / `row_display.py` / `table_display.py` / `sort_headers.py` / `csv_export.py` / `row_color_rules.py` |
| 出荷トレンド一覧 | `table_display.py` / `export_csv.py` |
| 検収書比較 | `comparison_display.py` / `settings_labels.py` |
| ポータル基盤 | `database_display.py` / `user_management_display.py` |

- 列見出し・桁区切り・色分けクラス名・CSV の列順といった **画面／帳票の都合** が
  ドメイン層に置かれているため、「業務ルールをフレームワークの都合から隔離する」
  という戦略的判断（`docs/strategic_design.md` §5）が実質的に崩れている。
- 表示仕様の変更が `domain/` の変更として現れるため、ドメインの変更履歴が読みにくい。

### 併せて扱う課題

`application/portal/domain/value_objects/constants.py` が `RECEIPT_COMPARISON_PATH` 等、
**コンテキスト A（検収書比較）固有の知識** を持っている。
ポータル基盤（汎用サブドメイン）がコアサブドメインの詳細を知っている状態であり、
同種の「層／コンテキストの取り違え」として本 Issue のスコープに含める。

## 改善提案

- 表示整形のモジュールを `interfaces/` 配下（表示専用のプレゼンター）へ移す。
  ただし **判定結果のラベル**（アラート区分の名称など、ユビキタス言語に載る語）は
  ドメインに残す。両者の線引きを移設前に定義する。
- `portal/domain/value_objects/constants.py` のコンテキスト A 依存分は、
  検収書比較側が公開する定数を参照する形へ変える（またはメニュー定義へ寄せる）。

## 期待効果

- `domain/` の変更が業務ルールの変更と一対一になり、レビュー対象が絞れる。
- 表示仕様の変更が、ドメインのテストを壊さずに済む。

## 代替案

- **現状維持**: 表示整形が Django 非依存で書かれている限り実害は小さい。
  ただし `domain/` が肥大し、コアサブドメインの判定ロジックが埋もれる。
- **`interfaces/` ではなく `shared/` へ移す**: 汎用の整形（桁区切り等）だけを共有カーネルへ寄せる。
  一覧の絞り込み・並び替え・表示整形の汎用部分は S-1 対応で既に
  `application/shared/domain/value_objects/` へ移設済みであり、その延長として検討できる。

---

## 対策案 (Plan)

- 対策区分: **本格**
- 移設対象が十数本、5 コンテキストに跨るため、Issue 内では完結させない。
- 着手時は「ドメインに残すラベル」と「表示へ移す整形」の線引きを先に定義する。
  線引きが決まれば移設自体は機械的なので、コンテキスト単位で分割して進める。
- 優先度は低。[ISSUE-IOA-IMP-2026-001](ISSUE-0001-dict-centric-domain-model.md) の
  ドメインモデル整理が先行しないと、移設対象が再度動く。

## 実施内容 (Do)

- 変更概要: 未着手
- 対象ファイル:
- コミット:

## 検証結果 (Check)

- 期待効果の達成: 未
- テスト結果:
- レビュー結果:

## 振り返り・標準化 (Act)

- 標準化した内容:
- 反映先:
- 派生Issue: なし
