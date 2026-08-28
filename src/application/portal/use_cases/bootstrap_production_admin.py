from __future__ import annotations

from application.portal.domain.repositories.ports import BootstrapProductionAdminRunner
from application.portal.domain.value_objects.bootstrap import BootstrapProductionAdminConfig, BootstrapUserResult


class BootstrapProductionAdmin:
    def __init__(self, run_bootstrap: BootstrapProductionAdminRunner) -> None:
        self._run_bootstrap = run_bootstrap

    def execute(self, config: BootstrapProductionAdminConfig) -> BootstrapUserResult:
        return self._run_bootstrap(config)
