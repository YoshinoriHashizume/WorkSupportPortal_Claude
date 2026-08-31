# inventory_order_alert Issue台帳

このディレクトリは在庫発注アラート コンテキストの不具合・改善Issueを管理する。

- 保存規約: `ISSUE-{連番4桁}-{kebab-title}.md`
- 文書ID規約: `ISSUE-{APP}-{BUG|IMP}-{年}-{連番3桁}`
- 詳細な運用は manage-issue スキルを参照

## 対応中・未対応

| ID | 種別 | タイトル | 優先度 | ステータス | 対応文書 | 起票日 |
|----|------|----------|--------|-----------|----------|--------|
| [ISSUE-0001](ISSUE-0001-dict-centric-domain-model.md) | 改善 | ドメインモデルが `dict[str, object]` 中心で、エンティティが存在しない（DDDレビュー D-1／D-2） | 中 | Triaged | なし | 2026/08/25 |
| [ISSUE-0002](ISSUE-0002-presentation-concerns-in-domain.md) | 改善 | 表示の関心事が `domain/` に混入している（DDDレビュー D-6 ＋ portal 定数のコンテキストA依存） | 低 | Triaged | なし | 2026/08/25 |
| [ISSUE-0003](ISSUE-0003-flow-quadrant-detection-regression-unverified.md) | 改善 | 流動区分への置換で供給リスクの検知力が落ちていないかが未検証（L3レビュー L3F-3） | 中 | Triaged | なし | 2026/08/31 |
| [ISSUE-0004](ISSUE-0004-requirements-missing-exception-cases.md) | 改善 | 要件定義書の異常系に同時実行と集計エラーの記載がない（L3レビュー L3F-4 / L3F-5） | 低 | Triaged | なし | 2026/08/31 |
| [ISSUE-0005](ISSUE-0005-no-payload-size-requirement.md) | 改善 | 配信データ量の非機能要件がなく、見積り誤りを検出できなかった（L3レビュー L3F-6） | 中 | Triaged | なし | 2026/08/31 |
| [ISSUE-0006](ISSUE-0006-large-replacement-release-strategy-unstated.md) | 改善 | 大規模な置換要件で段階リリースの可否が要件段階で示されていない（L3レビュー L3F-7） | 低 | Triaged | なし | 2026/08/31 |

## クローズ済み

（まだありません）
