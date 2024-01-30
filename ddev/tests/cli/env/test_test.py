# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock


class MockEnvVars:
    def __init__(self, env_vars=None):
        assert env_vars['DDEV_REPO'] == 'core'

    def __enter__(*_args, **_kwargs):
        pass

    def __exit__(*_args, **_kwargs):
        pass


def test_env_vars_repo(ddev, helpers, data_dir, write_result_file, mocker):
    mocker.patch('subprocess.run', side_effect=write_result_file({'metadata': {}, 'config': {}}))
    with mock.patch('ddev.utils.structures.EnvVars', side_effect=MockEnvVars):
        result = ddev('env', 'test', 'postgres', 'py3.12')
        assert result.exit_code == 0, result.output
