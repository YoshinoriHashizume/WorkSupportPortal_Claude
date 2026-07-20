#!/bin/sh

# エラー時にスクリプトを停止
set -e

# 開始時刻を記録
START_TIME=$(date)

# ログディレクトリを作成（最初に実行）
mkdir -p /django_app/src/logs

echo "=========================================="
echo "ENTRYPOINT.SH 実行開始"
echo "=========================================="
echo "開始時刻: $START_TIME"
echo "現在のディレクトリ: $(pwd)"
echo "環境変数DEBUG: $DEBUG"
echo "=========================================="

# ログファイルに記録
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ENTRYPOINT.SH 実行開始" >> /django_app/src/logs/django.log


# タイムゾーンを設定
echo "タイムゾーン設定中..."
export TZ=Asia/Tokyo
echo "タイムゾーン設定完了: $TZ"

# デバッグ用にディレクトリ内容を表示
echo "ディレクトリ構造確認中..."
cd /django_app/
echo "メインディレクトリ: $(pwd)"
ls -la /django_app/

cd /django_app/src
echo "ソースディレクトリ: $(pwd)"
ls -la /django_app/src/
echo "ディレクトリ構造確認完了"

# マイグレーション
echo "=========================================="
echo "データベースマイグレーション開始"
echo "=========================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] データベースマイグレーション開始" >> /django_app/src/logs/django.log
echo "DB 接続待ち..."
i=0
DB_OK=0
while [ "$i" -lt 30 ]; do
  if python -c "import django; django.setup(); from django.db import connection; connection.ensure_connection()" 2>/dev/null; then
    echo "DB 接続 OK"
    DB_OK=1
    break
  fi
  i=$((i + 1))
  sleep 2
done
if [ "$DB_OK" -ne 1 ]; then
  echo "DB 接続に失敗しました（タイムアウト）"
  exit 1
fi
echo "migrate実行中..."
python manage.py migrate --noinput
if [ "$AUTH_DEV_MODE" = "true" ]; then
  python manage.py bootstrap_local_dev || true
fi
echo "データベースマイグレーション完了"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] データベースマイグレーション完了" >> /django_app/src/logs/django.log

# 静的ファイルのコピー
echo "=========================================="
echo "静的ファイル収集開始"
echo "=========================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 静的ファイル収集開始" >> /django_app/src/logs/django.log
echo "collectstatic実行中..."
python manage.py collectstatic --noinput
echo "静的ファイル収集完了"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 静的ファイル収集完了" >> /django_app/src/logs/django.log


# サーバー起動処理
echo "=========================================="
echo "サーバー起動処理開始"
echo "=========================================="

# 処理時間を計算
END_TIME=$(date)
echo "処理開始時刻: $START_TIME"
echo "処理終了時刻: $END_TIME"

# ログファイルに記録
echo "[$(date '+%Y-%m-%d %H:%M:%S')] サーバー起動処理開始" >> /django_app/src/logs/django.log

# DEBUG / DJANGO_DEBUG のどちらかが真なら開発サーバー
# exec により runserver / gunicorn が PID 1 になり、停止・ヘルスチェックと連動する
# WEB_BIND_PORT があれば優先（devcontainer は常に 8880 にしてホスト 8990 と揃える）
_DEBUG_FLAG=$(printf '%s' "${DEBUG:-${DJANGO_DEBUG:-false}}" | tr '[:upper:]' '[:lower:]')
if [ "$_DEBUG_FLAG" = "true" ] || [ "$_DEBUG_FLAG" = "1" ]; then
    _DEFAULT_BIND_PORT=8880
else
    _DEFAULT_BIND_PORT=8000
fi
_BIND_PORT=$(printf '%s' "${WEB_BIND_PORT:-$_DEFAULT_BIND_PORT}" | tr -d '[:space:]')
if [ -z "$_BIND_PORT" ]; then
    _BIND_PORT="$_DEFAULT_BIND_PORT"
fi

if [ "$_DEBUG_FLAG" = "true" ] || [ "$_DEBUG_FLAG" = "1" ]; then
    echo "開発サーバー起動中..."
    echo "アクセスURL（コンテナ内）: http://localhost:${_BIND_PORT}"
    echo "アクセスURL（ホストから）: http://localhost:8990 （ポートフォワード 8990->${_BIND_PORT}）"
    echo "=========================================="
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 開発サーバー起動開始" >> /django_app/src/logs/django.log
    exec python manage.py runserver "0.0.0.0:${_BIND_PORT}"
else
    echo "本番サーバー起動中..."
    echo "アクセスURL: http://localhost:${_BIND_PORT}"
    echo "=========================================="
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 本番サーバー起動開始" >> /django_app/src/logs/django.log
    exec gunicorn config.wsgi:application --bind "0.0.0.0:${_BIND_PORT}" --chdir /django_app/src --workers 3 --timeout 120
fi
