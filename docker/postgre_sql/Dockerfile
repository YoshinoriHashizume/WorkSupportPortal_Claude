FROM postgres:16-bookworm

# カスタム設定ファイルをコピー
COPY postgresql.conf /etc/postgresql/postgresql.conf

# 初期化スクリプトをコピー（コンテナ初回起動時に自動実行される）
COPY init.sh /docker-entrypoint-initdb.d/init.sh
RUN chmod +x /docker-entrypoint-initdb.d/init.sh

# コンテナが HTTP の 5432 番ポートを使うことをドキュメント的に宣言。
# 実際にホスト側のポートと紐付けるのは docker-compose.production.yamlのportsの記述。
EXPOSE 5432
