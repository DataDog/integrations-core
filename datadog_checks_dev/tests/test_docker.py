# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest
import tenacity

from datadog_checks.dev.ci import running_on_ci
from datadog_checks.dev.docker import ComposeFileUp, compose_file_active, docker_run, get_e2e_discovery_metadata
from datadog_checks.dev.subprocess import run_command

from .common import not_windows_ci

pytestmark = [not_windows_ci]
HERE = os.path.dirname(os.path.abspath(__file__))
DOCKER_DIR = os.path.join(HERE, 'docker')


def test_get_e2e_discovery_metadata(tmp_path):
    check_root = tmp_path / 'test_check'
    check_package_root = check_root / 'datadog_checks' / 'test_check'
    data_dir = check_package_root / 'data'
    data_dir.mkdir(parents=True)
    (data_dir / 'auto_conf.yaml').write_text(
        'ad_identifiers:\n  - test\ndiscovery: {}\ninit_config:\ninstances: []\n',
        encoding='utf-8',
    )

    metadata = get_e2e_discovery_metadata(check_root)

    assert metadata == {
        'docker_volumes': [
            f'{check_package_root}/data/auto_conf.yaml:/etc/datadog-agent/conf.d/test_check.d/auto_conf.yaml:ro',
            '/var/run/docker.sock:/var/run/docker.sock:ro',
        ],
    }


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
    def test_wait_for_health_default(self):
        set_up = self.get_set_up()

        assert '--wait' in set_up.command

    def test_wait_for_health_explicit_disable(self):
        set_up = self.get_set_up(wait_for_health=False)

        assert '--wait' not in set_up.command

    def test_wait_for_health_typo_rejected(self):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')

        with pytest.raises(TypeError, match='unexpected keyword argument'):
            with docker_run(compose_file, waith_for_health=False):
                pass

    def get_set_up(self, **kwargs):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')

        with mock.patch('datadog_checks.dev.docker.environment_run') as environment_run:
            environment_run.return_value.__enter__.return_value = None
            with docker_run(compose_file, **kwargs):
                pass

        return environment_run.call_args[1]['up']

    @pytest.mark.parametrize(
        "capture",
        [
            None,
            True,
        ],
    )
    def test_compose_file(self, capture):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')

        try:
            args = {}
            if capture is not None:
                args['capture'] = capture
            with docker_run(compose_file, **args):
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
        condition = mock.MagicMock()
        condition.side_effect = Exception("exception")

        expected_exception = tenacity.RetryError
        if attempts is None:
            if running_on_ci():
                expected_call_count = 2
            else:
                expected_exception = Exception

        with pytest.raises(expected_exception):
            with docker_run(
                up=mock.MagicMock(), down=mock.MagicMock(), attempts=attempts, conditions=[condition], attempts_wait=0
            ):
                pass

        assert condition.call_count == expected_call_count

    def test_retry_condition_failed_only_on_first_run(self):
        up = mock.MagicMock()
        up.return_value = ""

        condition = mock.MagicMock()
        condition.side_effect = [Exception("exception"), None, None]

        with docker_run(up=up, down=mock.MagicMock(), attempts=3, conditions=[condition], attempts_wait=0):
            assert condition.call_count == 2


class TestComposeFileUp:
    def test_wait_for_health_default(self):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')

        compose_file_up = ComposeFileUp(compose_file)

        assert '--wait' in compose_file_up.command

    def test_wait_for_health_explicit_disable(self):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')

        compose_file_up = ComposeFileUp(compose_file, wait_for_health=False)

        assert '--wait' not in compose_file_up.command

    def test_wait_for_health_typo_rejected(self):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')

        with pytest.raises(TypeError, match='unexpected keyword argument'):
            ComposeFileUp(compose_file, waith_for_health=False)
