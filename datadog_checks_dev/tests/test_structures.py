# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev.structures import EnvVars, TempDir


class TestEnvVars:
    def test_default(self):
        assert EnvVars() == os.environ

    def test_union(self):
        env = EnvVars({'DDEV_ENV_VAR': 'is_set'})

        assert len(env) - len(os.environ) == 1
        assert set(os.environ).symmetric_difference(set(env)) == {'DDEV_ENV_VAR'}

    def test_context_manager(self):
        with EnvVars({'DDEV_ENV_VAR': 'is_set'}, ignore=['PATH']):
            assert 'DDEV_ENV_VAR' in os.environ
            assert 'PATH' not in os.environ

        assert 'DDEV_ENV_VAR' not in os.environ
        assert 'PATH' in os.environ


class TestTempDir:
    def test_create_temp_dir(self):
        with TempDir('my-temp-dir') as temp_dir:
            assert os.path.exists(temp_dir)
            assert os.path.isdir(temp_dir)
            assert os.stat(temp_dir).st_mode & 0o700 == 0o700

        assert not os.path.exists(temp_dir)

    @pytest.mark.parametrize(
        'mode',
        [
            pytest.param(0o744, id='Read to all'),
            pytest.param(0o722, id='Write to all'),
            pytest.param(0o711, id='Exec to all'),
            pytest.param(0o707, id='All to others'),
            pytest.param(0o777, id='All to all'),
        ],
    )
    def test_create_with_mode(self, mode):
        with TempDir('my-temp-dir', mode=mode) as temp_dir:
            assert os.path.exists(temp_dir)
            assert os.path.isdir(temp_dir)
            assert os.stat(temp_dir).st_mode & mode == mode
