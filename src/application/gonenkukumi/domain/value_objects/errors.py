from __future__ import annotations

NAISAK_NOT_FOUND = "NAISAK_NOT_FOUND"


class OracleNotConfiguredError(RuntimeError):
    pass


class OracleQueryError(RuntimeError):
    pass


def oracle_error_message(exc: OracleQueryError) -> str:
    if str(exc) == NAISAK_NOT_FOUND:
        return "内作品番が見つかりません。得意先品番、設変値、対象日付を確認してください。"
    return str(exc)
