# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev.structures import EnvVars


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
