# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest
import tenacity

from datadog_checks.dev import RetryError
from datadog_checks.dev.ci import running_on_ci
from datadog_checks.dev.docker import compose_file_active, docker_run
from datadog_checks.dev.subprocess import run_command

from .common import not_windows_ci

pytestmark = [not_windows_ci]
HERE = os.path.dirname(os.path.abspath(__file__))
DOCKER_DIR = os.path.join(HERE, 'docker')


class TestComposeFileActive:
    def test_down(self):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')
        run_command(['docker', 'compose', '-f', compose_file, 'down'], capture=True)

        assert compose_file_active(compose_file) is False

    def test_up(self):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')

        try:
            run_command(['docker', 'compose', '-f', compose_file, 'up', '-d'], check=True)
            assert compose_file_active(compose_file) is True
        finally:
            run_command(['docker', 'compose', '-f', compose_file, 'down'], capture=True)


class TestDockerRun:
    def test_compose_file(self):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')

        try:
            with docker_run(compose_file):
                assert compose_file_active(compose_file) is True
            assert compose_file_active(compose_file) is False
        finally:
            run_command(['docker', 'compose', '-f', compose_file, 'down'], capture=True)

    @pytest.mark.parametrize(
        "attempts,expected_call_count",
        [
            (None, 1),
            (0, 1),
            (1, 1),
            (3, 3),
        ],
    )
    def test_retry_on_failed_conditions(self, attempts, expected_call_count):
        compose_file = os.path.join(DOCKER_DIR, "test_default.yaml")

        condition = mock.MagicMock()
        condition.side_effect = RetryError("error")

        expected_exception = tenacity.RetryError
        if attempts is None:
            if running_on_ci():
                expected_call_count = 2
            else:
                expected_exception = RetryError

        try:
            with pytest.raises(expected_exception):
                with docker_run(compose_file, attempts=attempts, conditions=[condition]):
                    pass

            assert condition.call_count == expected_call_count
        finally:
            run_command(["docker", "compose", "-f", compose_file, "down"], capture=True)

    def test_retry_condition_failed_only_on_first_run(self):
        compose_file = os.path.join(DOCKER_DIR, "test_default.yaml")

        condition = mock.MagicMock()
        condition.side_effect = [RetryError("error"), None, None]

        try:
            with docker_run(compose_file, attempts=3, conditions=[condition]):
                assert condition.call_count == 2

        finally:
            run_command(["docker", "compose", "-f", compose_file, "down"], capture=True)
