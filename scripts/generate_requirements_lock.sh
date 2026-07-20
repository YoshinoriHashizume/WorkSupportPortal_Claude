#!/usr/bin/env bash
# requirements-*.txt（宣言）から pin 済み lock を再生成する。
# 実行例（リポジトリルート、または web-app コンテナ内）:
#   bash scripts/generate_requirements_lock.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv が必要です（Docker web-app 内で実行するか、ホストに uv を入れてください）" >&2
  exit 1
fi

uv pip compile requirements-prod.txt -o requirements-prod.lock.txt
uv pip compile requirements-docker.txt -o requirements-docker.lock.txt
uv pip compile requirements-windows-prod.txt -o requirements-windows-prod.lock.txt

echo "生成完了:"
echo "  requirements-prod.lock.txt"
echo "  requirements-docker.lock.txt"
echo "  requirements-windows-prod.lock.txt"
