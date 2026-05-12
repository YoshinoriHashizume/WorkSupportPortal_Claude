# Microsoft 認証（Entra ID）構築手順

## 文書情報

| 項目 | 内容 |
|------|------|
| 目的 | 本ポータルで **「Microsoft で続行」** ログインを動かすまでを、**Microsoft 側の画面操作**と**アプリの環境変数**まで手順どおりに示す |
| 前提 | 会社の **Microsoft 365 / Entra ID のテナントはすでにある**（テナント新規作成は対象外） |
| 実装 | Auth.js（NextAuth.js）、プロバイダ `microsoft-entra-id`（[`src/auth.ts`](../src/auth.ts)） |

### 作業開始前に確定していること

次の **いずれかの URL** を、ログイン検証時にブラウザのアドレスバーに表示するオリジンとして使う（Entra のリダイレクト URI と一致させる）。

| 用途 | 入力・登録に使うオリジン（本ドキュメントの固定値） |
|------|------------------------------------------------------|
| PC で開発アプリを `npm run dev` し、`http://localhost:3000` で開く | `http://localhost:3000` |
| 本番（[`本番環境デプロイ手順.md`](本番環境デプロイ手順.md) と同じ公開 URL） | `http://192.168.3.196` |
| Docker Compose の nginx で `http://localhost:8080` だけを開く | `http://localhost:8080` |

上記以外の URL で公開する場合は、**実際にユーザーがアドレスバーで見る `http...` または `https...` まで**（末尾 `/` なし）をメモし、以降の **リダイレクト URI** と **`AUTH_URL`** の両方に **同じオリジン** を使う。

---

## 用語（最小）

| 用語 | 意味 |
|------|------|
| **テナント** | 会社の Microsoft アカウントが属するディレクトリ |
| **アプリ登録** | この Web アプリが Microsoft サインインを利用するための登録 |
| **クライアント ID** | アプリ登録ごとの UUID（第三者に知られても設計上問題ない識別子） |
| **クライアントシークレット** | アプリだけが保持する秘密文字列 |
| **リダイレクト URI** | サインイン完了後に Microsoft がブラウザを返す URL（パスは本アプリで固定） |

---

## パート A: Microsoft（Entra ID）側の作業

**サインインするアカウント**

次の **いずれかのロール**を持つアカウントで [Microsoft Entra 管理センター](https://entra.microsoft.com) または [Azure ポータル](https://portal.azure.com) にサインインする。

- グローバル管理者  
- アプリケーション管理者  
- クラウド アプリケーション管理者  

（いずれも無い場合は、上記ロールを付与された担当者に本パートの操作を依頼する。）

**ポータルでの開き方（どちらか一方）**

- Entra 管理センター: 左メニュー **アプリケーション** → **アプリの登録**  
- Azure ポータル: 左メニュー **Microsoft Entra ID** → **アプリの登録**

以下、メニュー名は **Entra 管理センター** に合わせて記載する。

### A-1. アプリ登録を新規作成する

1. **アプリの登録** で **＋ 新規登録** をクリックする。  
2. 次の表のとおり入力する。

| 画面の項目 | 入力する値 |
|------------|------------|
| **名前** | `CoreDataIntegrationPortal` |
| **サポートされているアカウントの種類** | **この組織ディレクトリのみに含まれるアカウント** を選択する。 |
| **リダイレクト URI**（種類が求められる場合は **Web**） | **空のまま**にする（A-2 で登録する）。 |

3. **登録** をクリックする。  
4. **アプリの概要** 画面が表示されたら、その画面を閉じずに A-2 に進む。

### A-2. リダイレクト URI を登録する

コールバック URL は次の **テンプレート** である（`{オリジン}` を **スキーム + ホスト + ポート（ポートがあるときのみ）** に置き換える。末尾 `/` は付けない）。

```text
{オリジン}/api/auth/callback/microsoft-entra-id
```

**登録操作**

1. 左メニュー **認証** を開く。  
2. **プラットフォーム構成** で **＋ プラットフォームを追加** → **Web** を選択する。  
3. **リダイレクト URI** に、使う環境に応じて **次の表の「登録する 1 行」をそのままコピーして貼り付ける**（複数環境で使うなら行を追加し、貼り付けを繰り返す）。

| 使うオリジン | リダイレクト URI に貼り付ける文字列（全文） |
|--------------|---------------------------------------------|
| `http://localhost:3000` | `http://localhost:3000/api/auth/callback/microsoft-entra-id` |
| `http://192.168.3.196` | `http://192.168.3.196/api/auth/callback/microsoft-entra-id` |
| `http://localhost:8080` | `http://localhost:8080/api/auth/callback/microsoft-entra-id` |
| 上記以外 | テンプレートの `{オリジン}` を、メモしたオリジンに置き換えた 1 行を入力する。 |

4. **フロントチャネルのログアウト URL** は **空のまま**にする。  
5. **構成** または **保存** をクリックして保存する。

**失敗時の代表原因**

`redirect_uri_mismatch` が出る場合、Entra に登録した URI と、ブラウザで開いているオリジン＋パス `/api/auth/callback/microsoft-entra-id` が **完全一致**していない（`http` と `https`、`localhost` と `127.0.0.1`、ポートの有無は別物）。

### A-3. API のアクセス許可

1. 左メニュー **API のアクセス許可** を開く。  
2. **＋ アクセス許可の追加** → **Microsoft Graph** → **委任されたアクセス許可** を選択する。  
3. 次の **4 つ** を検索して追加する（追加後、一覧に 4 つ並ぶこと）。

| 追加する権限名（検索キー） |
|----------------------------|
| `openid` |
| `profile` |
| `email` |
| `User.Read` |

4. **アクセス許可の追加** をクリックして確定する。  
5. 画面上部に **（テナント名）に管理者の同意を与えます** というボタンが表示されている場合はクリックして同意する。表示されていない場合は **手順 5 は行わない**。

### A-4. クライアントシークレットを発行する

1. 左メニュー **証明書とシークレット** を開く。  
2. **クライアント シークレット** タブで **＋ 新しいクライアント シークレット** をクリックする。  
3. 次のとおり入力して **追加** をクリックする。

| 画面の項目 | 入力する値 |
|------------|------------|
| **説明** | `CoreDataIntegrationPortal-EntraClientSecret-1` |
| **有効期限** | 画面上のプルダウンで **最長の期間** を選択する（例として **24 か月** が表示されていればそれを選ぶ。24 か月が無い場合は一覧に表示される **最長** を選ぶ） |

4. 一覧に表示される **値** 列の文字列を **すぐにコピー**する（この画面を離れると **値の全文は再表示されない**）。  
5. コピーした文字列を、社内の秘密情報保管場所に保存する（平文メールでの送付は禁止）。

有効期限が切れる前に、新しいシークレットを同手順で追加し、アプリの `AUTH_MICROSOFT_ENTRA_ID_SECRET` を新しい値に差し替える。

### A-5. アプリ担当へ渡す 4 項目（コピー元と環境変数名）

アプリ登録の **概要** 画面で次をコピーし、安全な経路でアプリ担当へ渡す。

| 渡す項目 | Entra の画面でのコピー元 | アプリ側の環境変数名 |
|----------|--------------------------|----------------------|
| 1. アプリケーション（クライアント）ID | **概要** の「アプリケーション (クライアント) ID」 | `AUTH_MICROSOFT_ENTRA_ID_ID` |
| 2. ディレクトリ（テナント）ID | **概要** の「ディレクトリ (テナント) ID」 | 下記 Issuer 組み立てに使用 |
| 3. クライアントシークレットの値 | A-4 の手順 4 でコピーした **値**（「シークレット ID」ではない） | `AUTH_MICROSOFT_ENTRA_ID_SECRET` |
| 4. Issuer URL | 手順は下の **Issuer の組み立て** | `AUTH_MICROSOFT_ENTRA_ID_ISSUER` |

**Issuer の組み立て**

1. 項目 2 の **ディレクトリ（テナント）ID** の UUID をコピーする（ハイフン付きのまま）。  
2. 次の 1 行の `<テナントID>` を、その UUID に **置き換えた結果** を `AUTH_MICROSOFT_ENTRA_ID_ISSUER` に渡す（角括弧 `<` `>` は削除し、UUID のみが入る）。

```text
https://login.microsoftonline.com/<テナントID>/v2.0
```

**組み立て例（値はダミー。実際は手順 1 の UUID に置き換える）**

テナント ID が `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` のとき、Issuer は次の **1 行**である。

```text
https://login.microsoftonline.com/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/v2.0
```

---

## パート B: アプリ（本リポジトリ）側の作業

### B-1. 環境変数ファイルを用意する

1. リポジトリの [`.env.example`](../.env.example) をコピーし、ファイル名を **`.env.local`** にする（本番サーバーでは運用ルールに従い、同じ変数名で秘密管理に登録する）。  
2. 次の表の **「入力する値」** 列どおりに設定する（変数名は左列のとおり）。

| 環境変数名 | 必須 | 入力する値 |
|------------|------|------------|
| `AUTH_SECRET` | はい | 直下の **AUTH_SECRET の生成** に従って生成した文字列を、`AUTH_SECRET="..."` の形式で入力する。変数名 `NEXTAUTH_SECRET` でも可（実装が `AUTH_SECRET` と併読する）。 |
| `AUTH_TRUST_HOST` | はい | `true` |
| `AUTH_URL` | はい（またはコメントアウト） | 直下の **AUTH_URL に入力する値** の表から **1 行だけ**選び、その「入力する値」列を入力する。`AUTH_URL` を設定しない運用にする場合は、`.env.example` と同様に **`AUTH_URL=` 行をコメントアウト**する。 |
| `AUTH_MICROSOFT_ENTRA_ID_ID` | はい | A-5 の項目 1（クライアント ID）を **そのまま貼り付け**る。 |
| `AUTH_MICROSOFT_ENTRA_ID_SECRET` | はい | A-5 の項目 3（シークレットの値）を **そのまま貼り付け**る。 |
| `AUTH_MICROSOFT_ENTRA_ID_ISSUER` | はい | A-5 の項目 4（組み立てた Issuer URL）を **そのまま 1 行で貼り付け**る。 |

**AUTH_SECRET の生成（いずれか 1 つ）**

- Git Bash / WSL / macOS / Linux: ターミナルで `openssl rand -base64 32` を実行し、表示された 1 行をコピーする。  
- PowerShell: 下記「PowerShell で `AUTH_SECRET` を生成」を実行し、表示 1 行をコピーする。

**AUTH_URL に入力する値**

| ブラウザで開く URL のオリジン | `AUTH_URL` に入力する文字列（全文） |
|------------------------------|-------------------------------------|
| `http://localhost:3000` | `http://localhost:3000` |
| `http://192.168.3.196` | `http://192.168.3.196` |
| `http://localhost:8080` | `http://localhost:8080` |
| 上記以外 | 作業開始前にメモしたオリジンと **同一の文字列** |

**`.env.local` の記入例**

```env
AUTH_SECRET="（AUTH_SECRET の生成で得た文字列）"
AUTH_TRUST_HOST="true"
AUTH_URL="http://localhost:3000"

AUTH_MICROSOFT_ENTRA_ID_ID="bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
AUTH_MICROSOFT_ENTRA_ID_SECRET="（A-4 でコピーしたシークレットの値）"
AUTH_MICROSOFT_ENTRA_ID_ISSUER="https://login.microsoftonline.com/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/v2.0"
```

- `AUTH_SECRET` の引用符内は、上記 **AUTH_SECRET の生成** の出力に置き換える。  
- `AUTH_MICROSOFT_ENTRA_ID_ID` の引用符内は、A-5 の **項目 1** に置き換える（`bbbbbbbb-...` はダミー）。  
- `AUTH_MICROSOFT_ENTRA_ID_SECRET` の引用符内は、A-5 の **項目 3** に置き換える。  
- `AUTH_MICROSOFT_ENTRA_ID_ISSUER` の 1 行は、A-5 の **項目 4** に置き換える（`aaaaaaaa-...` はダミー）。  
- `AUTH_URL` の行は、**AUTH_URL に入力する値** の表に合わせて書き換える。

**PowerShell で `AUTH_SECRET` を生成する**

```powershell
[Convert]::ToBase64String([byte[]](1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

表示された **1 行**をコピーし、`AUTH_SECRET="..."` の引用符内に貼り付ける。

### B-2. URL の一致確認（チェックリスト）

次の **3 つの文字列**が、すべて **同じオリジン** になっていること（末尾 `/` なし）。

1. ログイン試験時にブラウザのアドレスバーに表示される `http...` または `https...` まで（パスより前）。  
2. Entra の **認証** に登録したリダイレクト URI のうち、今回使っている行の **`/api/auth/callback/microsoft-entra-id` より前**の部分。  
3. `.env.local` に **`AUTH_URL` または `NEXTAUTH_URL` の行がある場合**は、その行の値が 1 と同じオリジンか確認する。**`AUTH_URL` / `NEXTAUTH_URL` をコメントアウトしている場合**は、1 と 2 の一致だけを確認する。

### B-3. 動作確認

1. アプリを起動し、`/login` を開く。  
2. `AUTH_MICROSOFT_ENTRA_ID_ID` と `AUTH_MICROSOFT_ENTRA_ID_SECRET` の両方が空でないとき、**「Microsoft で続行」** ボタンが表示される。  
3. そのボタンから会社アカウントでサインインできることを確認する。

### B-4. Entra 未設定で画面だけ試す場合

`NODE_ENV=development` かつ **`AUTH_DEV_MODE=true`** のとき、ログイン画面から **メール `dev@local` / パスワード `dev`** でサインインできる。本番では **`AUTH_DEV_MODE` を書かない** または `false` にする。詳細は [`ローカル開発環境構築手順.md`](ローカル開発環境構築手順.md) を参照する。

---

## トラブルシューティング

| 症状 | 確認する項目 |
|------|----------------|
| `redirect_uri_mismatch` | Entra **認証** のリダイレクト URI が、`{使用中のオリジン}/api/auth/callback/microsoft-entra-id` と **完全一致**か。 |
| ログイン直後にエラー・ループ | `AUTH_URL` / `NEXTAUTH_URL` が B-2 の 1 と一致しているか。`AUTH_TRUST_HOST` が `true` か。 |
| Microsoft ボタンが出ない | `AUTH_MICROSOFT_ENTRA_ID_ID` と `AUTH_MICROSOFT_ENTRA_ID_SECRET` が両方とも空でないか（[`src/auth.ts`](../src/auth.ts)）。 |
| シークレット失効 | A-4 で新しいシークレットを発行し、`AUTH_MICROSOFT_ENTRA_ID_SECRET` を新しい値に更新する。 |

---

## 関連ドキュメント

| 文書 |
|------|
| [`アプリケーション仕様書.md`](アプリケーション仕様書.md) |
| [`ローカル開発環境構築手順.md`](ローカル開発環境構築手順.md) |
| [`本番環境デプロイ手順.md`](本番環境デプロイ手順.md) |

---

## 改訂履歴

| 版 | 日付 | 変更内容 |
|----|------|----------|
| 0.1 | 2026-04-17 | 初版相当 |
| 0.2 | 2026-05-12 | 手順の再構成、リダイレクト URI・Issuer・環境変数の対応を追記 |
| 0.3 | 2026-05-12 | 曖昧表現を削り、画面入力値・固定文字列・分岐を表で明示 |
