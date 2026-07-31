from pathlib import Path

from config.repo_paths import repo_root

import pytest

SRC_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = repo_root(Path(__file__).resolve())

LEGACY_REPO_NAMES = (
    "CoreDataIntegrationPortal",
    "coredataintegrationportal",
)
LEGACY_PRODUCT_NAMES = (
    "基幹システム連携ポータル",
    "基幹データ連携ポータル",
)
EXPECTED_REPO_SLUG = "worksupportportal"
EXPECTED_PRODUCT_NAME = "業務支援ポータル"


@pytest.mark.parametrize(
    "relative_path",
    [
        "docker-compose.devcontainer.yaml",
        ".env.example",
    ],
)
def test_config_files_use_work_support_portal_naming(relative_path):
    content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")

    for legacy in LEGACY_REPO_NAMES:
        assert legacy not in content, f"{relative_path} still contains {legacy}"

    assert EXPECTED_REPO_SLUG in content


def test_base_template_uses_work_support_portal_title():
    content = (SRC_ROOT / "templates" / "base.html").read_text(encoding="utf-8")

    assert EXPECTED_PRODUCT_NAME in content

    for legacy in LEGACY_PRODUCT_NAMES:
        assert legacy not in content
