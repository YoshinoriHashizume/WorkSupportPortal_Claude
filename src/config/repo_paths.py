"""リポジトリルート（Docker 環境ルート）を解決する。"""
from __future__ import annotations

import os
from pathlib import Path

_MARKERS = (
    "docker-compose.devcontainer.yaml",
    "docker-compose.production.yaml",
    "Document",
)


def repo_root(start: Path | None = None) -> Path:
    env = os.environ.get("WSP_REPO_ROOT")
    if env:
        path = Path(env)
        if path.is_dir():
            return path

    for candidate in (Path("/repo"),):
        if any((candidate / marker).exists() for marker in _MARKERS):
            return candidate

    here = start or Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if any((parent / marker).exists() for marker in _MARKERS):
            return parent
    # fallback: src の親
    src = Path(__file__).resolve().parents[1]
    return src.parent
