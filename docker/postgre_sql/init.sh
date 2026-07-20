#!/bin/bash
# PostgreSQL初期化スクリプト
# 環境変数からデータベース名、ユーザー名、パスワードを読み込む
#
# NOTE: PostgreSQL公式イメージでは POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
#       環境変数でデフォルトのDB・ユーザーが自動作成される。
#       このスクリプトでは追加のDB作成やスキーマ設定など拡張的な初期化を行う。

set -e

# 環境変数のデフォルト値を設定（互換性のため）
POSTGRES_DB="${POSTGRES_DB:-django-db}"
POSTGRES_USER="${POSTGRES_USER:-django}"

# psqlコマンドでSQLを実行
# docker-entrypoint-initdb.dのスクリプトはPOSTGRES_USERとして実行される
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- 拡張機能のインストール（必要に応じて）
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "citext";

    -- スキーマの作成（必要に応じて）
    -- CREATE SCHEMA IF NOT EXISTS app;

    -- ユーザーに全権限を付与（既にオーナーだが明示的に）
    GRANT ALL PRIVILEGES ON DATABASE "${POSTGRES_DB}" TO "${POSTGRES_USER}";
    ALTER DATABASE "${POSTGRES_DB}" OWNER TO "${POSTGRES_USER}";
EOSQL

echo "データベース '${POSTGRES_DB}' とユーザー '${POSTGRES_USER}' の初期化が完了しました。"
