from __future__ import annotations

import pytest

from applications.asset_inventory.domain.match_key import build_match_key, normalize_asset_number


@pytest.mark.parametrize(
    ("asset_number", "branch", "expected"),
    [
        ("L5262", "0001", "5262|0001"),
        ("5262", "0001", "5262|0001"),
        ("l999", "0000", "999|0000"),
        (" 3043 ", "0000", "3043|0000"),
    ],
)
def test_TC_AIV_DOM_001_build_match_key(asset_number, branch, expected):
    assert build_match_key(asset_number, branch) == expected


def test_TC_AIV_DOM_003_trim_asset_number():
    assert normalize_asset_number(" 3043 ") == "3043"
