"""推奨アクション定義ファイルの読み込みテスト（test-design.md TC-SFV-I-007〜009）。

`infrastructure/config/recommended_actions.json` があれば `with_action_texts()` で文言を上書きし、
なければ既定、壊れていれば WARNING ログを出して既定に戻す（05 design §4.3、REQ-SFV-F-006・NF-007）。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_INCOMING,
)
from application.inventory_order_alert.domain.value_objects.recommended_action import (
    DEFAULT_RECOMMENDED_ACTIONS,
)
from application.inventory_order_alert.infrastructure.config import recommended_actions as module
from application.inventory_order_alert.infrastructure.config.recommended_actions import (
    DEFAULT_RECOMMENDED_ACTIONS_PATH,
    load_recommended_actions,
)


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


# --- TC-SFV-I-007: 定義ファイルがあれば文言を上書き ---


def test_i007_definition_file_overrides_action_text(tmp_path):
    path = _write(tmp_path / "recommended_actions.json", json.dumps({"low-flow-no-incoming": "X"}, ensure_ascii=False))

    actions = load_recommended_actions(path)

    assert actions.for_quadrant(QUADRANT_LOW_FLOW_NO_INCOMING).action == "X"
    assert actions.for_quadrant(QUADRANT_DORMANT_STOCK) == DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_DORMANT_STOCK)
    assert (
        actions.for_quadrant(QUADRANT_LOW_FLOW_NO_INCOMING).status_template
        == DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_LOW_FLOW_NO_INCOMING).status_template
    )


def test_i007_unknown_keys_and_non_string_values_are_ignored(tmp_path):
    path = _write(
        tmp_path / "recommended_actions.json",
        json.dumps({"foo": "X", "dormant-stock": 123, "low-flow-no-shipment": "Y"}, ensure_ascii=False),
    )

    actions = load_recommended_actions(path)

    assert actions.for_quadrant("低流動品（出荷なし）").action == "Y"
    assert actions.for_quadrant(QUADRANT_DORMANT_STOCK) == DEFAULT_RECOMMENDED_ACTIONS.for_quadrant(QUADRANT_DORMANT_STOCK)


# --- TC-SFV-I-008: 定義ファイルがなければ既定 ---


def test_i008_missing_file_returns_default(tmp_path):
    assert load_recommended_actions(tmp_path / "missing.json") == DEFAULT_RECOMMENDED_ACTIONS


def test_i008_default_path_is_next_to_module_and_currently_absent_returns_default():
    assert DEFAULT_RECOMMENDED_ACTIONS_PATH.parent == Path(module.__file__).parent
    assert DEFAULT_RECOMMENDED_ACTIONS_PATH.name == "recommended_actions.json"
    # 既定パスにファイルがなければ既定を返す（ある場合は上書き後のコレクションになる）
    actions = load_recommended_actions()
    assert len(actions) == 4


# --- TC-SFV-I-009: 定義ファイルが不正 JSON なら警告ログを出して既定 ---


def test_i009_broken_json_logs_warning_and_returns_default(tmp_path, caplog):
    path = _write(tmp_path / "recommended_actions.json", "{ not json")

    with caplog.at_level(logging.WARNING):
        actions = load_recommended_actions(path)

    assert actions == DEFAULT_RECOMMENDED_ACTIONS
    assert any(record.levelno == logging.WARNING and "recommended_actions.json" in record.getMessage() for record in caplog.records)


def test_i009_non_object_json_logs_warning_and_returns_default(tmp_path, caplog):
    path = _write(tmp_path / "recommended_actions.json", json.dumps(["X"]))

    with caplog.at_level(logging.WARNING):
        actions = load_recommended_actions(path)

    assert actions == DEFAULT_RECOMMENDED_ACTIONS
    assert any(record.levelno == logging.WARNING for record in caplog.records)
