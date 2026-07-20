---
name: make-drawio-context-map
description: |
  DDD（ドメイン駆動設計）のコンテキストマップをdraw.io形式（.drawio）で作成する。
  サブドメイン分類、境界づけられたコンテキスト、コンテキスト間の関係パターン
  （順応者、腐敗防止層、顧客/供給者等）を色分けした図として出力する。
  ユーザーが「コンテキストマップを図にして」「コンテキストマップをdraw.ioで」
  「DDDの全体像を図にして」「サブドメインの関係図を作って」
  「.drawioでコンテキストマップを出力して」などと依頼したときに使用する。
  strategic_design.mdや壁打ち結果からコンテキストマップを生成する場合にも使用する。
argument-hint: "[戦略的設計書のファイルパス、またはコンテキスト情報]"
allowed-tools: Read, Write, Glob
---

# DDDコンテキストマップ draw.io作成スキル

DDD（ドメイン駆動設計）のコンテキストマップをdraw.io形式で生成する。

## 入力元の特定

$ARGUMENTS

- ファイルパスが指定されている場合は Read ツールで読み取る
- 引数が空の場合は、会話内の壁打ち結果やコンテキスト情報を入力元として使用する
- 情報が不足している場合は、ユーザーに「コンテキストマップに含めるコンテキストと関係を教えてください」と質問する

## コンテキストマップの構成要素

図に含めるべき要素を入力から抽出する:

1. **サブドメインとその分類**（コア / 支援 / 汎用）
2. **境界づけられたコンテキスト**（各サブドメイン内のコンテキスト）
3. **コンテキスト間の関係**（パターン名、上流/下流、技術的実現方法）
4. **業務フローの引き継ぎ**（システム連携ではない業務的な受け渡し）

## draw.io スタイルルール

### テキストの行間（最重要）

HTMLフォーマットテキストの `line-height` は必ず `1.2` を使用する。

```
必須: line-height:1.2
禁止: line-height:1.4 以上（行間が広すぎる）
```

### コンテンツテキストのスタイル

```xml
value="&lt;div style='text-align:left;font-size:11px;line-height:1.2'&gt;テキスト&lt;/div&gt;"
style="text;html=1;align=left;verticalAlign=top;spacingTop=4;spacingLeft=4;"
```

### 箇条書き

HTMLの `<ul>/<li>` は使わない。中黒（・）+ `&lt;br&gt;` で表現する。

### サブドメイン分類の色分け

| 分類 | 背景色(fillColor) | 枠線色(strokeColor) | 用途 |
|------|-------------------|--------------------|----|
| コアサブドメイン | `#f8cecc` | `#b85450` | 基幹システム等の外部システム |
| 支援サブドメイン（主） | `#dae8fc` | `#6c8ebf` | メインの支援ドメイン |
| 支援サブドメイン（副） | `#d5e8d4` | `#82b366` | 別の支援ドメイン（区別が必要な場合） |
| 汎用サブドメイン | `#e1d5e7` | `#9673a6` | 認証、通知等の外部サービス |

支援サブドメインが3つ以上ある場合は、黄系（`#fff2cc` / `#d6b656`）も使用する。

### 関係線のスタイル

| パターン | 線の色 | 線の太さ | 線種 |
|---------|--------|---------|------|
| 順応者（Conformist） | `#b85450`（赤） | 2 | 実線 |
| 腐敗防止層（ACL） | `#82b366`（緑） | 2 | 実線 |
| 顧客/供給者（Customer-Supplier） | `#6c8ebf`（青） | 2 | 実線 |
| 共有カーネル（Shared Kernel） | `#d6b656`（黄） | 2 | 実線 |
| 保留・未確認 | `#999999`（灰） | 1 | 破線 `dashPattern=8 4` |
| 業務フローの引き継ぎ | `#666666`（灰） | 1 | 点線 `dashPattern=5 5` |

### グループ化（サブドメインの囲み）

```xml
<mxCell id="group-x"
  value="サブドメイン名"
  style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=12;fontStyle=1;verticalAlign=top;spacingTop=5;dashed=1;dashPattern=5 5;"
  vertex="1" parent="1">
  <mxGeometry x="40" y="80" width="300" height="280" as="geometry" />
</mxCell>
```

### コンテキストの矩形

```xml
<mxCell id="ctx-x"
  value="&lt;b&gt;コンテキスト名&lt;/b&gt;&lt;br&gt;&lt;font style='font-size:10px'&gt;説明テキスト&lt;br&gt;補足情報&lt;/font&gt;"
  style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=12;"
  vertex="1" parent="1">
  <mxGeometry x="60" y="120" width="200" height="80" as="geometry" />
</mxCell>
```

### 構想段階のコンテキスト

まだ実装されていないコンテキストは破線枠で表現する:

```xml
style="...;strokeDasharray=3 3;"
```

### 関係線

```xml
<!-- 実線（確定した関係） -->
<mxCell id="rel-x"
  value="パターン名: 技術的実現方法"
  style="edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;fontSize=10;fontColor=#b85450;strokeColor=#b85450;strokeWidth=2;"
  edge="1" parent="1" source="source-id" target="target-id">
  <mxGeometry relative="1" as="geometry" />
</mxCell>

<!-- 中間点を使ったルーティング -->
<mxCell id="rel-x" ... edge="1" parent="1" source="a" target="b">
  <mxGeometry relative="1" as="geometry">
    <Array as="points">
      <mxPoint x="300" y="200" />
    </Array>
  </mxGeometry>
</mxCell>
```

## レイアウトの原則

### 配置の基本方針

```
上部: コアサブドメイン（外部システム）+ 汎用サブドメイン
下部: 支援サブドメイン（自分たちが作るもの）
```

データの流れは上から下（外部→内部）を基本とする。

### サイズの目安

| 要素 | 幅 | 高さ |
|------|-----|------|
| コンテキスト矩形 | 180〜220 | 70〜120 |
| グループ囲み | コンテキスト数に応じて | コンテキスト数に応じて |
| セル間の間隔 | 最低 20px | 最低 20px |
| グループ内余白 | 最低 30px | 最低 30px |

### ページサイズ

| コンテキスト数 | pageWidth | pageHeight |
|-------------|-----------|------------|
| 5個以下 | 1200 | 800 |
| 6〜12個 | 1600 | 900 |
| 13個以上 | 1600 | 1200 |

## 凡例（必須）

図の右下に凡例を配置する。以下の情報を含める:

1. 色分けの意味（サブドメイン分類）
2. 線種の意味（関係パターン）

## 基本のXML構造

```xml
<mxfile host="app.diagrams.net" modified="日付" agent="Claude" version="24.0.0" type="device">
  <diagram id="context-map" name="コンテキストマップ">
    <mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1600" pageHeight="1200" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />

        <!-- タイトル -->
        <!-- サブドメイングループ + コンテキスト矩形 -->
        <!-- 関係線 -->
        <!-- 凡例 -->

      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

## HTMLエスケープ

draw.ioのXML内でHTMLを埋め込む場合:

| 文字 | エスケープ |
|------|----------|
| `<` | `&lt;` |
| `>` | `&gt;` |
| `&` | `&amp;` |

## チェックリスト

生成後、以下を確認すること:

- [ ] `<mxfile>` / `</mxfile>` で囲まれているか
- [ ] 全てのテキストで `line-height:1.2` が指定されているか
- [ ] HTMLタグが正しくエスケープされているか
- [ ] セルIDに重複がないか
- [ ] 矢印の source / target が正しいセルIDを参照しているか
- [ ] サブドメインの分類ごとに色分けされているか
- [ ] 関係パターンごとに線種・色が区別されているか
- [ ] 凡例が含まれているか
- [ ] 構想段階のコンテキストは破線枠になっているか

## 出力手順

1. 入力からコンテキスト一覧と関係一覧を抽出する
2. サブドメインごとにグルーピングする
3. レイアウトを設計する（座標、サイズ）
4. XMLを生成する
5. .drawio ファイルとして Write ツールで出力する
6. ユーザーに出力先を報告する
