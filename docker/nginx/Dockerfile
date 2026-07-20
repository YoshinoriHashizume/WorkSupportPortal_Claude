# alpine は軽量な Linux ディストリビューション
FROM nginx:1.27-alpine

# デフォルトの設定ファイルを削除し、カスタム設定をコピー
RUN rm /etc/nginx/conf.d/default.conf
COPY default.conf /etc/nginx/conf.d/default.conf

# コンテナが HTTP の 80 番ポートを使うことをドキュメント的に宣言。
# 実際にホスト側のポートと紐付けるのは docker-compose.production.yamlのportsの記述。
EXPOSE 80
