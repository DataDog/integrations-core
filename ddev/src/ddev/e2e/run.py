# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Generator

from ddev.e2e.constants import E2EEnvVars
from ddev.utils.hatch import get_hatch_env_vars
from ddev.utils.structures import EnvVars


class E2EEnvironmentRunner:
    def __init__(self, env: str, verbosity: int):
        self.__env = env
        self.__verbosity = verbosity

    @contextmanager
    def start(self) -> Generator[list[str], None, None]:
        with EnvVars({E2EEnvVars.TEAR_DOWN: 'false', **get_hatch_env_vars(verbosity=self.__verbosity)}):
            yield self._base_command()

    @contextmanager
    def stop(self) -> Generator[list[str], None, None]:
        with EnvVars({E2EEnvVars.SET_UP: 'false', **get_hatch_env_vars(verbosity=self.__verbosity)}):
            yield self._base_command()

    def _base_command(self) -> list[str]:
        return [
            sys.executable,
            '-m',
            'hatch',
            'env',
            'run',
            '--env',
            self.__env,
            '--',
            'test',
            '--capture=no',
            '--disable-warnings',
            '--exitfirst',
            # We need -2 verbosity and by default the test command sets the verbosity to +2
            '-qqqq',
            '--no-header',
        ]
