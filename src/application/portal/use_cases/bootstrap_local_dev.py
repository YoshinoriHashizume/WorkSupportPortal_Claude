from __future__ import annotations

from application.portal.domain.repositories.ports import BootstrapLocalDevRunner
from application.portal.domain.value_objects.bootstrap import BootstrapLocalDevConfig, BootstrapUserResult


class BootstrapLocalDev:
    def __init__(self, run_bootstrap: BootstrapLocalDevRunner) -> None:
        self._run_bootstrap = run_bootstrap

    def execute(self, config: BootstrapLocalDevConfig) -> BootstrapUserResult:
        return self._run_bootstrap(config)
