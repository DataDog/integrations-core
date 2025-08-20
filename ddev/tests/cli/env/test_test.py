# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from contextlib import nullcontext

import mock
import pytest

from tests.helpers.mocks import MockPopen


class MockEnvVars:
    def __init__(self, env_vars=None):
        assert env_vars['DDEV_REPO'] == 'core'

    def __enter__(*_args, **_kwargs):
        pass

    def __exit__(*_args, **_kwargs):
        pass


def test_env_vars_repo(ddev, helpers, data_dir, write_result_file, mocker):
    mocker.patch('subprocess.run', side_effect=write_result_file({'metadata': {}, 'config': {}}))
    json_output = json.dumps({'py3.12': {'e2e-env': False}})
    mocker.patch('subprocess.Popen', return_value=MockPopen(returncode=0, stdout=json_output.encode()))
    with mock.patch('ddev.utils.structures.EnvVars', side_effect=MockEnvVars):
        result = ddev('env', 'test', 'postgres', 'py3.12')
        assert result.exit_code == 0, result.output
        # Ensure test was not skipped
        assert "does not have E2E tests to run" not in result.output


@pytest.mark.parametrize(
    'target, expectation',
    [
        ('datadog_checks_dev', nullcontext()),
        ('datadog_checks_base', nullcontext()),
        # This will raise an OSError because the package is not a valid integration
        ('datadog_checks_tests_helper', pytest.raises(OSError)),
        ('ddev', nullcontext()),
    ],
    ids=['datadog_checks_dev', 'datadog_checks_base', 'datadog_checks_tests_helper', 'ddev'],
)
@pytest.mark.parametrize('env', ['py3.12', 'all', ''], ids=['py3.12', 'all', 'no-env'])
def test_env_test_not_e2e_testable(ddev, target: str, env: str, expectation):
    with expectation:
        result = ddev('env', 'test', target, env)
        assert result.exit_code == 0, result.output
        assert "does not have E2E tests to run" in result.output
