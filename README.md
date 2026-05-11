# Core Data Integration Portal

リポジトリ／作業フォルダ名: **CoreDataIntegrationPortal**

基幹データ連携ポータル（仕様は `Document/` を参照）。

## セットアップ

1. Node.js 20+ を用意する。
2. `.env.example` を **`.env.local` と `.env` の両方**に反映する（または `DATABASE_URL` 等を両方に同じ内容で書く）。**Prisma CLI**（`npx prisma`）は主に **`.env`** を読むため、`.env.local` のみだと接続先がずれることがある。
3. PostgreSQL を起動する（ローカルまたは `docker compose up -d postgres` など）。**起動前に開発ログインすると Auth.js の CallbackRouteError**（内部では DB 接続失敗など）になりやすい。
4. スキーマ反映とシード:

```bash
npx prisma db push
npx prisma db seed
```

5. 開発サーバー:

```bash
npm run dev
```

同一 PC なら `http://localhost:3000`、**別 PC からデバッグ**するときは開発 PC の LAN IP（例 `http://192.168.1.10:3000`）で開く。`.env.local` の **`AUTH_URL` をその URL に合わせる**（Auth.js のリダイレクト整合）。`npm run dev` は `0.0.0.0` で待ち受けるため、同一 LAN からポート 3000 に届くよう OS のファイアウォールだけ許可すればよい。  
`AUTH_DEV_MODE=true` のときはログイン画面から **開発ユーザー**（`dev@local` / `dev`）でサインインできる。

### トラブル時

- **Docker を使う場合**: 先に **Docker Desktop を起動**してから `docker compose` を実行する。
- **PowerShell 5.x** ではコマンドを `&&` でつなげないことがある。ディレクトリ移動と実行は行を分けるか、`;` を使う。
- **ローカルデバッグ時**に Docker・DB・開発サーバーをどの順で立ち上げるかは **`Document/ローカル開発環境構築手順.md` §13** を参照する。
- 上記の詳細・その他の対処は **`Document/ローカル開発環境構築手順.md` §10** を参照する。

## Docker（app + PostgreSQL + nginx）

```bash
# .env.local に AUTH_SECRET 等を記載してから
docker compose up -d --build
```

アプリ直: `http://localhost:3000`（別 PC からは `http://<ホストIP>:3000`）、nginx 経由: `http://localhost:8080`（同様に IP 可）。Docker 利用時も **`.env.local` の `AUTH_URL`** を実際にブラウザで開くオリジンに合わせる。

## フォルダ構成

DDD の方針は `Document/ドメイン駆動設計.md` §5。`src/domains/` にコンテキスト、`src/infrastructure/` に Prisma / Oracle など。
