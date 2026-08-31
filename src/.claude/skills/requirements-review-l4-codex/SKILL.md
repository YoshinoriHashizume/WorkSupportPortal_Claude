---
name: requirements-review-l4-codex
description: |
  要件定義書のL4レビュー（Codexによる独立第2意見レビュー）を実行する。
  Claudeで実施済みのL1（形式）・L2（用語）・L3（妥当性）を1回で網羅する統合レビューを、
  別モデル（Codex / OpenAI）に実行させ、先行レビューの見落としをクロスチェックする。
  レビュー結果は requirements.md には追記せず、別レポートファイルに出力する。
  ユーザーが「Codexでレビューして」「L4レビューをお願い」「別モデルで要件定義書をレビュー」
  「Codexにクロスチェックさせて」などと依頼したときに使用する。
argument-hint: "[要件定義書のファイルパス] [任意: --model <codexモデル名>]"
allowed-tools: Read, Write, Glob, Grep, Bash(command:*), Bash(codex:*), Bash(date:*), Bash(mkdir:*), Bash(cat:*)
---

# 要件定義書 L4レビュー（Codexによる独立第2意見レビュー）

Claude で実施した L1/L2/L3 レビューの後に、**別モデル（Codex / OpenAI）** に
L1+L2+L3 を網羅した統合レビューを実行させ、**独立した第2意見（クロスチェック）** を得るためのスキルです。

- このスキルの実行主体は **Claude（オーケストレーター）** であり、実際のレビューは `codex exec` で起動した Codex が行う。
- レビュー結果は **requirements.md には追記せず、別レポートファイル** に保存する。
- requirements.md の本文・レビュー履歴・その他の成果物は **一切変更しない**。

---

## 前提条件

- Claude 側で L1/L2/L3 レビューを実施済みであること（本スキルはその後の独立チェック）。
- 実行環境に **Codex CLI がインストール・認証済み** であること。
  未インストールの場合はレビューを実行できないため、手順1で検知して中断・案内する。

---

## 手順1: Codex CLI の存在確認（最初に必ず実施）

Codex は PATH に無くても `~/.local/bin/codex` 等に実体があることがある。PATH フォールバックを含めて検出する:

```bash
# PATH に無い環境向けに ~/.local/bin もフォールバックで探す
export PATH="$HOME/.local/bin:$PATH"
command -v codex || ls -l "$HOME/.local/bin/codex" 2>/dev/null
```

- **見つかった場合**: 続けて `codex --version` を確認し、手順2へ進む。
  以降の `codex` 実行でも、必要なら `export PATH="$HOME/.local/bin:$PATH"` を同一コマンド内で前置する。
- **見つからない場合**: レビューは実行できない。以下を案内して **中断** する（ファイルは作成しない）。
  - 「この環境には Codex CLI がインストールされていません。」
  - インストール: `npm install -g @openai/codex`（または Codex の公式手順に従う）
  - 認証: `codex login`（または API キーの設定）
  - インストール・認証後に再度このスキルを実行するよう案内する。

---

## 手順2: レビュー対象と関連文書の特定

$ARGUMENTS

- 第1引数を要件定義書のパスとして扱う。`--model <name>` が渡された場合は Codex モデル指定として控える。
- **引数が空の場合は、必ずユーザーに「どの要件定義書をレビューしますか?」と質問する。**
- パスのヒント: 要件定義書は通常 `application/{app_name}/docs/spec/{feature-name}/requirements.md`。
- 対象ファイルが存在するか Read で確認する（存在しなければユーザーに再確認）。
- 関連文書のパスを Glob で解決する（存在するものだけを Codex に渡す）:
  - `application/{app_name}/docs/ubiquitous_language.md`
  - `docs/ubiquitous_language_core.md`
  - `docs/strategic_design.md`
- 対象パスから `{app_name}` と `{feature-name}` を把握しておく（レポート出力先に使う）。

---

## 手順3: Codex へ渡す統合レビュープロンプトの組み立て（ファイル本文を埋め込む）

> **重要（この環境の制約）**: Codex の実行サンドボックス（bwrap）は、WSL/ネストされたコンテナ環境では
> `bwrap: No permissions to create a new namespace` で起動できないことがある。その場合 Codex は
> **自分でファイルを読めない**。したがって、Codex にファイルパスを渡して読ませるのではなく、
> **対象ファイルの本文をプロンプトに直接埋め込み、Codex にはシェル・ツールを一切使わせない** 方式を既定とする。
> これによりサンドボックスの起動自体が不要になる。詳細は `docs/procedures/codex-install-procedure.md` を参照。

1. このスキルの `references/combined-review-prompt.md` を Read で読み込む（L1+L2+L3 の全13観点と出力フォーマットが自己完結で書かれている）。
2. その内容の末尾に、実行時の情報を追記した「実行時アペンディックス」を作る:
   - **「ツール・シェルを使わないこと。必要なファイル本文はこのプロンプト末尾に埋め込み済み」** と明記する。
   - **存在する関連文書の扱い**（core・strategic_design が無ければ該当観点をスキップする旨）を明記する。
   - Claude 側の L1/L2/L3 レビュー履歴がこの会話内にあれば、その要約を「先行レビューの結論」として添付し、
     「これに引きずられず独立に検証し、見落としを拾うこと」と指示する。
3. 次の順でプロンプトファイル（スクラッチパッド配下、例: `codex-review-prompt.md`）を組み立てる:
   1. `combined-review-prompt.md`（レビュー観点・出力フォーマット）
   2. 実行時アペンディックス（上記2）
   3. **対象 `requirements.md` の本文**（区切り: `===== BEGIN FILE: requirements.md =====` 〜 `===== END FILE ... =====`）
   4. **存在する関連文書（`ubiquitous_language.md` 等）の本文**（同様の区切りで埋め込む）
   - 区切りは三連バッククォートではなく `===== BEGIN/END FILE =====` 形式にする（対象文書内の code fence と衝突しないため）。
   - 組み立ては `cat` で連結するのが簡単（例: `{ cat REF; cat APPENDIX; printf '...BEGIN...'; cat REQ; printf '...END...'; } > PROMPT_FILE`）。

---

## 手順4: Codex の実行（読み取り専用）

Codex にレビュー結果を標準出力へ生成させる。手順3で本文を埋め込んでいるため、Codex は
ファイルを読む必要がなく、シェルも使わない（＝サンドボックス起動が不要）。
ファイルへの保存は Claude 側（手順5）が行う。

```bash
# <PROMPT_FILE>: 手順3で組み立てた（本文埋め込み済みの）プロンプトファイル
# <REPO_ROOT>: リポジトリのルート（例: /django_app/src）
# <OUT_FILE>: Codex の出力を捕捉する一時ファイル（スクラッチパッド配下）
# [--model <name>]: 引数で指定された場合のみ付与（未指定なら Codex 設定のモデルに委譲）

export PATH="$HOME/.local/bin:$PATH"  # PATH に codex が無い環境向けフォールバック
# プロンプトは引数ではなく stdin（末尾の `-`）から渡す。
# 理由: 関連文書を全文埋め込むとプロンプトが数十KBになり、引数展開 "$(cat ...)" では
#       OS の引数長上限(ARG_MAX)を超え `Argument list too long`(exit 126) で失敗するため。
#       stdin は ARG_MAX の影響を受けない。
cat <PROMPT_FILE> | codex exec \
  --sandbox read-only \
  -C <REPO_ROOT> \
  [--model <name>] \
  - \
  > <OUT_FILE> 2>/tmp/codex-review.err
```

- **stdin 方式の理由と代替（重要）**: 上記は末尾 `-` でプロンプトを stdin から読ませる方式。関連文書を全文埋め込むと数十KBになり、引数として渡す（`"$(cat <PROMPT_FILE>)"` を最後の引数にする）と `Argument list too long`(exit 126) で失敗する。`-`/stdin を **サポートしない古い・別バージョンの Codex** では従来どおり引数方式に切り替えてよいが、その場合はプロンプトが ARG_MAX を超えないよう注意する（超える場合は埋め込む関連文書を絞る／要約する）。
- 終了コードを確認する。非0なら `/tmp/codex-review.err` の内容とともにユーザーに報告し、原因（未認証・モデル名誤り・ネットワーク等）を案内して中断する。
- 標準出力（`<OUT_FILE>`）が空・明らかに不完全な場合も、エラー出力を添えて報告する。
- **bwrap エラーが出た場合**: `bwrap: No permissions to create a new namespace` が `<OUT_FILE>` や
  エラー出力に現れ、Codex が「ファイルを読めない」と述べて実質レビューしていないことがある。
  これはサンドボックス（bubblewrap）が namespace を作れないことが原因。**手順3の本文埋め込みが
  正しくできていれば Codex はファイルを読む必要がないので再発しないはず**。それでも Codex が
  コマンド実行を試みて失敗する場合は、外側（Claude 実行環境）で既にサンドボックス済みである前提で
  `--dangerously-bypass-approvals-and-sandbox` を代わりに付けて再実行する（bwrap を経由しなくなる）。
  この場合も本文はプロンプトに埋め込み済みで、プロンプトで「ファイルを変更しない・コマンドを実行しない」と
  厳命しているため、ファイル改変のリスクは低い。
- 上記フラグ名が Codex のバージョンで異なる場合に備え、失敗時は `codex exec --help` を確認して調整する。

---

## 手順5: レビューレポートの保存（別ファイル）

Codex の出力を、requirements.md とは別の専用レポートファイルに保存する。

1. `date '+%Y%m%d-%H%M'` と `date '+%Y/%m/%d %H:%M'` を取得する（ファイル名用・本文用）。
2. 出力先ディレクトリを作成する:
   `application/{app_name}/docs/spec/{feature-name}/reviews/`
   ```bash
   mkdir -p application/{app_name}/docs/spec/{feature-name}/reviews
   ```
3. レポートファイル名: `requirements-review-codex-YYYYMMDD-HHMM.md`
4. `<OUT_FILE>` の内容を Read し、先頭にメタデータヘッダを付けて Write で保存する:

````markdown
# 要件定義書 L4レビュー（Codex 独立第2意見）レポート

- **対象文書**: application/{app_name}/docs/spec/{feature-name}/requirements.md
- **レビュー種別**: L1+L2+L3 統合・独立クロスチェック
- **実行モデル**: <codex実行モデル名 / 未指定なら "Codex 既定モデル">
- **実行ツール**: Codex CLI (`codex exec`)
- **実行日時**: YYYY/MM/DD HH:MM
- **先行レビュー**: Claude による L1/L2/L3（requirements.md のレビュー履歴を参照）

---

（ここに Codex が生成したレビュー本体をそのまま貼り付ける）
````

- **requirements.md 本体・レビュー履歴には追記しない。** 本スキルの成果物はこの別レポートのみ。

---

## 手順6: ユーザーへの報告

- レポートの保存先パスを伝える。
- Codex の総合判定（PASS / CONDITIONAL PASS / FAIL）と、NG・警告の件数を要約する。
- **第2意見としての価値**を明確にする: Claude の L1/L2/L3 レビュー履歴と突き合わせ、
  **Codex だけが指摘した項目（先行レビューの見落とし候補）** を抜き出して提示する。
- 対応方針（どの指摘を requirements.md に反映するか）は **ユーザーが判断** する旨を伝える。
  反映が決まった指摘は、通常どおり該当レベルのスキル（L1/L2/L3）または手動で requirements.md に反映する。

---

## 注意事項

- このスキルは **既存ファイルを変更しない**（レポートの新規作成のみ）。requirements.md やユビキタス言語集の更新は行わない。
- Codex は **読み取り専用** で実行し、ファイル操作は Claude が担う（意図しない変更を防ぐ）。
- Codex の指摘はあくまで **第2意見**。Claude の L1/L2/L3 と食い違う場合は、仕様（SSOT）とユビキタス言語集に照らして最終判断する。
- Codex CLI 未インストール・未認証の環境では実行できない（手順1で検知）。

## 次のステップ

- Codex の指摘のうち反映すべきものを確定したら、対応するレビュー（L1/L2/L3）や手動修正で requirements.md に反映する。
- 反映後、必要なら再度このスキルで独立チェックを行い、レポートを更新（新しいタイムスタンプで別ファイル）してもよい。
