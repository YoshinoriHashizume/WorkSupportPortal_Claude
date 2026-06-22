#!/usr/bin/env bash
# Install Docker Engine and Compose plugin on Ubuntu (WSL2).
# Run inside Ubuntu: bash scripts/wsl/install-docker-engine.sh
set -euo pipefail

if ! grep -qi microsoft /proc/version 2>/dev/null; then
  echo "WARN: This script is intended for Ubuntu on WSL2." >&2
fi

sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 git

sudo usermod -aG docker "${USER}" || true

if command -v service >/dev/null 2>&1; then
  sudo service docker start || true
fi

echo ""
echo "Docker Engine install finished."
echo "If 'docker' permission denied, run: newgrp docker"
echo "Verify: docker version && docker compose version"
