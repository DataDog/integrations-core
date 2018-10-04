# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys

import pytest

from datadog_checks.dev.conditions import (
    CheckCommandOutput, CheckDockerLogs, CheckEndpoints, WaitFor
)
from datadog_checks.dev.errors import RetryError
from datadog_checks.dev.subprocess import run_command

HERE = os.path.dirname(os.path.abspath(__file__))
DOCKER_DIR = os.path.join(HERE, 'docker')


class TestWaitFor:
    def test_no_error_no_result_success(self):
        assert WaitFor(lambda: None)() is True

    def test_no_error_true_result_success(self):
        assert WaitFor(lambda: True)() is True

    def test_no_error_non_true_result_fail(self):
        with pytest.raises(RetryError):
            WaitFor(lambda: False, attempts=1)()

    def test_error_fail(self):
        def f():
            raise Exception

        with pytest.raises(RetryError):
            WaitFor(f, attempts=1)()


class TestCheckCommandOutput:
    def test_no_matches(self):
        check_command_output = CheckCommandOutput(
            '{} -c "import os;print(\'foo\')"'.format(sys.executable),
            ['bar'],
            attempts=1
        )

        with pytest.raises(RetryError):
            check_command_output()

    def test_matches(self):
        check_command_output = CheckCommandOutput(
            '{} -c "import os;print(\'foo\')"'.format(sys.executable),
            ['foo', 'bar']
        )

        matches = check_command_output()
        assert matches == 1

    def test_matches_all_fail(self):
        check_command_output = CheckCommandOutput(
            '{} -c "import os;print(\'foo\')"'.format(sys.executable),
            ['foo', 'bar'],
            matches='all',
            attempts=1
        )

        with pytest.raises(RetryError):
            check_command_output()

    def test_matches_all_success(self):
        check_command_output = CheckCommandOutput(
            '{} -c "import os;print(\'foobar\')"'.format(sys.executable),
            ['foo', 'bar'],
            matches='all'
        )

        matches = check_command_output()
        assert matches == 2


class TestCheckDockerLogs:
    def test_no_matches(self):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')
        run_command(['docker-compose', '-f', compose_file, 'down'])
        check_docker_logs = CheckDockerLogs(compose_file, 'Vault server started', attempts=1)

        with pytest.raises(RetryError):
            check_docker_logs()

    def test_matches(self):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')
        check_docker_logs = CheckDockerLogs(compose_file, 'Vault server started')

        try:
            run_command(['docker-compose', '-f', compose_file, 'up', '-d'], check=True)
            check_docker_logs()
        finally:
            run_command(['docker-compose', '-f', compose_file, 'down'], capture=True)


class TestCheckEndpoints:
    def test_fail(self):
        check_endpoints = CheckEndpoints('https://google.microsoft', attempts=1)

        with pytest.raises(RetryError):
            check_endpoints()

    def test_success(self):
        check_endpoints = CheckEndpoints(['https://google.com', 'https://bing.com'])

        check_endpoints()
