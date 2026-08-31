from pathlib import Path

from config.repo_paths import repo_root


REPO_ROOT = repo_root(Path(__file__).resolve())


def test_claude_md_is_agent_source_of_truth():
    """エージェント向け常時規約は CLAUDE.md（.cursor/rules ではない）。

    CLAUDE.md は「reference を読まなくても守るべきクリティカルなルール」だけを
    載せるスリムな方針のため、本文の網羅性ではなく最小限の骨格のみを検証する。
    `.cursor/rules` を使わないことは test_cursor_clean_architecture_rule_removed
    で実体側から担保する。
    """
    claude_md = REPO_ROOT / "CLAUDE.md"
    assert claude_md.is_file()
    text = claude_md.read_text(encoding="utf-8")
    assert "Clean Architecture" in text or "クリーンアーキテクチャ" in text
    assert "interfaces → use_cases → domain" in text
    assert "wiring.py" in text


def test_cursor_clean_architecture_rule_removed():
    cursor_rule = REPO_ROOT / ".cursor" / "rules" / "clean-architecture.mdc"
    assert not cursor_rule.is_file()
