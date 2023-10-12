# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys

import pytest

from ddev.e2e.constants import E2EEnvVars
from ddev.e2e.run import E2EEnvironmentRunner


@pytest.fixture(scope='module')
def trigger_command() -> list[str]:
    def _trigger_command(env: str) -> list[str]:
        return [
            sys.executable,
            '-m',
            'hatch',
            'env',
            'run',
            '--env',
            env,
            '--',
            'test',
            '--capture=no',
            '--disable-warnings',
            '--exitfirst',
            '-qqqq',
            '--no-header',
        ]

    return _trigger_command


@pytest.fixture(scope='module')
def trigger_command_py2(trigger_command) -> list[str]:
    return lambda env: trigger_command(env)[:-1]


class TestE2EEnvironmentRunner:
    def test_start(self, trigger_command) -> None:
        old_env_vars = dict(os.environ)
        runner = E2EEnvironmentRunner('py3.11', 0)
        with runner.start() as command:
            new_env_vars = dict(os.environ)

            assert command == trigger_command('py3.11')
            assert set(new_env_vars) - set(old_env_vars) == {E2EEnvVars.TEAR_DOWN}
            assert new_env_vars[E2EEnvVars.TEAR_DOWN] == 'false'

    def test_start_py2(self, trigger_command_py2) -> None:
        old_env_vars = dict(os.environ)
        runner = E2EEnvironmentRunner('py2.7', 0)
        with runner.start() as command:
            new_env_vars = dict(os.environ)

            assert command == trigger_command_py2('py2.7')
            assert set(new_env_vars) - set(old_env_vars) == {E2EEnvVars.TEAR_DOWN}
            assert new_env_vars[E2EEnvVars.TEAR_DOWN] == 'false'

    def test_stop(self, trigger_command) -> None:
        old_env_vars = dict(os.environ)
        runner = E2EEnvironmentRunner('py3.11', 0)
        with runner.stop() as command:
            new_env_vars = dict(os.environ)

            assert command == trigger_command('py3.11')
            assert set(new_env_vars) - set(old_env_vars) == {E2EEnvVars.SET_UP}
            assert new_env_vars[E2EEnvVars.SET_UP] == 'false'

    def test_stop_py2(self, trigger_command_py2) -> None:
        old_env_vars = dict(os.environ)
        runner = E2EEnvironmentRunner('py2.7', 0)
        with runner.stop() as command:
            new_env_vars = dict(os.environ)

            assert command == trigger_command_py2('py2.7')
            assert set(new_env_vars) - set(old_env_vars) == {E2EEnvVars.SET_UP}
            assert new_env_vars[E2EEnvVars.SET_UP] == 'false'

    def test_verbosity(self, trigger_command) -> None:
        old_env_vars = dict(os.environ)
        runner = E2EEnvironmentRunner('py3.11', 1)
        with runner.start() as command:
            new_env_vars = dict(os.environ)

            assert command == trigger_command('py3.11')
            assert set(new_env_vars) - set(old_env_vars) == {E2EEnvVars.TEAR_DOWN, 'HATCH_VERBOSE'}
            assert new_env_vars[E2EEnvVars.TEAR_DOWN] == 'false'
            assert new_env_vars['HATCH_VERBOSE'] == '1'
