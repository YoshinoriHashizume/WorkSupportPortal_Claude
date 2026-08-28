from __future__ import annotations

"""基幹 Oracle 接続の共有 ACL。業務 app の infrastructure はここから import する。"""

from application.sales.domain.value_objects.errors import OracleNotConfiguredError, OracleQueryError
from application.gonenkukumi.infrastructure.oracle.client import (
    oracle_config,
    oracle_connect_timeout_seconds,
    oracle_connection,
    rows_as_dicts,
    use_mock,
)

__all__ = [
    "OracleNotConfiguredError",
    "OracleQueryError",
    "oracle_config",
    "oracle_connect_timeout_seconds",
    "oracle_connection",
    "rows_as_dicts",
    "use_mock",
]
