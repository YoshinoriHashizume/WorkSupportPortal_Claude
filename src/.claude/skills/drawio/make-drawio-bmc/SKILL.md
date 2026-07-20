---
name: make-drawio-bmc
description: |
  ビジネスモデルキャンバス（BMC）をdraw.io形式（.drawio）で作成する。
  9つの基本要素（価値の提案、顧客セグメント、チャネル、顧客との関係、
  収益の流れ、主要なリソース、主要な活動、キーパートナー、コスト構造）を
  標準的なBMCレイアウトで配置した図を出力する。
  ユーザーが「ビジネスモデルキャンバスを図にして」「BMCをdraw.ioで」
  「ビジネスモデルキャンバスを.drawioで出力して」「BMCを作って」
  などと依頼したときに使用する。
argument-hint: "[BMC情報のファイルパス、またはBMC情報]"
allowed-tools: Read, Write, Glob
---

# ビジネスモデルキャンバス draw.io作成スキル

ビジネスモデルキャンバス（BMC）をdraw.io形式で生成する。

## 入力元の特定

$ARGUMENTS

- ファイルパスが指定されている場合は Read ツールで読み取る
- 引数が空の場合は、会話内のBMC情報を入力元として使用する
- 情報が不足している場合は、9つの要素について順にユーザーに質問する

## BMCの9つの要素

| # | 要素 | 位置 | 説明 |
|---|------|------|------|
| 1 | 価値の提案 | 中央 | 顧客にどんな価値を提供するか |
| 2 | 顧客セグメント | 右端 | 誰に価値を届けるか |
| 3 | 顧客との関係 | 右上 | 顧客とどのような関係を築くか |
| 4 | チャネル | 右下 | どうやって価値を届けるか |
| 5 | 主要な活動 | 左上 | 価値を生み出すために何をするか |
| 6 | 主要なリソース | 左下 | 価値を生み出すために何が必要か |
| 7 | キーパートナー | 左端 | 誰と協力するか |
| 8 | コスト構造 | 下段左 | 何にコストがかかるか |
| 9 | 収益の流れ | 下段右 | どうやって収益を得るか |

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

```
良い例: ・項目1&lt;br&gt;・項目2&lt;br&gt;・項目3
悪い例: &lt;ul&gt;&lt;li&gt;項目1&lt;/li&gt;&lt;/ul&gt;
```

### HTMLエスケープ

| 文字 | エスケープ |
|------|----------|
| `<` | `&lt;` |
| `>` | `&gt;` |
| `&` | `&amp;` |

## BMCレイアウト仕様

### 全体構成

```
+---------------+---------------+---------------+---------------+---------------+
|               |               |               |               |               |
| ⑦キー        | ⑤主要な活動   |               | ③顧客との関係 | ②顧客        |
|  パートナー   |               | ①価値の提案    |               |  セグメント   |
|               +---------------+  （黄色強調）  +---------------+               |
|               |               |               |               |               |
|               | ⑥主要な       |               | ④チャネル     |               |
|               |  リソース     |               |               |               |
+---------------+---------------+---------------+---------------+---------------+
|                                               |                               |
|            ⑧コスト構造                         |         ⑨収益の流れ           |
|                                               |                               |
+-----------------------------------------------+-------------------------------+
```

### 座標とサイズ

| 要素 | x | y | width | height |
|------|---|---|-------|--------|
| ⑦ キーパートナー（枠） | 40 | 80 | 230 | 340 |
| ⑤ 主要な活動（枠） | 270 | 80 | 250 | 170 |
| ⑥ 主要なリソース（枠） | 270 | 250 | 250 | 170 |
| ① 価値の提案（枠） | 520 | 80 | 260 | 340 |
| ③ 顧客との関係（枠） | 780 | 80 | 250 | 170 |
| ④ チャネル（枠） | 780 | 250 | 250 | 170 |
| ② 顧客セグメント（枠） | 1030 | 80 | 230 | 340 |
| ⑧ コスト構造（枠） | 40 | 420 | 610 | 200 |
| ⑨ 収益の流れ（枠） | 650 | 420 | 610 | 200 |

各ラベル（見出し行）は枠と同じ x, y, width で height=30。
各コンテンツテキストは枠の x+5, y+35 に配置。

### 色の使い方

| 要素 | 枠の背景色 | ラベルの背景色 |
|------|-----------|-------------|
| ① 価値の提案（枠） | `#FFF9E6` | `#FFE599` |
| ① 価値の提案（ラベル） | — | `fillColor=#FFE599;strokeColor=#333333` |
| その他の要素（枠） | `#FFFFFF` | — |
| その他の要素（ラベル） | — | `fillColor=#f0f0f0;strokeColor=#333333` |

### ボックス（枠）のスタイル

```xml
<mxCell id="box-x" value=""
  style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#333333;strokeWidth=2;"
  vertex="1" parent="1">
  <mxGeometry x="40" y="80" width="230" height="340" as="geometry" />
</mxCell>
```

### ラベル（見出し行）のスタイル

```xml
<mxCell id="label-x" value="⑦ キーパートナー"
  style="text;html=1;fontSize=13;fontStyle=1;align=left;verticalAlign=top;fillColor=#f0f0f0;strokeColor=#333333;strokeWidth=1;spacingLeft=8;spacingTop=4;"
  vertex="1" parent="1">
  <mxGeometry x="40" y="80" width="230" height="30" as="geometry" />
</mxCell>
```

### コンテンツテキストのスタイル

```xml
<mxCell id="content-x"
  value="&lt;div style='text-align:left;font-size:11px;line-height:1.2'&gt;・&lt;b&gt;項目1&lt;/b&gt;&lt;br&gt;・&lt;b&gt;項目2&lt;/b&gt;&lt;br&gt;・項目3&lt;/div&gt;"
  style="text;html=1;align=left;verticalAlign=top;spacingTop=4;spacingLeft=4;"
  vertex="1" parent="1">
  <mxGeometry x="45" y="115" width="220" height="290" as="geometry" />
</mxCell>
```

## オプション要素

### タイトル

図の上部中央にタイトルを配置する:

```xml
<mxCell id="title" value="ビジネスモデルキャンバス — プロジェクト名"
  style="text;html=1;fontSize=20;fontStyle=1;align=center;verticalAlign=middle;"
  vertex="1" parent="1">
  <mxGeometry x="350" y="15" width="500" height="35" as="geometry" />
</mxCell>
```

### サブタイトル（事業概要）

タイトルの直下に事業概要を1行で配置する:

```xml
<mxCell id="subtitle" value="事業概要テキスト"
  style="text;html=1;fontSize=11;align=center;verticalAlign=middle;fontColor=#666666;"
  vertex="1" parent="1">
  <mxGeometry x="200" y="48" width="800" height="22" as="geometry" />
</mxCell>
```

### 中心の問い（吹き出し）

BMCの下部に、プロジェクトの核心的な問いを吹き出しで配置する:

```xml
<mxCell id="why"
  value="&lt;div style='line-height:1.2'&gt;&lt;b&gt;問いのテキスト&lt;/b&gt;&lt;br&gt;回答テキスト&lt;/div&gt;"
  style="shape=callout;whiteSpace=wrap;html=1;perimeter=calloutPerimeter;size=20;position=0.5;position2=1;base=30;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=12;rounded=1;"
  vertex="1" parent="1">
  <mxGeometry x="450" y="640" width="400" height="80" as="geometry" />
</mxCell>
```

## ページサイズ

BMCは固定レイアウトのため、以下のサイズを使用する:

- **pageWidth**: `1600`
- **pageHeight**: `900`（吹き出しなし） / `800`（吹き出しあり、ただし全体がy=640+80=720に収まる場合）

## 基本のXML構造

```xml
<mxfile host="app.diagrams.net" modified="日付" agent="Claude" version="24.0.0" type="device">
  <diagram id="bmc" name="ビジネスモデルキャンバス">
    <mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1600" pageHeight="900" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />

        <!-- タイトル + サブタイトル -->
        <!-- ⑦ キーパートナー: box-7, label-7, content-7 -->
        <!-- ⑤ 主要な活動: box-5, label-5, content-5 -->
        <!-- ⑥ 主要なリソース: box-6, label-6, content-6 -->
        <!-- ① 価値の提案: box-1, label-1, content-1 -->
        <!-- ③ 顧客との関係: box-3, label-3, content-3 -->
        <!-- ④ チャネル: box-4, label-4, content-4 -->
        <!-- ② 顧客セグメント: box-2, label-2, content-2 -->
        <!-- ⑧ コスト構造: box-8, label-8, content-8 -->
        <!-- ⑨ 収益の流れ: box-9, label-9, content-9 -->
        <!-- （オプション）中心の問い: why -->

      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

### セルIDの命名規則

| 要素 | ID |
|------|-----|
| 枠 | `box-{番号}` |
| ラベル | `label-{番号}` |
| コンテンツ | `content-{番号}` |
| タイトル | `title` |
| サブタイトル | `subtitle` |
| 中心の問い | `why` |

## チェックリスト

生成後、以下を確認すること:

- [ ] `<mxfile>` / `</mxfile>` で囲まれているか
- [ ] 9つの要素すべてが含まれているか
- [ ] 全てのテキストで `line-height:1.2` が指定されているか
- [ ] HTMLタグが正しくエスケープされているか
- [ ] セルIDに重複がないか
- [ ] ① 価値の提案が黄色で強調されているか
- [ ] レイアウトが標準的なBMC配置になっているか

## 出力手順

1. 入力から9つの要素の内容を抽出する
2. 不足している要素があればユーザーに質問する
3. 各要素のテキストを整形する（箇条書き、強調等）
4. 上記レイアウト仕様に従ってXMLを生成する
5. .drawio ファイルとして Write ツールで出力する
6. ユーザーに出力先を報告する
