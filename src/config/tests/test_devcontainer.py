from __future__ import annotations

import json
import re
from pathlib import Path

from config.repo_paths import repo_root


REPO_ROOT = repo_root(Path(__file__).resolve())


def _load_devcontainer_json() -> dict:
    path = REPO_ROOT / ".devcontainer" / "devcontainer.json"
    # JSONC（コメント付き）を許容して読む
    raw = path.read_text(encoding="utf-8")
    without_line_comments = re.sub(r"^\s*//.*$", "", raw, flags=re.MULTILINE)
    without_block_comments = re.sub(r"/\*.*?\*/", "", without_line_comments, flags=re.DOTALL)
    return json.loads(without_block_comments)


def test_devcontainer_json_exists_and_targets_web_app():
    data = _load_devcontainer_json()
    assert data["dockerComposeFile"] == "../docker-compose.devcontainer.yaml"
    assert data["service"] == "web-app"
    assert data["workspaceFolder"] == "/django_app/src"
    assert data["remoteUser"] == "vscode"


def test_devcontainer_does_not_bind_host_ssh_directory():
    """個人パス固定の .ssh bind は禁止（起動失敗・秘密鍵露出防止）。"""
    path = REPO_ROOT / ".devcontainer" / "devcontainer.json"
    source = path.read_text(encoding="utf-8")
    assert "ssh-MasatsuguKoga" not in source

    data = _load_devcontainer_json()
    mounts = data.get("mounts") or []
    for mount in mounts:
        assert isinstance(mount, str)
        lower = mount.lower()
        assert "/home/vscode/.ssh" not in lower
        assert "\\.ssh" not in lower
        assert "/.ssh" not in lower.replace("\\", "/")


def test_devcontainer_persists_claude_config_volume_only():
    data = _load_devcontainer_json()
    mounts = data.get("mounts") or []
    assert any("claude-code-config-" in m and "/home/vscode/.claude" in m for m in mounts)
