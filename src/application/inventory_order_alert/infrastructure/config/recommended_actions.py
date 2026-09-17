"""推奨アクション（T-207）の文言を定義ファイルで上書きする（05 design §4.3、REQ-SFV-F-006・NF-007）。

同じディレクトリの `recommended_actions.json`（`{"low-flow-no-incoming": "...", ...}`）を読み、
`RecommendedActions.with_action_texts()` で既定の文言を差し替える。
ファイルがなければ既定、壊れていれば WARNING ログを出して既定に戻す（画面を止めない）。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from application.inventory_order_alert.domain.value_objects.recommended_action import (
    DEFAULT_RECOMMENDED_ACTIONS,
    RecommendedActions,
)

logger = logging.getLogger(__name__)

#: 既定の定義ファイル。キーは流動区分キー（`FLOW_QUADRANT_KEYS` の値）、値は推奨アクションの文言。
DEFAULT_RECOMMENDED_ACTIONS_PATH = Path(__file__).resolve().parent / "recommended_actions.json"


def _read_overrides(path: Path) -> dict[str, str]:
    """定義ファイルを読み、文字列の値だけを返す。読めない・形式外は空にする。"""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("推奨アクション定義ファイルを読み込めないため既定を使います: %s (%s)", path, exc)
        return {}
    if not isinstance(raw, dict):
        logger.warning("推奨アクション定義ファイルはオブジェクト形式である必要があります（既定を使います）: %s", path)
        return {}
    return {str(key): value for key, value in raw.items() if isinstance(value, str)}


def load_recommended_actions(path: Path | None = None) -> RecommendedActions:
    """定義ファイルを適用した推奨アクションのコレクションを返す。"""
    target = path if path is not None else DEFAULT_RECOMMENDED_ACTIONS_PATH
    if not target.exists():
        return DEFAULT_RECOMMENDED_ACTIONS
    return DEFAULT_RECOMMENDED_ACTIONS.with_action_texts(_read_overrides(target))
