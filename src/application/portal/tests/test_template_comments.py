"""テンプレートのコメント記法の検査（プロジェクト全体）。

Django の `{# ... #}` は **1 行コメント専用**で、複数行にまたがると閉じられず、
**コメントの中身がそのまま画面に表示される**。2026-09-30 に在庫発注アラートの詳細ダイアログで
実際に発生したため、全テンプレートを走査して再発を防ぐ。

複数行の注釈を書きたいときは `{% comment %} ... {% endcomment %}` を使う。
"""

from __future__ import annotations

from pathlib import Path

import pytest

TEMPLATES_ROOT = Path(__file__).resolve().parents[3] / "templates"


def _template_files() -> list[Path]:
    return sorted(TEMPLATES_ROOT.rglob("*.html"))


def test_scan_covers_the_templates():
    # 走査対象が空だと検証が素通りするため、件数そのものを固定する
    assert len(_template_files()) > 20


@pytest.mark.parametrize("path", _template_files(), ids=lambda path: str(path.relative_to(TEMPLATES_ROOT)))
def test_inline_comments_are_closed_on_the_same_line(path: Path):
    """`{#` は同じ行で `#}` を閉じること。閉じないと中身が画面に出る。"""
    offenders = [
        (index, line.strip())
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if line.count("{#") > line.count("#}")
    ]

    assert offenders == [], (
        f"{path.relative_to(TEMPLATES_ROOT)} に複数行の {{# #}} があります。"
        "Django の {# #} は 1 行専用で、複数行にすると中身が画面に表示されます。"
        "1 行にまとめるか {% comment %} を使ってください: " + str(offenders)
    )
