from __future__ import annotations

from collections.abc import Callable

from apps.portal.domain.bootstrap import BootstrapProductionAdminConfig, BootstrapUserResult

BootstrapProductionAdminRunner = Callable[[BootstrapProductionAdminConfig], BootstrapUserResult]


class BootstrapProductionAdminUsecase:
    def __init__(self, run_bootstrap: BootstrapProductionAdminRunner) -> None:
        self._run_bootstrap = run_bootstrap

    def execute(self, config: BootstrapProductionAdminConfig) -> BootstrapUserResult:
        return self._run_bootstrap(config)
