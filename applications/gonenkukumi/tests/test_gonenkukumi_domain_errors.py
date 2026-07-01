from __future__ import annotations

from applications.gonenkukumi.domain.errors import (
    NAISAK_NOT_FOUND,
    OracleQueryError,
    oracle_error_message,
)


def test_oracle_error_message_maps_naisak_not_found():
    message = oracle_error_message(OracleQueryError(NAISAK_NOT_FOUND))
    assert "内作品番が見つかりません" in message


def test_oracle_error_message_passes_through_other_errors():
    assert oracle_error_message(OracleQueryError("得意先候補の取得に失敗しました。")) == (
        "得意先候補の取得に失敗しました。"
    )
